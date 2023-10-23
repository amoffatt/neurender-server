
from multiprocessing import Pool
from threading import Semaphore
import os
from pathlib import Path
import fnmatch
from typing import Tuple
import urllib
import boto3
from datetime import datetime
from pydantic import BaseModel
from neurender.utils.files import get_last_modified
from am_imaging.files import as_path

from neurender.utils.pydantic import read_yaml_file, write_yaml_file
from . import config
from .utils.subprocess import run_command
from .utils import path_str, print_err

cfg = config.load()

SELECT_ALL_FILES = "**/*"

@staticmethod
def parse_s3_url(url) -> Tuple[str, str]:
    """Splits an AWS S3 URL into the bucket name and key.

    Args:
        url: The AWS S3 URL.

    Returns:
        A tuple containing (bucket name, key), or (None, None) if the url/path is not valid
    """

    parsed_url = urllib.parse.urlparse(url)

    bucket_name = parsed_url.netloc
    key = parsed_url.path.lstrip('/')

    # If bucket_name is not set
    if not bucket_name:
        if key:
            bucket_name, key = key.split('/', 1)

    return (bucket_name, key)

def is_s3_dir(s3_obj):
    return s3_obj['Size'] == 0 and s3_obj['Key'][-1] == '/'

def load_remote_meta(directory:Path|str):
    remote_meta_path = Path(directory) / DIRECTORY_METAFILE_NAME
    try:
        return read_yaml_file(RemoteFileMeta, remote_meta_path)
    except Exception as e:
        print_err("Remote folder metadata not loaded:", e)


class StorageError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


DIRECTORY_METAFILE_NAME = ".remote.meta"
class RemoteFileMeta(BaseModel):
    url:str = ''

def _create_s3_client(s3_config:config.S3Config):
    return boto3.client('s3',
                        aws_access_key_id=s3_config.access_key,
                        aws_secret_access_key=s3_config.access_secret_key,
                        endpoint_url=s3_config.endpoint_url)


def _s3_download_file(s3_config:config.S3Config, bucket_name:str, file_key:str, local_path:Path, last_modified_time:datetime):
    s3 = _create_s3_client(s3_config)
    s3.download_file(bucket_name, str(file_key), local_path)
    timestamp = last_modified_time.timestamp()
    os.utime(local_path, times=(timestamp, timestamp))
    # print(f"    ****Download complete for {local_path}, {bucket_name}, {file_key}")

def _s3_upload_file(s3_config:config.S3Config, file_path:Path, bucket_name:str, file_key:str):
    # print(f"    ****Starting upload for {file_path}, {bucket_name}, {file_key}")
    s3 = _create_s3_client(s3_config)
    s3.upload_file(file_path, bucket_name, file_key)
    # print(f"    ****Upload complete for {file_path}, {bucket_name}, {file_key}")


class WorkerPool:
    def __init__(self, worker_count=8):
        self.worker_count = worker_count
        self._semaphore = Semaphore(worker_count)
        self._pool = Pool(processes=worker_count)

    def __enter__(self):
        self._pool.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        self._pool.close()
        self._pool.join()
        self._pool.__exit__(type, value, traceback)


    def submit(self, func, args=(), kwargs={}):
        self._semaphore.acquire()
        print("  *Invoking function:", func, args, kwargs)
        self._pool.apply_async(func, args, kwargs,
                               callback=lambda _: self._semaphore.release(),
                               error_callback=lambda err: print_err("Worker pool error:", err))


