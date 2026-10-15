"""The fixes the doctor offers. Each takes the config and returns True if it worked."""

import time

from vs_doctor import config as doctor_config
from vs_doctor import windows


def wait_until(condition, seconds) -> bool:
    """Check condition() once a second for up to `seconds`."""
    for _ in range(seconds):
        if condition():
            return True
        time.sleep(1)
    return condition()


def open_filemaker(config) -> bool:
    """Open the FileMaker files (which starts FileMaker) and wait for it to appear."""
    for path in doctor_config.fm_files(config):
        windows.open_file(path)
    return wait_until(windows.filemaker_running, seconds=60)


def start_service(config) -> bool:
    """Start the data server's service (needs admin) and wait for it to be running."""
    name = config["doctor"]["service_name"]
    windows.start_service(name)
    return wait_until(lambda: windows.service_state(name) == "RUNNING", seconds=30)


START_SCRIPT_NAME = "Start data server.cmd"


def start_script_path():
    return doctor_config.report_dir() / START_SCRIPT_NAME


def write_start_script(config):
    """Write a file staff can double-click to start the service. It asks Windows for admin rights."""
    name = config["doctor"]["service_name"]
    path = start_script_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "@echo off\r\n"
        f"powershell -NoProfile -Command \"Start-Process sc.exe -ArgumentList 'start {name}' -Verb RunAs\"\r\n"
        "echo Starting the data server. Run vsdata-doctor again in a minute.\r\n"
        "pause\r\n"
    )
    return path


def start_service_as_admin(config) -> bool:
    """Open the start script (Windows asks 'Do you want to allow this?') and wait for the service."""
    windows.open_file(write_start_script(config))
    name = config["doctor"]["service_name"]
    return wait_until(lambda: windows.service_state(name) == "RUNNING", seconds=60)
