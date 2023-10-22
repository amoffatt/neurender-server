
import os
from pathlib import Path, PurePath
import fnmatch
import urllib
import boto3
from pydantic import BaseModel
from neurender.utils.files import get_last_modified

from neurender.utils.pydantic import read_yaml_file, write_yaml_file
from . import config
from .utils.subprocess import run_command
from .utils import path_str, print_err

cfg = config.load()

SELECT_ALL_FILES = "**/*"

@staticmethod
def parse_s3_url(url):
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
        else:
            return (None, None)

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


class S3:

    def __init__(self):
        s3_config = cfg.storage.s3

        self.s3 = boto3.client('s3',
                               endpoint_url=s3_config.endpoint_url,
                               aws_access_key_id=s3_config.access_key,
                               aws_secret_access_key=s3_config.access_secret_key)
        


    def sync_to_local(self, src:str, dst:Path | str=None, select=""):
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
        s3 = self.s3
        if not dst:
            dst = Path(src).name
        else:
            dst = Path(dst).expanduser()

        select = select or SELECT_ALL_FILES

        bucket_name, bucket_prefix = parse_s3_url(src)

        print(f"Copying S3 to local '{bucket_name}:{bucket_prefix}' => '{dst}'")

        s3_result = s3.list_objects_v2(Bucket=bucket_name, Prefix=bucket_prefix)
        s3_contents = s3_result.get('Contents')
        if not s3_contents:
            print(f"{src} returned no content")
            raise StorageError('No remote content found')

        dst.mkdir(parents=True, exist_ok=True)

        # Write remote directory metadata
        meta_file = dst / DIRECTORY_METAFILE_NAME
        meta = RemoteFileMeta(url=src)
        write_yaml_file(meta, meta_file)

        for obj in s3_contents:
            # print("\n\n====")
            # print("Found object:", obj)

            file_key = obj['Key']
            remote_last_modified = obj['LastModified']

            if not fnmatch.fnmatch(file_key, select):
                continue

            local_path = dst / PurePath(file_key).relative_to(bucket_prefix)

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
                s3.download_file(bucket_name, file_key, local_path)
                timestamp = remote_last_modified.timestamp()
                os.utime(local_path, times=(timestamp, timestamp))


    def sync_to_remote(self, src:Path | str, dst:str, select=""):
        """
        Syncs the local file system folder `src` to the S3 bucket path/url `dst`.
        """
        s3 = self.s3
        select = select or SELECT_ALL_FILES

        src = Path(src).expanduser()

        if not dst:
            # check for remote.meta file if no dst provided
            try:
                dst = load_remote_meta(src).url
            except Exception as e:
                raise StorageError(f"No destination URL provided and {DIRECTORY_METAFILE_NAME} could not be loaded from source directory")

        
        bucket_name, bucket_prefix = parse_s3_url(dst)

        s3_result = s3.list_objects_v2(Bucket=bucket_name, Prefix=bucket_prefix)
        s3_existing_contents = s3_result.get('Contents')
        if not s3_existing_contents:
            print(f"No existing remote content found in bucket {bucket_name}:{bucket_prefix}")

        remote_lookup = { o['Key']:o for o in s3_existing_contents }


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
                s3.upload_file(src_path, bucket_name, dst_path)
                

    