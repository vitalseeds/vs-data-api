"""Thin wrappers around the Windows calls the doctor makes. The only module that talks to the OS."""

import ctypes
import os
import subprocess
import sys


def is_windows() -> bool:
    return sys.platform == "win32"


def _run(args) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout


def running_processes() -> list:
    """Image names of running processes, e.g. ["FileMaker Pro.exe", ...]."""
    output = _run(["tasklist", "/NH", "/FO", "CSV"])
    return [line.split('","')[0].strip('"') for line in output.splitlines() if line.strip()]


def filemaker_running() -> bool:
    return any(name.lower().startswith("filemaker") for name in running_processes())


def service_state(name):
    """RUNNING, STOPPED, ... or None if there is no such service."""
    for line in _run(["sc", "query", name]).splitlines():
        if line.strip().startswith("STATE"):
            return line.split()[-1]
    return None


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):  # not Windows
        return False


def start_service(name) -> None:
    _run(["sc", "start", name])


def open_file(path) -> None:
    """Open a file with its default app, as a double-click would (FileMaker for .fmp12)."""
    os.startfile(str(path))
