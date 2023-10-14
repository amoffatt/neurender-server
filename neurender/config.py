from io import IOBase, StringIO
from pathlib import Path
from pydantic import BaseModel
from .utils.pydantic import read_yaml_file, write_yaml_file
from .paths import CONFIG_FILE


class S3Config(BaseModel):
    endpoint_url:str = None
    access_key:str = None
    access_secret_key:str = None


class StorageConfig(BaseModel):
    s3:S3Config = None
    

class NeurenderConfig(BaseModel):
    storage:StorageConfig = None



def load(file:Path | str | IOBase = None):
    try:
        return read_yaml_file(NeurenderConfig, file or CONFIG_FILE)
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}")
        return NeurenderConfig()

def load_str(config_str:str):
    return load(StringIO(config_str))
    

def write(config:NeurenderConfig):
    write_yaml_file(config, CONFIG_FILE)