"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

import logging
from collections import defaultdict

from rich import print

from vs_data import log
from vs_data.cli.table import display_table
from vs_data.fm import constants
from vs_data.fm.constants import fname as _f
from vs_data.fm.constants import tname as _t
from vs_data.fm import db as fmdb
from vs_data.stock.batch_upload import wc_large_product_update_stock
from vs_data.stock.batch_upload import wc_regular_product_update_stock
from inspect import cleandoc as dedent

WC_MAX_API_RESULT_COUNT = 100
LARGE_VARIATION_SKU_SUFFIX = "Gr"


def get_unprocessed_stock_corrections_join_acq_stock(connection):
    columns = [
        "id",
        "sku",
        "large_packet_correction",
        "stock_change",
        "wc_stock_updated",
        "vs_stock_updated",
        "wc_product_id",
        "wc_variation_lg_id",
        "stock_regular",
        "stock_large",
    ]
    acq_sku = _f("acquisitions", "sku")
    stock_sku = _f("stock", "sku")
    where = f'SC.{_f("stock_corrections", "wc_stock_updated")} IS NULL'

    # TODO: case sensitive validation of sku in FileMaker would negate LOWER()
    # This would be much more performant as could use indexes
    sql = (
        "SELECT SC.id, SC.sku, sc.large_packet_correction, sc.stock_change, "
        "SC.wc_stock_updated, SC.vs_stock_updated, "
        "A.wc_product_id, A.wc_variation_lg_id, "
        "S.stock_regular, S.stock_large "
        'FROM "stock_corrections" SC '
        f'LEFT JOIN "acquisitions" A ON LOWER(SC.sku) = LOWER(A.{acq_sku}) '
        f'LEFT JOIN "stock" S ON LOWER(A.{acq_sku}) = LOWER(S.{stock_sku}) '
        "WHERE " + where
    )
    log.debug(sql)
    rows = connection.cursor().execute(sql).fetchall()
    return fmdb.zip_validate_columns(rows, columns)


def get_large_batches_awaiting_upload_join_acq(connection: object) -> list:
    """
    Query the FM database for large_batches
    that are ready to be added to WooCommerce stock.

    Returns a list
    """
    # TODO: duplication between columns definition and sql
    columns = [
        "awaiting_upload",
        "batch_number",
        "packets",
        "sku",
        "wc_product_id",
        "wc_variation_lg_id",
    ]
    awaiting = _f("large_batches", "awaiting_upload")
    where = f"lower({awaiting})='yes' AND b.pack_date IS NOT NULL"

    sql = (
        "SELECT B.awaiting_upload, B.batch_number, B.packets, S.sku, A.wc_product_id, A.wc_variation_lg_id "
        f'FROM "{_t("large_batches")}" B '
        f'LEFT JOIN "{_t("seed_lots")}" S ON B.seed_lot = S.lot_number '
        'LEFT JOIN "acquisitions" A ON S.sku = A.SKU '
        "WHERE " + where
    )
    rows = connection.cursor().execute(sql).fetchall()

    # return [dict(zip(columns, r)) for r in rows]
    return fmdb.zip_validate_columns(rows, columns)


def _set_wc_stock_updated_flag(connection, correction_ids=None):
    if not correction_ids:
        return

    table_name = "stock_corrections"
    fm_table = _t(table_name)
    wc_stock_updated = _f(table_name, "wc_stock_updated")
    id = _f(table_name, "id")
    sql = ""
    for correction in correction_ids:
        try:
            sql = f"UPDATE {fm_table} SET {wc_stock_updated}=1 WHERE {id} = {correction}"
            cursor = connection.cursor()
            log.info(sql)
            cursor.execute(sql)
            log.info(cursor.rowcount)
        except Exception:
            # ensure other rows are still processed if there is an issue, eg
            # missing product id
            pass
    connection.commit()


def get_wc_products_by_id(wcapi: object, ids: list):
    ids = [str(id) for id in ids]
    comma_separated_ids = ",".join(ids)
    response = wcapi.get(
        "products",
        params={"include": comma_separated_ids, "per_page": WC_MAX_API_RESULT_COUNT},
    )
    if response.status_code == 200:
        return response.json()


def get_wc_large_variations_stock(wcapi: object, lg_variation_id_map: dict):
    """
    Gets product variations including stock quantity.

    Args:
        woocommerce api instance
        list of product ids
        large variation ids (dict) used as a map of product_id:variation_id
    """
    product_large_variations = {}
    for product_id in lg_variation_id_map:
        large_variation_id = lg_variation_id_map[product_id]
        response = wcapi.get(
            f"products/{product_id}/variations/{large_variation_id}",
            params={"per_page": WC_MAX_API_RESULT_COUNT},
        )
        if response.status_code == 200:
            stock_quantity = response.json()["stock_quantity"]
            product_large_variations[product_id] = {
                "variation_id": large_variation_id,
                "stock_quantity": stock_quantity,
            }
    return product_large_variations


