
from pathlib import Path, PurePath
import fnmatch
import urllib
import boto3
from . import config
from .utils.subprocess import run_command
from .utils import path_str

cfg = config.load()

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
    

class StorageError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class S3:


    def __init__(self):
        s3_config = cfg.storage.s3

        self.s3 = boto3.client('s3',
                               endpoint_url=s3_config.endpoint_url,
                               aws_access_key_id=s3_config.access_key,
                               aws_secret_access_key=s3_config.access_secret_key)
        


    def sync_to_local(self, src:str, dst:Path | str, select="**/*"):
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
        dst = Path(dst).expanduser()
        bucket_name, bucket_prefix = parse_s3_url(src)

        print(f"Copying S3 to local '{bucket_name}:{bucket_prefix}' => '{dst}'")

        s3_result = s3.list_objects_v2(Bucket=bucket_name, Prefix=bucket_prefix)
        s3_contents = s3_result.get('Contents')
        if not s3_contents:
            print(f"{src} returned no content")
            raise StorageError('No remote content found')

        for obj in s3_contents:
            #print("Found object:", obj)

            file_key = obj['Key']

            if not fnmatch.fnmatch(file_key, select):
                continue

            local_path = dst / PurePath(file_key).relative_to(bucket_prefix)

            if local_path.exists():
                print(f" ==> Skipping file already present at {local_path}")
                continue

            print(f" ==> Downloading remote S3 file at {bucket_name}/{file_key} => {local_path}")

            if is_s3_dir(obj):
                local_path.mkdir(exist_ok=True, parents=True)
            else:
                local_path.parent.mkdir(exist_ok=True, parents=True)
                s3.download_file(bucket_name, file_key, local_path)


    def sync_to_remote(self, src:Path | str, dst:str, select="**/*"):
        """
        Syncs the local file system folder `src` to the S3 bucket path/url `dst`.
        """
        s3 = self.s3

        src = Path(src).expanduser()
        
        bucket_name, bucket_prefix = parse_s3_url(dst)
        bucket_prefix = Path(bucket_prefix)

        for src_path in src.glob(select):
            if src_path.is_file():
                subpath = src_path.relative_to(src)
                dst_path = str(bucket_prefix / subpath)

                print(f" ==> Uploading file at {src_path} to {bucket_name}:{dst_path}")
                s3.upload_file(src_path, bucket_name, dst_path)
                

    