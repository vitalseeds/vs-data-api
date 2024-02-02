import os

import pydantic
from pydantic import BaseSettings, ConfigDict, Field, PrivateAttr
from woocommerce import API as wc_api

from vs_data_api.vs_data import log, wc


class Settings(BaseSettings):
    # model_config = ConfigDict(env_file=".envrc", env_file_encoding="utf-8")

    app_name: str = "VS Data API"
    # fm_connection_string = os.environ.get("VSDATA_FM_CONNECTION_STRING", "")
    fm_connection_string: str = Field()
    fm_link_connection_string: str = Field()
    vsdata_wc_url: str = Field(..., env="vsdata_wc_url")
    vsdata_wc_key: str = Field(..., env="vsdata_wc_key")
    vsdata_wc_secret: str = Field(..., env="vsdata_wc_secret")
    _wcapi: wc_api = PrivateAttr()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wcapi = wc.get_api(self.vsdata_wc_url, self.vsdata_wc_key, self.vsdata_wc_secret)

    @property
    def wcapi(self):
        """Property makes woocommerce available without the underscrore (aesthetic)"""
        return self._wcapi

    class Config:
        env_prefix = "vsdata_"  # defaults to no prefix, i.e. ""
        case_sensitive = False


class TestSettings(Settings):
    app_name: str = "VS Data TEST"

    fm_connection_string: str = Field(..., env="vsdata_test_fm_connection_string")
    fm_link_connection_string: str = Field(..., env="vsdata_test_fm_link_connection_string")
    vsdata_wc_url: str = Field(..., env="vsdata_test_wc_url")
    vsdata_wc_key: str = Field(..., env="vsdata_test_wc_key")
    vsdata_wc_secret: str = Field(..., env="vsdata_test_wc_secret")
