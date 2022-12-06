from woocommerce import API
from vs_data.utils.cli import display_table


def get_api(url, key, secret):
    # print(url, key, secret)
    print(url)
    return API(
        url=url, consumer_key=key, consumer_secret=secret, version="wc/v3", timeout=300
    )


def display_product_table(products, fields=["id", "sku", "stock_quantity"]):
    if hasattr(products, "json"):
        products = products.json()

    rows = []
    for product in products:
        rows.append([product[f] for f in fields])

    display_table(fields, rows)
