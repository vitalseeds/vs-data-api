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
from vs_data.fm import db as fmdb


WC_MAX_API_RESULT_COUNT = 10


def get_batches_awaiting_upload_join_acq(connection):
    columns = ["awaiting_upload", "batch_number", "packets", "sku", "wc_product_id"]
    awaiting = constants.fname("packeting_batches", "awaiting_upload")
    where = f"lower({awaiting})='yes'"

    sql = (
        "SELECT B.awaiting_upload,B.batch_number, B.packets, A.sku, A.wc_product_id  "
        'FROM "packeting_batches" B '
        'LEFT JOIN "acquisitions" A ON B.sku = A.SKU '
        "WHERE " + where
    )
    rows = connection.cursor().execute(sql).fetchall()
    return [dict(zip(columns, r)) for r in rows]


def unset_awaiting_upload_flag(connection, batch_ids=[]):
    assert batch_ids

    fm_table = constants.tname("packeting_batches")
    awaiting_upload = constants.fname("packeting_batches", "awaiting_upload")
    batch_number = constants.fname("packeting_batches", "batch_number")
    sql = ""
    for batch in batch_ids:
        sql = f"UPDATE {fm_table} SET {awaiting_upload}='no' WHERE {batch_number} = {batch}"
        cursor = connection.cursor()
        log.info(sql)
        cursor.execute(sql)
        log.info(cursor.rowcount)
    connection.commit()


def get_products_by_id(wcapi: object, ids: dict):
    ids = [str(id) for id in ids]
    comma_separated_ids = ",".join(ids)
    response = wcapi.get(
        "products",
        params={"include": comma_separated_ids, "per_page": 100},
    )
    if response.status_code == 200:
        return response.json()


def _total_stock_increments(batches):
    """
    Add up stock increments per sku
    in case there are multiple batches for a single product (sku)
    """
    stock_increments = defaultdict(lambda: 0)
    for batch in batches:
        stock_increments[batch["wc_product_id"]] += batch["packets"]
    return stock_increments


# TODO: improve performance of lookups from returned data
# TODO: add tests
def update_wc_stock_for_new_batches(connection, wcapi=None):
    batches = get_batches_awaiting_upload_join_acq(connection)
    if not batches:
        log.debug("No batches awaiting upload")
        return False

    log.debug("Batches awaiting upload")
    log.debug(batches)

    # Get current wc stock quantity
    batch_product_ids = [b["wc_product_id"] for b in batches]
    products = get_products_by_id(wcapi, batch_product_ids)

    if not products:
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
            for p in products
        ]
    )

    stock_increments = _total_stock_increments(batches)
    product_updates = []
    for product in products:
        current_stock_quantity = product["stock_quantity"]
        new_stock_quantity = current_stock_quantity + stock_increments[product["id"]]
        product_updates.append(
            {
                "id": product["id"],
                "stock_quantity": new_stock_quantity,
            }
        )
    data = {"update": product_updates}
    response = wcapi.post("products/batch", data).json()

    # Check response for batches whose products have had stock updated on WC
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
    unset_awaiting_upload_flag(connection, uploaded_batches)

    if len(response["update"]):
        return response["update"]


def get_product_sku_map_from_linkdb(fmlinkdb):
    table = "link:Products"
    columns = ["link_wc_product_id", "sku", "name"]
    products = fmdb.select(fmlinkdb, table, columns)
    return products


def update_acquisitions_wc_id(connection, sku_id_map):
    fm_table = constants.tname("acquisitions")
    link_wc_id = "link_wc_product_id"
    wc_id = "wc_product_id"
    sku_field = constants.fname("acquisitions", "sku")
    for row in sku_id_map:
        sql = f"UPDATE {fm_table} SET {wc_id}={row[link_wc_id]} WHERE {sku_field} = '{row['sku']}'"
        print(sql)
        cursor = connection.cursor()
        cursor.execute(sql)
        print(cursor.rowcount)
        connection.commit()
