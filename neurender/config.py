from io import IOBase, StringIO
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from .utils.pydantic import read_yaml_file, write_yaml_file
from .paths import CONFIG_FILE


class S3Config(BaseModel):
    endpoint_url:str = ''
    access_key:str = ''
    access_secret_key:str = ''
    process_count:int = 8


class StorageConfig(BaseModel):
    s3:Optional[S3Config] = None
    

class NeurenderConfig(BaseModel):
    storage:Optional[StorageConfig] = None



def load(file:Path | str | IOBase = '') -> NeurenderConfig:
    try:
        return read_yaml_file(NeurenderConfig, file or CONFIG_FILE)
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}")
        return NeurenderConfig()

def load_str(config_str:str):
    return load(StringIO(config_str))
    

def write(config:NeurenderConfig):
    write_yaml_file(config, CONFIG_FILE)