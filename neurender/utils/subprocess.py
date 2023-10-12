import subprocess

class SubprocessError(Exception):
    def __init__(self, status):
        self.status = status

    def __str__(self):
        return f"{self.__class__.__name__}(status={self.status})"

def run_command(cmd_arr, cwd):
    result = subprocess.call(cmd_arr, cwd=cwd)
    if result != 0:
        raise SubprocessError(result)