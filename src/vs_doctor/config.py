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
    """
    Read config.ini over the defaults. Raises configparser.Error if the file is malformed.

    With no path and no config.ini in the usual place, fall back to a developer's .env
    (see env_file_used).
    """
    config = defaults()
    if path is None and not config_path().exists():
        env_file = find_env_file()
        if env_file:
            apply_env_file(config, env_file)
            return config
    # utf-8-sig: Notepad may save the file with a byte order mark
    config.read(path or config_path(), encoding="utf-8-sig")
    return config


# --- developer settings: the app's .env (copied from vs_data_api.env, which the doctor can't import) ---

ENV_FILE_VAR = "VSDATA_ENV_FILE"
REPO_ROOT = Path(__file__).resolve().parents[2]


def find_env_file():
    """The .env the app would load: $VSDATA_ENV_FILE, else the repo's, else the current folder's."""
    explicit = os.environ.get(ENV_FILE_VAR)
    candidates = [Path(explicit)] if explicit else [REPO_ROOT / ".env", Path.cwd() / ".env"]
    return next((path for path in candidates if path.is_file()), None)


def parse_env_file(path) -> dict:
    """KEY=value lines; quotes, an `export ` prefix and # comments are handled."""
    values = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if len(value) > 1 and value[0] in "\"'" and value.endswith(value[0]):
            value = value[1:-1]
        else:
            value = value.split(" #")[0].strip()
        values[key] = value
    return values


def apply_env_file(config, path):
    """Fill the config from VSDATA_* in the file (real environment variables win, as in the app)."""
    values = {**parse_env_file(path), **{k: v for k, v in os.environ.items() if k.startswith("VSDATA_")}}
    for key in [*REQUIRED["vsdata"], "wc_verify_ssl"]:
        if f"VSDATA_{key.upper()}" in values:
            config["vsdata"][key] = values[f"VSDATA_{key.upper()}"]
    if "VSDATA_PORT" in values:
        config["server"]["port"] = values["VSDATA_PORT"]
    for key in DOCTOR_DEFAULTS:
        if f"VSDATA_DOCTOR_{key.upper()}" in values:
            config["doctor"][key] = values[f"VSDATA_DOCTOR_{key.upper()}"]
    config.read_dict({"source": {"env_file": str(path)}})


def env_file_used(config):
    """The .env the settings came from (developer settings), or None when they came from config.ini."""
    path = config.get("source", "env_file", fallback="")
    return Path(path) if path else None


def missing_settings(config) -> list:
    # the doctor-only settings are for the office install; developers can do without
    required = {"vsdata": REQUIRED["vsdata"]} if env_file_used(config) else REQUIRED
    return [
        f"{key} in [{section}]"
        for section, keys in required.items()
        for key in keys
        if not config.get(section, key, fallback="").strip()
    ]


def fm_files(config) -> list:
    return [Path(line.strip()) for line in config["doctor"]["fm_files"].splitlines() if line.strip()]


def report_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "VSData" if local else get_config_dir()
