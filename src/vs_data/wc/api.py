from woocommerce import API
from vs_data.cli.table import display_table


def get_api(url, key, secret):
    # print(url, key, secret)
    print(url)
    response = None
    try:
        response = API(
            url=url,
            consumer_key=key,
            consumer_secret=secret,
            version="wc/v3",
            timeout=300,
        )
    except Exception:
        print("Could not connect to woocommerce API")

    return response

    print("hello")
