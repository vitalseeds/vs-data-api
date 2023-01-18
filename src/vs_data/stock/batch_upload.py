"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

from rich import print
from vs_data.cli.table import display_table
from vs_data.fm import db as fmdb
from vs_data.fm import constants
from collections import defaultdict

WC_MAX_API_RESULT_COUNT = 10


def get_batches_awaiting_upload(connection):
    table = "packeting_batches"
    # columns = ["awaiting_upload", "sku", "skufk", "batch_number", "packets", "to_pack"]
    columns = ["awaiting_upload", "batch_number", "sku", "packets"]
    awaiting = constants.fname("packeting_batches", "awaiting_upload")
    where = f"{awaiting}='yes'"
    return fmdb.select(connection, table, columns, where)


def get_batches_awaiting_upload_join_acq(connection):
    table = "packeting_batches"
    # columns = ["awaiting_upload", "sku", "skufk", "batch_number", "packets", "to_pack"]
    columns = ["awaiting_upload", "batch_number", "packets", "sku", "wc_product_id"]
    # column_map = {c: constants.fname(table, c) for c in columns}
    awaiting = constants.fname("packeting_batches", "awaiting_upload")
    where = f"{awaiting}='yes'"

    sql = (
        "SELECT B.awaiting_upload,B.batch_number, B.packets, A.sku, A.wc_product_id  "
        'FROM "packeting_batches" B '
        'LEFT JOIN "acquisitions" A ON B.sku = A.SKU '
        "WHERE awaiting_upload='yes' "
    )
    print(sql)
    rows = connection.cursor().execute(sql).fetchall()
    return [dict(zip(columns, r)) for r in rows]


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


def get_products_in_stock(wcapi):
    return wcapi.get(
        "products",
        params={
            "stock_status": "instock",
            "per_page": WC_MAX_API_RESULT_COUNT,
            "page": 10,
        },
    )


def get_products_by_id(wcapi, ids):
    ids = [str(id) for id in ids]
    comma_separated_ids = ",".join(ids)
    products = wcapi.get(
        "products",
        params={"include": comma_separated_ids, "per_page": 100},
    )
    return products.json() if products else None


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
    # product_stock = {p["id"]: p["stock_quantity"] for p in products}
    return products.json()


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
def update_wc_stock_for_new_batches(connection, wcapi=None, debug=False):
    # batches = get_batches_awaiting_upload(connection)[:1]
    batches = get_batches_awaiting_upload_join_acq(connection)
    if debug:
        print("Batches awaiting upload")
        print(batches)

    # Get current wc stock quantity
    batch_product_ids = [b["wc_product_id"] for b in batches]
    products = get_products_by_id(wcapi, batch_product_ids)
    if debug:
        print("Current WC product stock")
        print(
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

    # Check that the batches have updated correctly on WC
    # print(response)
    for product in response["update"]:
        print(f'{product["id"]}: {product["stock_quantity"]}')

    # updated_products = {
    #     p["id"]: p["stock_quantity"] for p in get_products_by_id(wcapi, batch_product_ids)
    # }
    # for product in product_updates:
    #     if product["stock_quantity"] == :
    # if debug:
    #     print("Updated WC product stock")
    #     print(
    #         [{"stock": p["stock_quantity"], "sku": p["sku"]} for p in updated_products]
    #     )


def get_product_sku_map_from_linkdb(fmlinkdb):
    table = "link:Products"
    columns = ["link_wc_product_id", "sku", "name"]
    products = fmdb.select(fmlinkdb, table, columns)
    return products


def get_acquisitions_sku_map_from_vsdb(connection):
    table = "Acquisitions"
    columns = ["sku", "crop", "wc_product_id"]
    products = fmdb.select(connection, table, columns)
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
