"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

from rich import print
from vs_data.utils.cli import display_table

WC_MAX_API_RESULT_COUNT = 10


def get_batches_awaiting_upload(fmdb):
    table = "Packeting Batches"
    columns = ["Awaiting_upload", "Batch Number", "Packets", "To pack"]
    field_list = ",".join([f'"{f}"' for f in columns])
    where = "Awaiting_upload='yes'"
    sql = f'SELECT {field_list} FROM "{table}" WHERE {where}'
    print(sql)
    return columns, fmdb.execute(sql).fetchall()


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
    May need to fetch them all and write to db? Otherwise map to product ID
    Believe currently link_db stores the map of product id to SKU
    """
    if not sku:
        return
    sku = "ChTr"
    # products = wcapi.get("products", params={"sku": sku})
    products = wcapi.get(
        "products",
        params={"sku": sku},
    )
    products = products.json()
    # product_stock = {p["id"]: p["stock_quantity"] for p in products}
    products


def update_wc_stock_from_batch(fmdb, wcapi=None):
    headers, batches = get_batches_awaiting_upload(fmdb)
    display_table(headers, batches)


# def get_seed_lot(fmdb):
#     # table = "Packeting Batches"
#     # table_alias = "p"
#     columns = [
#         "Awaiting_upload",
#         "Batch Number",
#         "Packets",
#         "To pack",
#         "SKU",
#         "Cost of seed",
#     ]
#     # columns = [f"{table_alias}.{c}" for c in columns]
#     # field_list = ",".join([f'"{f}"' for f in columns])
#     # where = "Awaiting_upload='yes'"
#     # sql = f'SELECT {field_list} FROM "{table}" as {table_alias} WHERE {where}'
#     # sql = 'SELECT "Awaiting_upload","Batch Number","Packets","To pack" FROM "Packeting Batches" WHERE Awaiting_upload=\'yes\' '
#     # 'UNION SELECT "SKU", "SKU_lrg" FROM Aquisitions'
#     sql = 'SELECT "Awaiting_upload","Batch Number","Packets","To pack","SKU", "SeedLotFK" FROM "Packeting Batches" JOIN "Seed Lots" ON "Seed Lots"."Lot number"="Packeting Batches"."SeedLotFK" WHERE Awaiting_upload=\'yes\' '
#     print(sql)
#     return columns, fmdb.execute(sql).fetchall()

# From FM 14 pdf
# SELECT *
# FROM Salespeople LEFT OUTER JOIN Sales_Data
# ON Salespeople.Salesperson_ID = Sales_Data.Salesperson_ID
