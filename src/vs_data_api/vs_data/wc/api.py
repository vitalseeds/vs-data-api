import urllib

from requests.exceptions import HTTPError
from woocommerce import API

from vs_data_api.vs_data import log


def get_api(url, key, secret, check_status=False):
    """
    Return a wcapi api instance (official simple wrapper library).

    If check_status then perform a test request first.
    """
    api = API(
        url=url,
        consumer_key=key,
        consumer_secret=secret,
        version="wc/v3",
        timeout=300,
    )
    if check_status:
        log.info(f"Testing WC API connection: {url}")
        try:
            api.get("/").raise_for_status()
        except HTTPError as msg:
            log.error(f"Could not access WooCommerce API ({url})")
            log.error(msg)
            return False

    return api
