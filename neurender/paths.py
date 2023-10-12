import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TOOLS_ROOT = PROJECT_ROOT / "tools"

GAUSSIAN_SPLATTING_ROOT = TOOLS_ROOT / "gaussian-splatting"
NERFSTUDIO_GAUSSIAN_SPLATTING_ROOT = TOOLS_ROOT / "nerfstudio-gaussian-splatting-fork"

CONFIG_FILE = Path("~/.neurender.conf").expanduser()