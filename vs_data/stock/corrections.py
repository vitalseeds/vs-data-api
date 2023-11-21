"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

import logging
from collections import defaultdict

from rich import print

from vs_data import log
from vs_data.cli.table import display_table
from vs_data.fm import db
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


def _check_product_updates(response, corrections, vs_key="wc_product_id"):
    """
    Checks the WC response for updated products and compares that with submitted
    stock_corrections
    """
    updated_products = [product["id"] for product in response["update"]]
    uploaded_corrections = [
        c["id"] for c in corrections if int(c[vs_key]) in updated_products
    ]
    log.debug(uploaded_corrections)
    return uploaded_corrections


def get_most_recent_batch(connection: object, sku: str) -> list:
    # NOT CURRENTLY IN USE
    # TODO: should get sku from join on seed_lot, not packeting_batches
    return fmdb.select(
        connection,
        "packeting_batches",
        ["awaiting_upload", "batch_number", "packets", "pack_date", "left_in_batch"],
        where=f"pack_date IS NOT NULL AND LOWER(sku)=LOWER('{sku}') AND left_in_batch>0",
        order_by="pack_date DESC",
        limit=1
    )


def get_current_batch_id(connection: object, sku: str, field_name="packing_batch") -> list:
    # TODO: should get sku from join on seed_lot, not packeting_batches
    acquisition = fmdb.select(
        connection,
        "acquisitions",
        ["sku", field_name],
        where=f"LOWER(sku)=LOWER('{sku}')",
    )
    return acquisition[0][field_name] if acquisition else None


def get_current_large_batch_id(connection: object, sku: str) -> list:
    return get_current_batch_id(connection, sku, field_name="large_packing_batch")


def get_current_batch(connection: object, sku: str, table_name="packeting_batches") -> list:
    current_batch_id = get_current_batch_id(connection, sku)
    # TODO: join batch to get 'left in batch' value
    batch = fmdb.select(
        connection,
        table_name,
        ["batch_number", "sku", "packets", "left_in_batch"],
        where=f"batch_number={current_batch_id}",
    )
    return batch[0] if len(batch) else None


def get_current_large_batch(connection: object, sku: str) -> list:
    return get_current_batch(connection, sku, table_name=_t("large_batches"))


def amend_current_left_in_batch(connection: object, sku, correction, table_name="packeting_batches") -> [int|str, int]:
    """
    Apply the correction amount to the 'left in batch' records for batch/order tracking
    """
    # TODO: remove this, unneccessary
    # https://github.com/vitalseeds/vs-data-api/issues/23#issuecomment-1808648652
    batch_table = constants.tname(table_name)
    left_in_batch = constants.fname(batch_table, "left_in_batch")
    batch_number = constants.fname(batch_table, "batch_number")
    packed = constants.fname(batch_table, "packets")

    correction_remainder = int(correction)
    while correction_remainder:
        current_batch = get_current_batch(connection, sku, table_name)
        packets_in_batch = current_batch[packed]
        correction_result = int(current_batch["left_in_batch"]) + correction_remainder

        if correction_result < 1:
            # If there is not enough stock in the batch after amendment we will
            # need to amend next batch as well
            correction_remainder = correction_result
            # set current_batch to next
        elif correction_result > packets_in_batch:
            # Positive stock amendment exceeds size of batch
            # set current_batch to previous
            correction_remainder = correction_result - packets_in_batch
            correction_result = packets_in_batch
        else:
            # All done
            correction_remainder = 0

        batch_id = current_batch['batch_number']
        sql = f"UPDATE {batch_table} SET {left_in_batch}={correction_result} WHERE {batch_number}={batch_id}"
        cursor = connection.cursor()
        print(sql)
        cursor.execute(sql)
        print(cursor.rowcount)
        # return fmdb.select(
        #     connection,
        #     "acquisitions",
        #     ["sku", "packing_batch"],
        #     where=f"LOWER(sku)=LOWER('{sku}')",
        # )
    connection.commit()
    return current_batch, correction_result


def amend_current_left_in_large_batch(connection: object, sku, correction) -> [int | str, int]:
    return amend_current_left_in_batch(connection, sku, correction, table_name="packeting_batches")


def process_stock_corrections(stock_corrections, connection, wcapi=None):
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
        lg_updates = _check_product_updates(
            response_large,
            large_variation_corrections,
            vs_key="wc_variation_lg_id"
        )
        log.debug(lg_updates)
        uploaded_corrections.extend(lg_updates)
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
    uploaded_corrections = process_stock_corrections(stock_corrections, connection, wcapi)

    _set_wc_stock_updated_flag(connection, uploaded_corrections)

    # import pickle
    # from os.path import exists
    # stock_corrections_pickle = "tmp/stock_corrections.pickle"
    # if exists(stock_corrections_pickle):
    #     with open(stock_corrections_pickle, 'rb') as file:
    #         stock_corrections = pickle.load(file)
    # else:
    #     with open(stock_corrections_pickle, 'wb') as file:
    #         pickle.dump(stock_corrections, file)

    # from os.path import exists
    # uploaded_corrections_pickle = "tmp/uploaded_corrections.pickle"
    # if exists(uploaded_corrections_pickle):
    #     with open(uploaded_corrections_pickle, 'rb') as file:
    #         uploaded_corrections = pickle.load(file)
    # else:
    #     with open(uploaded_corrections_pickle, 'wb') as file:
    #         pickle.dump(uploaded_corrections, file)

    # print(stock_corrections)
    # print(uploaded_corrections_pickle)

    # For each uploaded correction
    corrections = {c["id"]: c for c in stock_corrections}
    print(uploaded_corrections)

    for correction_id in uploaded_corrections:
        correction = corrections[correction_id]
        log.info(correction)
        #   Get current batch
        if correction["large_packet_correction"]:
            log.info("large_packet_correction")

            #
            current_batch, left_in_batch = amend_current_left_in_large_batch(
                connection,
                correction["sku"],
                # correction["stock_change"]
                100
            )
            print(current_batch)
            print(left_in_batch)
            continue
            # Amend 'left in batch' value

        # current_batch_id = get_current_batch_id(connection, correction["sku"])
        log.info("regular_packet_correction")
        current_batch, left_in_batch = amend_current_left_in_batch(
            connection,
            correction["sku"],
            correction["stock_change"]
        )
        log.debug(current_batch)
        log.debug(left_in_batch)
        # Amend 'left in batch' value

    # TODO: Also update stock value in FM directly from woocommerce value (lg/reg)
    # This will negate requirement for a preceding 'update stock' FM script

    return uploaded_corrections
