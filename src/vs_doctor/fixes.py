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
