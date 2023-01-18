"""
Useful functions for stock management.

Created during development but not yet needed.
"""

from vs_data.fm import db as fmdb
from vs_data.fm import constants

WC_MAX_API_RESULT_COUNT = 10


def get_wp_product_by_sku(wcapi, sku):
    """
    Unfortunately most products don't seem to have a sku in WC
    May need to fetch them all and write to fmdb? Otherwise map to product ID
    Believe currently link_db stores the map of product id to SKU
    """
    sku = "ChTr"
    if not sku:
        return
    products = wcapi.get(
        "products",
        params={"sku": sku},
    )
    return products.json()


def get_products_in_stock(wcapi):
    return wcapi.get(
        "products",
        params={
            "stock_status": "instock",
            "per_page": WC_MAX_API_RESULT_COUNT,
            "page": 10,
        },
    )


def get_batches_awaiting_upload(connection):
    table = "packeting_batches"
    columns = ["awaiting_upload", "batch_number", "sku", "packets"]
    awaiting = constants.fname("packeting_batches", "awaiting_upload")
    where = f"{awaiting}='yes'"
    return fmdb.select(connection, table, columns, where)


def get_large_batches_awaiting_upload(connection):
    table = "large_batches"
    columns = [
        "awaiting_upload",
        "sku",
        "skufk",
        "batch_number",
        "packed",  # equivalent of 'packets'
        "packets",  # equivalent of 'to_pack'
    ]
    where = "awaiting_upload='yes'"
    return fmdb.select(connection, table, columns, where)
