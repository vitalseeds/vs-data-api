"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

import os
from collections import defaultdict
from datetime import datetime
from textwrap import dedent

from pypika import Query, Table

from vs_data_api.vs_data import log
from vs_data_api.vs_data.fm import constants
from vs_data_api.vs_data.fm import db as fmdb
from vs_data_api.vs_data.fm.constants import fname as _f
from vs_data_api.vs_data.fm.constants import get_fm_table_column_aliases
from vs_data_api.vs_data.fm.constants import tname as _t
from vs_data_api.vs_data.stock.batch_upload import wc_large_product_update_stock, wc_regular_product_update_stock

WC_MAX_API_RESULT_COUNT = 100
LARGE_VARIATION_SKU_SUFFIX = "Gr"
PACK_SIZE_OPTIONS = {
    "regular": "Regular packet",
    "large": "Large pack",
}
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin")


def get_unprocessed_stock_corrections_join_acq_stock(connection):
    columns = [
        "id",
        "sku",
        "large_packet_correction",
        "stock_change",
        "comment",
        "create_line_item",
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
        "SELECT SC.id, SC.sku, sc.large_packet_correction, sc.stock_change, sc.comment, sc.create_line_item, "
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


def _set_vs_stock_updated_flag(connection, correction_ids=None):
    if not correction_ids:
        return

    table_name = "stock_corrections"
    fm_table = _t(table_name)
    vs_stock_updated = _f(table_name, "vs_stock_updated")
    id = _f(table_name, "id")
    sql = ""
    for correction in correction_ids:
        try:
            sql = f"UPDATE {fm_table} SET {vs_stock_updated}=1 WHERE {id} = {correction}"
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
    uploaded_corrections = [c["id"] for c in corrections if int(c[vs_key]) in updated_products]
    log.debug(uploaded_corrections)
    return uploaded_corrections


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


# def get_current_batch(connection: object, sku: str) -> list:
#     current_batch_id = get_current_batch_id(connection, sku)
#     log.info(current_batch_id)
#     # TODO: join batch to get 'left in batch' value
#     batch = fmdb.select(
#         connection,
#         "packeting_batches",
#         ["batch_number", "sku", "packets", "left_in_batch"],
#         where=f"batch_number={int(current_batch_id)}",
#     )
#     log.info(batch)
#     return batch[0] if len(batch) else None


# def get_current_large_batch(connection: object, sku: str) -> list:
#     current_batch_id = get_current_batch_id(connection, sku, field_name="large_packing_batch")
#     log.info(current_batch_id)
#     # TODO: join batch to get 'left in batch' value
#     batch = fmdb.select(
#         connection,
#         "large_batches",
#         ["batch_number", "sku", "packets", "left_in_batch"],
#         # Large batch ID is a string eg  'gr1234'
#         where=f"batch_number='{current_batch_id.upper()}'",
#     )
#     log.info(batch)
#     return batch[0] if len(batch) else None


def amend_left_in_batch(connection: object, sku, correction, large_batch=False) -> [int | str, int]:
    """
    Apply the correction amount to the 'left in batch' records for batch/order tracking
    """
    table_name = "large_batches" if large_batch else "packeting_batches"
    batch_table = constants.tname(table_name)

    left_in_batch = constants.fname(batch_table, "left_in_batch")
    batch_number = constants.fname(batch_table, "batch_number")

    if large_batch:
        current_batch_id = get_current_large_batch_id(connection, sku)
    else:
        current_batch_id = get_current_batch_id(connection, sku)
    if not current_batch_id:
        log.warn(f"current_batch not found for {sku} (large_batch={large_batch})")
        # It is possible for there not to be a current batch, eg product is a calendar
        return None

    if large_batch:
        # large batch uses string as ID eg 'GR1234'
        sql = f"UPDATE {batch_table} SET {left_in_batch}={left_in_batch} + {int(correction)} WHERE {batch_number}='{current_batch_id}'"
    else:
        sql = f"UPDATE {batch_table} SET {left_in_batch}={left_in_batch} + {int(correction)} WHERE {batch_number}={current_batch_id}"

    cursor = connection.cursor()
    log.debug(sql)
    cursor.execute(sql)
    connection.commit()
    return current_batch_id


def amend_left_in_large_batch(connection: object, sku, correction) -> [int | str, int]:
    return amend_left_in_batch(connection, sku, correction, large_batch=True)


def push_stock_corrections(stock_corrections, connection, wcapi=None):
    # Separate large and regular packet stock corrections
    # validate that product actually has a product/variation
    regular_product_corrections = [
        sc for sc in stock_corrections if not sc["large_packet_correction"] and sc["wc_product_id"]
    ]
    large_variation_corrections = [
        sc for sc in stock_corrections if sc["large_packet_correction"] and sc["wc_variation_lg_id"]
    ]
    invalid_variation_corrections = [
        sc["sku"] for sc in stock_corrections if sc["large_packet_correction"] and not sc["wc_variation_lg_id"]
    ]

    wc_product_ids = [c["wc_product_id"] for c in regular_product_corrections]
    lg_variation_id_map = {c["wc_product_id"]: c["wc_variation_lg_id"] for c in large_variation_corrections}

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
    if wc_product_ids and (products_stock := get_wc_products_by_id(wcapi, wc_product_ids)):
        regular_stock_increments = _total_stock_increments(regular_product_corrections)
        # log.debug(products_stock)
        log.debug(regular_stock_increments)
        response_regular = wc_regular_product_update_stock(wcapi, products_stock, regular_stock_increments)
        uploaded_corrections.extend(_check_product_updates(response_regular, regular_product_corrections))

    # Get current wc stock quantity for large variations
    if lg_variation_id_map:
        products_large_variation_stock = get_wc_large_variations_stock(wcapi, lg_variation_id_map)
        large_stock_increments = _total_stock_increments(large_variation_corrections)
        log.debug(large_stock_increments)
        lg_variation_ids = {c["wc_product_id"]: c["wc_variation_lg_id"] for c in large_variation_corrections}
        response_large = wc_large_product_update_stock(
            wcapi,
            products_large_variation_stock,
            large_stock_increments,
            lg_variation_ids,
        )
        lg_updates = _check_product_updates(response_large, large_variation_corrections, vs_key="wc_variation_lg_id")
        log.debug(lg_updates)
        uploaded_corrections.extend(lg_updates)
    log.debug(uploaded_corrections)
    return uploaded_corrections


def amend_local_stock(connection, local_stock_amend: dict, local_large_stock_amend: dict):
    """
    Set the stock value for a sku in the local database to reflect the uploaded
    stock amendment.

    This value will be overwritten once a day anyway when stock values are
    updated from WC.

    Accepts a dict for regular/large products in the form {sku: stock_change}
    """

    def _update_stock_field(sku, field_name, stock_change):
        log.debug(sku)
        log.debug(stock_change)
        field_name = _f("stock", field_name)
        update_query = dedent(
            f"""
        UPDATE {_t("stock")}
        SET {field_name} = {field_name} + {stock_change}
        WHERE LOWER(sku)=LOWER('{sku}')
        """
        )
        cursor = connection.cursor()
        cursor.execute(update_query)
        connection.commit()

    for sku in local_stock_amend:
        stock_change = int(local_stock_amend[sku])
        _update_stock_field(sku, "stock_regular", stock_change)

    for sku in local_large_stock_amend:
        stock_change = int(local_large_stock_amend[sku])
        _update_stock_field(sku, "stock_large", stock_change)


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
    log.info("Applying stock corrections")
    stock_corrections = get_unprocessed_stock_corrections_join_acq_stock(connection)

    if not stock_corrections:
        log.info("No stock corrections await processing")
        return False

    log.info(f"Applying {len(stock_corrections)} stock_corrections")
    log.debug("stock_corrections:")
    log.debug(stock_corrections)
    uploaded_corrections = push_stock_corrections(stock_corrections, connection, wcapi)
    if not uploaded_corrections:
        return []

    # IMPORTANT: updated flag prevents the correction being re-run
    _set_wc_stock_updated_flag(connection, uploaded_corrections)

    # For each uploaded correction
    corrections = {c["id"]: c for c in stock_corrections}

    # todays_date = datetime.now().strftime('%d/%m/%Y')
    todays_date = datetime.now().strftime("%Y/%m/%d")

    line_item_inserts = []
    local_stock_amend = defaultdict(lambda: 0)
    local_large_stock_amend = defaultdict(lambda: 0)
    for correction_id in uploaded_corrections:
        correction = corrections[correction_id]
        #  Example
        # {
        #     'id': 9,
        #     'sku': 'BeBO',
        #     'large_packet_correction': None,
        #     'stock_change': 3.0,
        #     'wc_stock_updated': None,
        #     'vs_stock_updated': None,
        #     'wc_product_id': 10351,
        #     'wc_variation_lg_id': 55146,
        #     'stock_regular': 155,
        #     'stock_large': -1
        # }
        log.info(correction)
        if correction["large_packet_correction"]:
            log.info("large_packet_correction")
            pack_size = PACK_SIZE_OPTIONS["large"]
            # Add up stock changes to apply locally (possible more than one per product)
            local_large_stock_amend[correction["sku"]] += correction["stock_change"]
            amend_left_in_large_batch(connection, correction["sku"], correction["stock_change"])
            stock_level = correction["stock_large"] + correction["stock_change"]
        else:
            log.info("regular_packet_correction")
            pack_size = PACK_SIZE_OPTIONS["regular"]
            # Add up stock changes to apply locally (possible more than one per product)
            local_stock_amend[correction["sku"]] += correction["stock_change"]
            amend_left_in_batch(connection, correction["sku"], correction["stock_change"])
            stock_level = correction["stock_regular"] + correction["stock_change"]

        # quantity in line items table represents order quantity
        # rather than resultant change to stock, so inverse it for use in audit line item
        correction_quantity = correction["stock_change"] * -1

        if correction["create_line_item"]:
            line_item_inserts.append(
                (
                    correction["sku"],  # sku
                    pack_size,  # pack_size
                    f"DATE '{todays_date}'",  # date
                    correction_quantity,  # quantity
                    ADMIN_EMAIL,  # email
                    # correction["item_cost"],  # item_cost
                    correction["id"],  # correction_id
                    f"{correction['comment']}",  # note
                    "Correction",  # transaction_type
                    stock_level,  # stock_level
                )
            )

    amend_local_stock(connection, local_stock_amend, local_large_stock_amend)

    log.info(line_item_inserts)
    # TODO: this is unreadable - should probably use dict for line items
    # Create string for 'VALUES' component of insert query
    # Quote string values
    insert_rows = [
        f"('{l[0]}', '{l[1]}', {l[2]}, {int(l[3])}, '{l[4]}', {l[5]}, '{l[6]}', '{l[7]}', {int(l[8])})"
        for l in line_item_inserts  # noqa
    ]
    insert_string = ", ".join(insert_rows)
    log.debug(insert_rows)
    log.debug(insert_string)

    insert_query = dedent(
        f"""
    INSERT INTO {_t("line_items")}
    (
        {_f("line_items", "sku")},
        {_f("line_items", "pack_size")},
        "{_f("line_items", "date")}",
        {_f("line_items", "quantity")},
        {_f("line_items", "email")},
        {_f("line_items", "correction_id")},
        {_f("line_items", "note")},
        {_f("line_items", "transaction_type")},
        {_f("line_items", "stock_level")}
    )
    VALUES
    {insert_string}
    """
    )

    log.debug(insert_query)
    with open("tmp/insert_query.sql", "w") as file:
        file.write(insert_query + "\n")

    cursor = connection.cursor()
    cursor.execute(insert_query)
    # print(cursor.rowcount)
    connection.commit()
    _set_vs_stock_updated_flag(connection, [l[5] for l in line_item_inserts])  # noqa

    # TODO: Also update stock value in FM directly from woocommerce value (lg/reg)
    # This will negate requirement for a preceding 'update stock' FM script

    return uploaded_corrections


def get_line_items_for_stock_correction(connection, correction_id: int) -> list[dict] | None:
    """
    Get the line item created to represent a stock correction (if exists)

    Returns a list (hopefully one element) of dicts
    """
    # sql = dedent(
    #     f"""
    # SELECT * FROM {_t("line_items")}
    # WHERE {_f("line_items", "correction_id")} = {correction_id}
    # """
    # )
    # log.debug(sql)
    # cursor = connection.cursor()
    # cursor.execute(sql)
    # rows = cursor.fetchall()
    # return list(rows) if rows else None

    # TODO: This form of query should be astracted for re-use
    # TODO: Use this pattern for fm.db.select function
    line_items = Table(_t("line_items"))
    columns = get_fm_table_column_aliases("line_items")
    column_aliases = get_fm_table_column_aliases("line_items").values()
    cid = _f("line_items", "correction_id")

    q = (
        Query.from_(line_items)
        .select(*column_aliases)
        .where(
            # line_items.correction_id == correction_id
            getattr(line_items, cid) == correction_id
        )
    )
    line_items = connection.cursor().execute(q.get_sql()).fetchall()

    # TODO: validate using pydantic model once using model aliases correctly
    line_item_dicts = [dict(zip(columns.keys(), li)) for li in line_items]
    return line_item_dicts if line_item_dicts else None
