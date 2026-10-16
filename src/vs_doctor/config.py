"""Find and read config.ini: the same file as the server, plus a [doctor] section."""

import configparser
import os
import sys
from pathlib import Path

DOCTOR_DEFAULTS = {
    "fm_files": "",
    "service_name": "VSDataAPI",
    "log_file": r"C:\Program Files\VSData\logs\stderr.log",
    "contact": "Call or WhatsApp Tom.",
    "docs_url": "",
}

REQUIRED = {
    "vsdata": ["fm_connection_string", "fm_link_connection_string", "wc_url", "wc_key", "wc_secret"],
    "doctor": ["fm_files"],
}


def get_config_dir() -> Path:
    """Copied from vs_data_api.config.get_config_dir (a test keeps the two in step)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "VSData"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VSData"
    else:  # Linux and others
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg_config) / "vsdata"


def config_path() -> Path:
    return get_config_dir() / "config.ini"


def defaults() -> configparser.ConfigParser:
    """A config holding only the defaults, used when config.ini can't be read."""
    # interpolation=None: a % in a password must not be treated as a variable
    config = configparser.ConfigParser(interpolation=None)
    config.read_dict({"vsdata": {}, "server": {"port": "8432"}, "doctor": DOCTOR_DEFAULTS})
    return config


def read_config(path=None) -> configparser.ConfigParser:
    """Read config.ini over the defaults. Raises configparser.Error if the file is malformed."""
    config = defaults()
    # utf-8-sig: Notepad may save the file with a byte order mark
    config.read(path or config_path(), encoding="utf-8-sig")
    return config


def missing_settings(config) -> list:
    return [
        f"{key} in [{section}]"
        for section, keys in REQUIRED.items()
        for key in keys
        if not config.get(section, key, fallback="").strip()
    ]


def fm_files(config) -> list:
    return [Path(line.strip()) for line in config["doctor"]["fm_files"].splitlines() if line.strip()]


def report_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "VSData" if local else get_config_dir()
