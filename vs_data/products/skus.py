from vs_data.stock.misc import get_all_products, get_all_wc_products
from vs_data.cli.table import display_product_table, display_table
import json
import pandas as pd
import pickle
from os.path import exists
import os
from vs_data.fm.db import convert_pyodbc_cursor_results_to_lists
from vs_data.fm import db
from vs_data.fm.constants import fname as _f
from vs_data.fm.constants import tname as _t
from vs_data import log
from rich import print
import numpy as np
from datascroller import scroll
from vs_data.stock.misc import wcapi_aggregate_paginated_response
from datetime import datetime

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
        with open("tmp/sku_capitalise_updates", "wb") as file:
            pickle.dump(variation_updates, file)
        quit()

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
