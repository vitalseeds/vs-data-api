from datetime import datetime
import csv
import pathlib
from vs_data.stock.misc import get_all_products, get_all_wc_products
from vs_data.cli.table import display_product_table, display_table
import json
import pandas as pd
import pickle
from os.path import exists
import os
from vs_data.fm.db import convert_pyodbc_cursor_results_to_lists
from vs_data.fm import db as fmdb
from vs_data.fm.constants import fname as _f
from vs_data.fm.constants import tname as _t
from vs_data import log
from rich import print
import numpy as np
from datascroller import scroll
from vs_data.stock.misc import wcapi_aggregate_paginated_response
from datetime import datetime
from vs_data.fm import constants

LAST_BATCH_UPDATE_LOG = "tmp/orders_batch_update_response.json"

WC_MAX_API_RESULT_COUNT = 100


def get_wc_variations_for_product(wcapi: object, product_id: int, variation_ids: list):
    """
    Gets product variations for a product.

    Args:
        woocommerce api instance
        product id
        variation ids
    """
    product_variations = []
    for variation_id in variation_ids:
        response = wcapi.get(
            f"products/{product_id}/variations/{variation_id}",
            params={"per_page": WC_MAX_API_RESULT_COUNT},
        )
        if response.status_code == 200:
            # stock_quantity = response.json()["stock_quantity"]
            product_variations.append(response.json())
    return product_variations


def get_acquisitions_with_large_variation(connection):
    table = "acquisitions"
    columns = [
        "sku",
        # "crop",
        "wc_product_id",
        "wc_variation_lg_id",
        "wc_variation_regular_id",
        # "not_selling_in_shop",
        "price",
        "lg_variation_price",
    ]
    lg_var_price = constants.fname("acquisitions", "lg_variation_price")
    where = f"{lg_var_price} IS NOT NULL"
    return fmdb.select(connection, table, columns, where)
    # return fmdb.select(connection, table, columns)


def get_audit_log_path(audit_key):
    audit_log_dir = os.environ.get("AUDIT_LOG_DIR", "tmp")
    return f'{audit_log_dir}/{audit_key}.csv'


def write_audit_csv(audit_key, list_of_dicts):
    filename = get_audit_log_path(audit_key)
    append = pathlib.Path(filename).is_file()

    with open(filename, mode='a') as csv_file:
        headers = list_of_dicts[0].keys()
        audit_log_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if not append:
            audit_log_writer.writerow(headers)
        for row in list_of_dicts:
            audit_log_writer.writerow(row.values())


# def record_current_wc_variation_prices(wcapi):
#     """
#     Intended only to record previous state of WC prices
#     Extremely slow as per variation
#     """
#     all_products = get_all_wc_products(wcapi)
#     # Filter to those with variations
#     wc_var_products = [
#         {"sku": p["sku"], "id": p["id"], "variation_ids": p["variations"]}
#         for p in all_products
#         if p["variations"]
#     ]
#     wc_variation_details = []
#     for p in wc_var_products:
#         # product_sku = p["sku"]
#         product_id = p["id"]
#         variation_ids = p["variation_ids"]
#         variations = get_wc_variations_for_product(
#             wcapi,
#             product_id,
#             variation_ids,
#         )
#         for variation in variations:
#             wc_variation_details.append({
#                 "product_id": product_id,
#                 "variation_id": variation['id'],
#                 "regular_price": variation['regular_price']
#             })
#         write_audit_csv("push_variation_prices_to_wc-2_wc_before", wc_variation_details)


def push_variation_prices_to_wc(wcapi, fmdb, cli: bool = False) -> list | None:
    # Query vs_db for variation prices
    variation_products = get_acquisitions_with_large_variation(fmdb)
    log.debug(variation_products)

    now = datetime.now() # current date and time
    run_time = now.strftime("%Y-%m-%d__%H-%M-%S")
    audit_key = f"wc_variation_prices_after_{run_time}"
    audit_log_path = get_audit_log_path(audit_key)

    # Audit: Export CSV of variation prices in DB pre update
    # write_audit_csv("push_variation_prices_to_wc-1_db_before", variation_products)
    # Audit: Export CSV of variation prices on WC pre update
    # record_current_wc_variation_prices(wcapi)

    # Loop products with variations
    try:
        for p in variation_products:
            wc_pid = p["wc_product_id"]

            wc_var_reg_id = p["wc_variation_regular_id"]
            wc_var_reg_price = p["price"]
            wc_var_lg_id = p["wc_variation_lg_id"]
            wc_var_lg_price = p["lg_variation_price"]

            def log_wc_variations_new_price(v):
                variation_updates_concise = [
                    {
                        "sku": v["sku"],
                        "id": v["id"],
                        "regular_price": v["regular_price"],
                        "permalink": v["permalink"],
                    }
                ]
                write_audit_csv(audit_key, variation_updates_concise)

            # PUT prices for regular and large variations to WC (via rest API update)
            # Push regular product variation price
            endpoint = f"products/{wc_pid}/variations/{wc_var_reg_id}"
            data = {
                "regular_price": str(wc_var_reg_price),
            }
            log.debug(data)
            response = wcapi.put(endpoint, data)
            log.debug(response)
            log.debug(response.json())
            log_wc_variations_new_price(response.json())

            # Push large product variation price
            endpoint = f"products/{wc_pid}/variations/{wc_var_lg_id}"
            data = {
                "regular_price": str(wc_var_lg_price),
            }
            response = wcapi.put(endpoint, data)
            log.debug(response)
            log.debug(response.json())
            log_wc_variations_new_price(response.json())
    except Exception:
        pass

    return variation_products, audit_log_path
    # Audit: Export CSV of variation prices post update
