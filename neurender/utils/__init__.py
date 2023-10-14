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

            
        