class S3:
    _config:config.S3Config

    def __init__(self):
        self._config = cfg.storage.s3

    def iter_s3_content(self, bucket, prefix):
        s3 = _create_s3_client(self._config)
        paginator = s3.get_paginator("list_objects_v2")
        print(f"  ** Listing S3 bucket: {bucket}:{prefix}")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        # total_pages = len(pages)

        print(f"  ** pages: {pages}")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for i, page in enumerate(pages):
            print(f"  ** Loading S3 page {i+1}")

            s3_contents = page.get('Contents')
            if not s3_contents:
                print(f"S3 bucket {bucket}:{prefix} (page: {page}) returned no content")
                raise StorageError('No remote content found')

            for o in s3_contents:
                yield o
    

    def sync_to_local(self, src:str, dst:Path | str='', select=""):
        """
        Syncs an S3 bucket url folder `src` to the local filesystem at `dst`.
        The s3 prefix is optional in `src`, which can be of the following forms:
            s3://bucket_name/path/to/directory
            /bucket_name/path
            bucket_name/path

        Note: `select` may behave differently, due to a bug in Python pathlib.
        fnmatch.fnmatch() is used here instead of Path.match(), because Path.match() does not
        properly expand the pattern '**'
        """
        if not dst:
            dst = Path(src).name
        else:
            dst = Path(dst).expanduser()

        select = select or SELECT_ALL_FILES

        bucket_name, bucket_prefix = parse_s3_url(src)

        print(f"Copying S3 to local '{bucket_name}:{bucket_prefix}' => '{dst}'")

        dst.mkdir(parents=True, exist_ok=True)

        # Write remote directory metadata
        meta_file = dst / DIRECTORY_METAFILE_NAME
        meta = RemoteFileMeta(url=src)
        write_yaml_file(meta, meta_file)

        with WorkerPool(self._config.process_count) as pool:
            
            for i, obj in enumerate(self.iter_s3_content(bucket_name, bucket_prefix)):
            #     pool.apply(_invoke_download_file, (self, i))
            # pool.map(_invoke_download_file, [(0, i) for i in range(10)])
                file_key = obj['Key']

                if not fnmatch.fnmatch(file_key, select):
                    continue

                remote_last_modified = obj['LastModified']
                local_path = dst / Path(file_key).relative_to(bucket_prefix)

                if local_path.exists():
                    last_modified = get_last_modified(local_path)
                    # print("Remote modified:", remote_last_modified)
                    # print("Local modified: ", last_modified)
                    verb = "Updating"
                    try:
                        if remote_last_modified and remote_last_modified <= last_modified:
                            verb = "Skipping"
                            continue 
                    finally:
                        print(f" ==> {verb} file already present at {local_path}")
                else:
                    print(f" ==> Downloading remote S3 file at {bucket_name}/{file_key} => {local_path}")


                if is_s3_dir(obj):
                    local_path.mkdir(exist_ok=True, parents=True)
                else:
                    local_path.parent.mkdir(exist_ok=True, parents=True)


                    pool.submit(
                        _s3_download_file,
                        (self._config, bucket_name, file_key, local_path, remote_last_modified))



    def sync_to_remote(self, src:Path | str, dst:str, select=""):
        """
        Syncs the local file system folder `src` to the S3 bucket path/url `dst`.
        """
        select = select or SELECT_ALL_FILES

        src = Path(src).expanduser()

        if not dst:
            # check for remote.meta file if no dst provided
            try:
                dst = load_remote_meta(src).url
            except Exception as e:
                raise StorageError(f"No destination URL provided and {DIRECTORY_METAFILE_NAME} could not be loaded from source directory")

        
        bucket_name, bucket_prefix = parse_s3_url(dst)

        try:
            remote_lookup = { o['Key']: o for o in self.iter_s3_content(bucket_name, bucket_prefix) }
        except Exception as e:
            print(f"Error retreiving existing content for bucket: {bucket_name}:{bucket_prefix}")


        with WorkerPool(self._config.process_count) as pool:
            for src_path in src.glob(select):
                if src_path.is_file():
                    subpath = src_path.relative_to(src)
                    dst_path = str(Path(bucket_prefix) / subpath)

                    verb = "Uploading"
                    existing_obj = remote_lookup.get(dst_path)
                    if existing_obj:
                        last_modified = get_last_modified(src_path)
                        if existing_obj['LastModified'] >= last_modified:
                            print(f"Skipping file {src_path}: Existing remote content is same or newer version")
                            continue
                        else:
                            verb = "Replacing"


                    print(f" ==> {verb} file at {src_path} to {bucket_name}:{dst_path}")
                    
                    pool.submit(
                        _s3_upload_file,
                        (self._config, src_path, bucket_name, dst_path))
                

    