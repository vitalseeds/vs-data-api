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

WC_MAX_API_RESULT_COUNT = 100


def get_batches_awaiting_upload_join_acq(connection):
    # TODO: should get sku from join on seed_lot, not packeting_batches
    columns = ["awaiting_upload", "batch_number", "packets", "sku", "wc_product_id"]
    awaiting = _f("packeting_batches", "awaiting_upload")
    where = f"lower({awaiting})='yes' AND b.pack_date IS NOT NULL"

    sql = (
        "SELECT B.awaiting_upload,B.batch_number, B.packets, A.sku, A.wc_product_id  "
        'FROM "packeting_batches" B '
        'LEFT JOIN "acquisitions" A ON B.sku = A.SKU '
        "WHERE " + where
    )
    rows = connection.cursor().execute(sql).fetchall()
    return [dict(zip(columns, r)) for r in rows]



def  get_large_batches_awaiting_upload_join_acq(connection: object) -> list:
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


def unset_awaiting_upload_flag(connection, batch_ids=None, large_batch=False):
    if batch_ids is None:
        batch_ids = []
    assert batch_ids

    table_name = "large_batches" if large_batch else "packeting_batches"

    fm_table = _t(table_name)
    awaiting_upload = _f(table_name, "awaiting_upload")
    batch_number = _f(table_name, "batch_number")
    sql = ""
    for batch in batch_ids:
        sql = f"UPDATE {fm_table} SET {awaiting_upload}='no' WHERE {batch_number} = {batch}"
        cursor = connection.cursor()
        log.info(sql)
        cursor.execute(sql)
        log.info(cursor.rowcount)
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


def get_wc_large_variations_by_product(wcapi: object, product_ids: list, lg_variation_ids: dict):
    """
    Gets product variations including stock quantity.

    Args:
        woocommerce api instance
        list of product ids
        large variation ids (dict) used as a map of product_id:variation_id
    """
    product_ids = [int(id) for id in product_ids]

    # products = get_wc_products_by_id(wcapi, product_ids)
    product_large_variations = {}
    for product_id in product_ids:
        large_variation_id = lg_variation_ids[product_id]
        response = wcapi.get(
            f"products/{product_id}/variations/{large_variation_id}",
            params={"per_page": WC_MAX_API_RESULT_COUNT},
        )
        if response.status_code == 200:
            stock_quantity = response.json()["stock_quantity"]
            product_large_variations[product_id] = {
                "variation_id": large_variation_id,
                "stock_quantity": stock_quantity
            }
    return product_large_variations

def _total_stock_increments(batches):
    """
    Add up stock increments per sku.

    Accounts for case that there may be multiple batches for a single product (sku).
    """
    stock_increments = defaultdict(lambda: 0)
    for batch in batches:
        stock_increments[batch["wc_product_id"]] += batch["packets"]
    return stock_increments


def wc_large_product_update_stock(wcapi, products: dict[dict], stock_increments, lg_variation_ids):
    variation_updates = []
    for product_id, product in products.items():
        current_stock_quantity = product["stock_quantity"] or 0
        new_stock_quantity = current_stock_quantity + stock_increments[product_id]

        variation_id = lg_variation_ids[product_id]
        endpoint = f"products/{product_id}/variations/{variation_id}"
        data = {
            "stock_quantity": new_stock_quantity
        }
        response = wcapi.put(endpoint, data)
        variation_updates.append(response.json())

    return {"update": variation_updates}


def wc_regular_product_update_stock(wcapi, products, stock_increments):
    product_updates = []
    for product in products:
        current_stock_quantity = product["stock_quantity"] or 0
        new_stock_quantity = current_stock_quantity + stock_increments[product["id"]]
        product_updates.append(
            {
                "id": product["id"],
                "stock_quantity": new_stock_quantity,
            }
        )
    data = {"update": product_updates}
    log.debug(data)
    return wcapi.post("products/batch", data).json()


