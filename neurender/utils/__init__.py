from pathlib import Path

def path_str(path:Path) -> str:
    return str(path.expanduser().absolute())