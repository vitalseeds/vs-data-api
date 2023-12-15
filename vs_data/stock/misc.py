"""
Useful functions for stock management.

Created during development but not yet needed.
"""

import itertools

from rich import print

from vs_data import log
from vs_data.fm import constants
from vs_data.fm import db as fmdb

WC_MAX_API_RESULT_COUNT = 100


# back port of 3.12 itertools.batched
# https://docs.python.org/3.12/library/itertools.html#itertools.batched
def batched(iterable, n):
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(itertools.islice(it, n)):
        yield batch


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


def get_wc_products_in_stock(wcapi):
    return wcapi.get(
        "products",
        params={
            "stock_status": "instock",
            "per_page": WC_MAX_API_RESULT_COUNT,
            "page": 10,
        },
    )


def wcapi_aggregate_paginated_response(func):
    """
    Repeat calls a decorated function to get all pages of WooCommerce API response.

    Combines the response data into a single list.

    Function to call must accept parameters:
        - wcapi object
        - page number
    """

    def wrapper(wcapi, page=0, *args, **kwargs):
        items = []
        page = 0
        num_pages = WC_MAX_API_RESULT_COUNT

        while page < num_pages:
            page += 1
            log.debug(f"{page=}")

            response = func(wcapi, page=page, *args, **kwargs)

            items.extend(response.json())
            num_pages = int(response.headers["X-WP-TotalPages"])
            num_products = int(response.headers["X-WP-Total"])

        log.debug(f"{num_products=}, {len(items)=}")
        return items

    return wrapper


def wcapi_batch_post(func):
    """
    Repeat calls a decorated function to post multiple updates to WooCommerce API.

    Function to call must accept parameters:
        - wcapi object
        - iterable to be processed

    and return a requests response.
    """

    def wrapper(wcapi, updates, *args, **kwargs):
        items = []
        log.debug(batched(updates, WC_MAX_API_RESULT_COUNT))
        for batch in batched(updates, WC_MAX_API_RESULT_COUNT):
            updates = func(wcapi, batch, *args, **kwargs)
            try:
                items.extend(updates)
            except TypeError:
                log.warn("No updates described in reponse to wcapi batch post")
                log.debug(f"{batch=}")
                log.debug(f"{updates=}")

        return items

    return wrapper


@wcapi_aggregate_paginated_response
def get_all_wc_products(wcapi, page=1):
    """
    Query WooCommerce rest api for all products

    Iterates paginated requests to escape API max per page limit.
    """
    response = wcapi.get(
        "products",
        params={
            "per_page": WC_MAX_API_RESULT_COUNT,
            "page": page,
        },
    )
    response.raise_for_status()
    return response


def get_batches_awaiting_upload(connection):
    table = "packeting_batches"
    columns = ["awaiting_upload", "batch_number", "sku", "packets", "wc_product_id"]
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


def get_all_products(connection, cli=False):
    """
    Get all products (acquisitions) from the VS filemaker database.
    """
    table = "acquisitions"
    columns = [
        "sku",
        "crop",
        "wc_product_id",
        "wc_variation_lg_id",
        "wc_variation_regular_id",
    ]
    # sku = constants.fname("acquisitions", "sku")
    where = ""
    if cli:
        return fmdb._select_columns(connection, table, columns, where)
    return fmdb.select(connection, table, columns, where)
