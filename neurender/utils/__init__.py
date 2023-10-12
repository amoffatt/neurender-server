from pathlib import Path
import uuid
import os
from typing import Type
from pydantic import BaseModel
from pydantic_yaml import parse_yaml_file_as, to_yaml_file

def path_str(path:Path | str) -> str:
    return str(Path(path).expanduser().absolute())

def unique_subpath(base_path:Path):
    while True:
        name = str(uuid.uuid4())[:8]
        path = base_path / name
        if not os.path.exists(path):
            return path

            

def read_yaml_file(_type:Type[BaseModel], path:Path | str):
    return parse_yaml_file_as(_type, path)

def write_yaml_file(model:BaseModel, path:Path | str):
    to_yaml_file(path, model)
        