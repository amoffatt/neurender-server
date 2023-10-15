from pathlib import Path
import uuid
import sys, os

def print_err(*args):
    print(*args, file=sys.stderr)

def path_str(path:Path | str) -> str:
    return str(Path(path).expanduser().absolute())

def unique_subpath(base_path:Path):
    while True:
        name = str(uuid.uuid4())[:8]
        path = base_path / name
        if not os.path.exists(path):
            return path

            
        