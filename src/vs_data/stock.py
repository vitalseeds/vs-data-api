"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

from rich import print
from vs_data.utils.cli import display_table
from vs_data.utils.fm import db as fmdb
from vs_data.utils.fm import constants

WC_MAX_API_RESULT_COUNT = 10


def get_batches_awaiting_upload(connection):
    table = "packeting_batches"
    columns = ["awaiting_upload", "sku", "skufk", "batch_number", "packets", "to_pack"]
    where = "awaiting_upload='yes'"
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


def get_products_in_stock(wcapi):
    return wcapi.get(
        "products",
        params={"stock_status": "instock", "per_page": WC_MAX_API_RESULT_COUNT},
    )


def get_products_by_id(wcapi, ids):
    ids = [str(id) for id in ids]
    comma_separated_ids = ",".join(ids)
    products = wcapi.get(
        "products",
        params={"include": comma_separated_ids, "per_page": WC_MAX_API_RESULT_COUNT},
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


def update_wc_stock_for_new_batches(connection, wcapi=None):
    # headers, batches = get_batches_awaiting_upload(connection)
    batches = get_batches_awaiting_upload(connection)
    print(batches)

    # lg_batches = get_large_batches_awaiting_upload(connection)
    # print(lg_batches)

    # ids = [str(id) for id in ids]
    # comma_separated_ids = ",".join(ids)
    # products = wcapi.get(
    #     "products",
    #     params={"include": comma_separated_ids, "per_page": 100},
    # )
    # return products.json() if products else None

    # variations = wcapi.get(
    #     f"products/{product_skus[2]['_kf_WooCommerceID']}/variations"
    # ).json()

    # print([{"id": v["id"], "sku": v["sku"]} for v in variations])

    # print(wcapi.get(f"products/{product_skus[0]['_kf_WooCommerceID']}").json())

    # print(wcapi.get(f"products").json())

    # overlaps = []
    # for p in product_skus:
    #     if match := [v for v in variation_skus if v["SKU"] == p["SKU"]]:
    #         overlaps.append({"product": p, "variation": match})

    # print("[red]OVERLAPS")
    # print(overlaps)
    # print(len(overlaps))

    # wcapi = ctx.parent.obj["wcapi"]
    # display_table(batches)


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
