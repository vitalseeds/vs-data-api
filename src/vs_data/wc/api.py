from woocommerce import API
from vs_data import log


def get_api(url, key, secret):
    log.info(url)
    return API(
        url=url,
        consumer_key=key,
        consumer_secret=secret,
        version="wc/v3",
        timeout=300,
    )
