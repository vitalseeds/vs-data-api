import os

import pydantic
from pydantic import BaseSettings, Field, PrivateAttr
from woocommerce import API as wc_api

from vs_data_api.vs_data import log, wc


class Settings(BaseSettings):
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


settings = Settings()
