import csv
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


def push_variation_prices_to_wc(wcapi, fmdb, cli: bool = False) -> list | None:
    # Query vs_db for variation prices
    variation_products = get_acquisitions_with_large_variation(fmdb)
    log.debug(variation_products)
    # Audit: Export CSV of variation prices pre update
    # f = open('tmp/variation_prices_pre_update.csv','wb')
    # w = csv.DictWriter(f, [
    #     "sku",
    #     # "crop",
    #     "wc_product_id",
    #     "wc_variation_lg_id",
    #     "wc_variation_regular_id",
    #     # "not_selling_in_shop",
    #     "price",
    #     "lg_variation_price",
    # ])
    # w.writerows(variation_products)
    # f.close()

    # Loop products with variations
    for p in variation_products:
        wc_pid = p["wc_product_id"]

        wc_var_reg_id = p["wc_variation_regular_id"]
        wc_var_reg_price = p["price"]
        wc_var_lg_id = p["wc_variation_lg_id"]
        wc_var_lg_price = p["lg_variation_price"]

        # Push regular product variation price
        endpoint = f"products/{wc_pid}/variations/{wc_var_reg_id}"
        data = {
            "regular_price": str(wc_var_reg_price),
        }
        log.debug(data)
        response = wcapi.put(endpoint, data)
        log.debug(response)
        log.debug(response.json())

        # Push large product variation price
        endpoint = f"products/{wc_pid}/variations/{wc_var_lg_id}"
        data = {
            "regular_price": str(wc_var_lg_price),
        }
        response = wcapi.put(endpoint, data)
        log.debug(response)
        log.debug(response.json())
        quit()

    # PUT prices for regular and large variations to WC (via rest API update)
    # Audit: Export CSV of variation prices post update


def recapitalise_lg_skus(wcapi, cli: bool = False) -> list | None:
    # Cache rest api call for products
    prod_skus_pickle = "tmp/prod_skus.pickle"
    if exists(prod_skus_pickle):
        # if None:
        with open(prod_skus_pickle, "rb") as file:
            prod_skus = pickle.load(file)
    else:
        # Get all products
        products = get_all_wc_products(wcapi)

        # Filter to those with variations
        prod_skus = [
            {"sku": p["sku"], "id": p["id"], "variation_ids": p["variations"]}
            for p in products
            if p["variations"]
        ]
        log.debug(prod_skus)

        with open(prod_skus_pickle, "wb") as file:
            pickle.dump(prod_skus, file)

    # Loop variations
    variation_updates = []
    for p in prod_skus:
        # product_sku = p["sku"]
        product_id = p["id"]
        variation_ids = p["variation_ids"]
        variations = get_wc_variations_for_product(
            wcapi,
            product_id,
            variation_ids,
        )
        if len(variations) == 2:
            regular_product_sku = [
                v["sku"]
                for v in variations
                if not v["sku"].endswith(("-GR", "-Gr", "-gr"))
            ][0]
            large_variations = [
                [v["id"], v["sku"]]
                for v in variations
                if v["sku"].endswith(("-GR", "-Gr", "-gr"))
            ]
            if not large_variations:
                continue
            large_variation = large_variations[0]
            large_variation_sku = large_variation[1]

            # Construct lg var sku from regular sku
            new_lg_sku = f"{regular_product_sku}-Gr"

            log.debug(
                f"• Regular product sku: {regular_product_sku}\n• Large variation sku: {large_variation_sku}\n• Capitalised lg var sku: {new_lg_sku}"
            )

            # Check if lg var sku is lowercase?
            if new_lg_sku == large_variation_sku:
                log.info(f"SKU already correct ({new_lg_sku})")
                continue

            log.warn(
                f"Large variation sku needs updating ({large_variation_sku} → {new_lg_sku})"
            )

            # generate rest api query to update

            endpoint = f"products/{product_id}/variations/{large_variation[0]}"
            data = {"sku": new_lg_sku}
            response = wcapi.put(endpoint, data)
            variation_updates.append(response.json())

        log.info(variation_updates)
        with open("tmp/sku_capitalise_updates.pickle", "wb") as file:
            pickle.dump(variation_updates, file)

    # post query

    # # Assume for now that we only want to get orders that are in 'packing'
    # orders = get_selected_orders(fmlinkdb)
    # # orders = [{'link_wc_order_id': 46011, 'full_name': 'Roberta Mathieson', 'status': 'packing', 'selected': 'Yes'}]
    # log.debug(f"{len(orders)=}")

    # if orders:
    #     wc_updates = wc_orders_update_status(wcapi, orders, target_status=target_status)
    #     log.info("WooCommerce updated")
    #     log.debug(wc_updates)
    #     if not wc_updates:
    #         return

    #     if target_status == "completed":
    #         link_result = link_db_update_completed_orders(fmlinkdb, wc_updates)
    #         log.info(
    #             f"Link database orders marked 'completed': {link_result} rows affected"
    #         )
    #     else:
    #         link_db_change_status_selected_orders(fmlinkdb, target_status=target_status)

    #     # return wc_response.get("update", [])
    #     return wc_updates