# TODO: improve performance of lookups from returned data
# TODO: add tests
# TODO: split large_variation logic out then review duplication
def update_wc_stock_for_new_batches(connection, wcapi=None, product_variation=None):
    """
    Update WooCommerce stock from newly packated batches.

    Args:
        FileMaker db connection
        WooCommerce API instance
        Product variation ('large' or None)

    Query filemaker for new batches that are ready for upload.
    Get the current stock level for product/variation.
    Add up stock increment per product from multiple batches.
    Update the stock_quantity for the WooCommerce product/variation
    """
    large_variation = True if product_variation == "large" else False

    # Get new batches from FM
    if large_variation:
        batches = get_large_batches_awaiting_upload_join_acq(connection)
        lg_variation_ids = {b["wc_product_id"]: b["wc_variation_lg_id"] for b in batches}
    else:
        batches = get_batches_awaiting_upload_join_acq(connection)
    batch_product_ids = [b["wc_product_id"] for b in batches]

    if not batches:
        log.debug("No batches awaiting upload")
        return False

    log.debug("Batches awaiting upload")
    log.debug(batches)

    # Get current wc stock quantity
    if large_variation:
        products_large_variation_stock = get_wc_large_variations_by_product(
            wcapi,
            batch_product_ids,
            lg_variation_ids
        )
        log.debug(products_large_variation_stock)
        if not products_large_variation_stock:
            log.debug("No product variations found for batches awaiting upload")
            return False

        log.debug("Current WC product stock")
        log.debug(products_large_variation_stock)

    else:
        products_stock = get_wc_products_by_id(wcapi, batch_product_ids)
        if not products_stock:
            log.debug("No products found for batches awaiting upload")
            return False

        log.debug("Current WC product stock")
        log.debug(
            [
                {
                    "wc_product_id": p["id"],
                    "sku": p["sku"],
                    "stock": p["stock_quantity"],
                }
                for p in products_stock
            ]
        )

    stock_increments = _total_stock_increments(batches)

    if large_variation:
        response = wc_large_product_update_stock(wcapi, products_large_variation_stock, stock_increments, lg_variation_ids)
    else:
        response = wc_regular_product_update_stock(wcapi, products_stock, stock_increments)

    # Check response for batches whose products have had stock updated on WC
    if large_variation:
        updated_variations = [product["id"] for product in response["update"]]
        log.debug("updated product variations:")
        log.debug(updated_variations)
        uploaded_batches = [
            int(b["batch_number"])
            for b in batches
            if b["wc_variation_lg_id"] and int(b["wc_variation_lg_id"]) in updated_variations
        ]
        log.debug("uploaded_batches:")
        log.debug(uploaded_batches)
    else:
        updated_products = [product["id"] for product in response["update"]]
        log.debug("updated_products:")
        log.debug(updated_products)
        uploaded_batches = [
            int(b["batch_number"])
            for b in batches
            if int(b["wc_product_id"]) in updated_products
        ]
        log.debug("uploaded_batches:")
        log.debug(uploaded_batches)

    # Remove 'Awaiting upload' flag

    unset_awaiting_upload_flag(connection, uploaded_batches, large_batch=large_variation)

    if len(response["update"]):
        return response["update"]


def get_product_sku_map_from_linkdb(fmlinkdb):
    table = "link:Products"
    columns = ["link_wc_product_id", "sku", "name"]
    products = fmdb.select(fmlinkdb, table, columns)
    return products


def get_product_variation_map_from_linkdb(fmlinkdb):
    table = "link:product_variations"
    columns = ["link_wc_variation_id", "sku", "variation_option"]
    variations = fmdb.select(fmlinkdb, table, columns)
    return variations


def update_acquisitions_wc_id(connection, sku_id_map):
    fm_table = _t("acquisitions")
    link_wc_id = "link_wc_product_id"
    wc_id = "wc_product_id"
    sku_field = _f("acquisitions", "sku")
    for row in sku_id_map:
        sql = f"UPDATE {fm_table} SET {wc_id}={row[link_wc_id]} WHERE {sku_field} = '{row['sku']}'"
        print(sql)
        cursor = connection.cursor()
        cursor.execute(sql)
        print(cursor.rowcount)
        connection.commit()

def update_acquisitions_wc_variations(connection, variation_id_map):
    large_variations = [v for v in variation_id_map if v["variation_option"] == "Large pack"]
    log.debug(large_variations)
    regular_variations = [v for v in variation_id_map if v["variation_option"] == "Regular packet"]
    log.debug(regular_variations)

    fm_table = _t("acquisitions")
    wc_variation_id = "link_wc_variation_id"
    parent_product_sku = _f("acquisitions", "sku")

    large_variation_field = _f("acquisitions", "wc_variation_lg_id")
    regular_variation_field = _f("acquisitions", "wc_variation_regular_id")

    for row in large_variations:
        # The large pack variations have calculated sku based on product sku + '-Gr'
        base_sku = row['sku'].replace("-Gr", "")
        sql = f"UPDATE {fm_table} SET {large_variation_field}={row[wc_variation_id]} WHERE {parent_product_sku} = '{base_sku}'"
        print(sql)
        cursor = connection.cursor()
        cursor.execute(sql)
        print(cursor.rowcount)
        connection.commit()

    for row in regular_variations:
        # Regular pack sku should be the same as parent product
        base_sku = row['sku']
        sql = f"UPDATE {fm_table} SET {regular_variation_field}={row[wc_variation_id]} WHERE {parent_product_sku} = '{base_sku}'"
        print(sql)
        cursor = connection.cursor()
        cursor.execute(sql)
        print(cursor.rowcount)
        connection.commit()