def _total_stock_increments(stock_corrections):
    """
    Add up stock increments per sku.

    Accounts for case that there may be multiple corrections for a single product (sku).
    """
    stock_increments = defaultdict(lambda: 0)
    for correction in stock_corrections:
        stock_increments[correction["wc_product_id"]] += int(correction["stock_change"])
    return stock_increments


def _check_product_updates(response, corrections):
    """
    Checks the WC response for updated products and compares that with submitted
    stock_corrections
    """
    updated_products = [product["id"] for product in response["update"]]
    uploaded_corrections = [
        c["id"] for c in corrections if int(c["wc_product_id"]) in updated_products
    ]
    log.debug(uploaded_corrections)
    return uploaded_corrections


def apply_corrections_to_wc_stock(connection, wcapi=None, cli=False):
    """
    Update WooCommerce stock from stock corrections.

    Args:
        FileMaker db connection
        WooCommerce API instance

    Query filemaker for stock corrections.
    Get the current stock level for product/variation.
    Add up stock increment per product from multiple corrections.
    Update the stock_quantity for the WooCommerce product/variation.
    """
    print("apply_corrections_to_wc_stock")
    stock_corrections = get_unprocessed_stock_corrections_join_acq_stock(connection)

    if not stock_corrections:
        log.debug("No stock corrections await processing")
        return False

    log.debug(f"stock_corrections {len(stock_corrections)}")
    log.debug(stock_corrections)

    # Separate large and regular packet stock corrections
    # validate that product actually has a product/variation
    regular_product_corrections = [
        sc
        for sc in stock_corrections
        if not sc["large_packet_correction"] and sc["wc_product_id"]
    ]
    large_variation_corrections = [
        sc
        for sc in stock_corrections
        if sc["large_packet_correction"] and sc["wc_variation_lg_id"]
    ]
    invalid_variation_corrections = [
        sc["sku"]
        for sc in stock_corrections
        if sc["large_packet_correction"] and not sc["wc_variation_lg_id"]
    ]

    wc_product_ids = [c["wc_product_id"] for c in regular_product_corrections]
    lg_variation_id_map = {
        c["wc_product_id"]: c["wc_variation_lg_id"] for c in large_variation_corrections
    }

    def log_submitted_corrections():
        log.debug("regular_product_corrections:")
        log.debug(regular_product_corrections)
        log.debug("large_variation_corrections:")
        log.debug(large_variation_corrections)
        log.debug(lg_variation_id_map)
        if invalid_variation_corrections:
            log.warning(
                f"The following SKUs do not have WooCommerce 'large' variation IDs and will not be updated: {', '.join(invalid_variation_corrections)}    "
            )

    log_submitted_corrections()

    uploaded_corrections = []

    # Get current wc stock quantity
    if wc_product_ids and (
        products_stock := get_wc_products_by_id(wcapi, wc_product_ids)
    ):
        regular_stock_increments = _total_stock_increments(regular_product_corrections)
        # log.debug(products_stock)
        log.debug(regular_stock_increments)
        response_regular = wc_regular_product_update_stock(
            wcapi, products_stock, regular_stock_increments
        )
        uploaded_corrections.extend(
            _check_product_updates(response_regular, regular_product_corrections)
        )

    # Get current wc stock quantity for large variations
    if lg_variation_id_map:
        products_large_variation_stock = get_wc_large_variations_stock(
            wcapi, lg_variation_id_map
        )
        large_stock_increments = _total_stock_increments(large_variation_corrections)
        log.debug(large_stock_increments)
        lg_variation_ids = {
            c["wc_product_id"]: c["wc_variation_lg_id"]
            for c in large_variation_corrections
        }
        response_large = wc_large_product_update_stock(
            wcapi,
            products_large_variation_stock,
            large_stock_increments,
            lg_variation_ids,
        )
        lg_updates = _check_product_updates(response_large, large_variation_corrections)
        log.debug(lg_updates)
        uploaded_corrections.extend(lg_updates)
    log.debug(uploaded_corrections)
    _set_wc_stock_updated_flag(connection, uploaded_corrections)

    # TODO: Also update stock value in FM directly from woocommerce value (lg/reg)
    # This will negate requirement for a preceding 'update stock' FM script

    return uploaded_corrections
