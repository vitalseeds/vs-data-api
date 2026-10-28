from functools import lru_cache

from vs_data_api import config


@lru_cache()
def get_settings():
    return config.Settings()
