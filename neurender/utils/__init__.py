from pathlib import Path
import uuid
import os

def path_str(path:Path) -> str:
    return str(path.expanduser().absolute())

def unique_subpath(base_path:Path):
    while True:
        name = str(uuid.uuid4())[:8]
        path = base_path / name
        if not os.path.exists(path):
            return path

            
        