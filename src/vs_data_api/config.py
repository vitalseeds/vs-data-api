import configparser
import os
import sys
from pathlib import Path

from pydantic import Field, PrivateAttr
from pydantic_settings import SettingsConfigDict, BaseSettings
from woocommerce import API as wc_api

from vs_data_api.vs_data import wc


def get_config_dir() -> Path:
    """Return platform-appropriate config directory for VS Data."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "VSData"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VSData"
    else:  # Linux and others
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg_config) / "vsdata"


def load_ini_config() -> dict:
    """
    Load configuration from INI file if it exists.

    Returns dict of environment variable names and values.
    Config file location is platform-dependent (see get_config_dir()).
    """
    config_path = get_config_dir() / "config.ini"
    if not config_path.exists():
        return {}

    parser = configparser.ConfigParser()
    parser.read(config_path)

    result = {}
    if "vsdata" in parser:
        for key, value in parser["vsdata"].items():
            result[f"vsdata_{key}"] = value
    return result


class Settings(BaseSettings):
    # model_config = ConfigDict(env_file=".envrc", env_file_encoding="utf-8")

    app_name: str = "VS Data API"
    # fm_connection_string = os.environ.get("VSDATA_FM_CONNECTION_STRING", "")
    fm_connection_string: str = Field()
    fm_link_connection_string: str = Field()
    vsdata_wc_url: str = Field(..., validation_alias="vsdata_wc_url")
    vsdata_wc_key: str = Field(..., validation_alias="vsdata_wc_key")
    vsdata_wc_secret: str = Field(..., validation_alias="vsdata_wc_secret")
    _wcapi: wc_api = PrivateAttr()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wcapi = wc.get_api(self.vsdata_wc_url, self.vsdata_wc_key, self.vsdata_wc_secret)

    @property
    def wcapi(self):
        """Property makes woocommerce available without the underscrore (aesthetic)"""
        return self._wcapi

    model_config = SettingsConfigDict(env_prefix="vsdata_", case_sensitive=False)


class TestSettings(Settings):
    app_name: str = "VS Data TEST"

    fm_connection_string: str = Field(..., validation_alias="vsdata_test_fm_connection_string")
    fm_link_connection_string: str = Field(..., validation_alias="vsdata_test_fm_link_connection_string")
    vsdata_wc_url: str = Field(..., validation_alias="vsdata_test_wc_url")
    vsdata_wc_key: str = Field(..., validation_alias="vsdata_test_wc_key")
    vsdata_wc_secret: str = Field(..., validation_alias="vsdata_test_wc_secret")
