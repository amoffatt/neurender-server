from pathlib import Path
from datetime import datetime as dt
from datetime import timezone

def get_last_modified(path:Path | str, tz=None):
    timestamp = Path(path).stat().st_mtime
    if not tz:
        tz = timezone.utc
    return dt.fromtimestamp(timestamp, tz=tz)

