import os

from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "VS Data API"
    fm_connection_string = os.environ.get("VSDATA_FM_CONNECTION_STRING", "")

    # class Config:
    #     env_file = ".env"

settings = Settings()