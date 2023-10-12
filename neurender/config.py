import os
from pathlib import Path
from pydantic import BaseModel
from .utils import read_yaml_file, write_yaml_file
from .paths import CONFIG_FILE
import boto3




class S3Config(BaseModel):
    endpoint_url:str = None
    access_key:str = None
    access_secret_key:str = None


class StorageConfig(BaseModel):
    s3:S3Config = None
    

class NeurenderConfig(BaseModel):
    storage:StorageConfig = None





def load():
    return read_yaml_file(NeurenderConfig, CONFIG_FILE)

def write(config:NeurenderConfig):
    write_yaml_file(config, CONFIG_FILE)