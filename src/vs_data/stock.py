"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

from rich import print
from vs_data.utils.cli import display_table


def get_batches_awaiting_upload(fmdb):
    table = "Packeting Batches"
    columns = ["Awaiting_upload", "Batch Number", "Packets", "To pack"]
    field_list = ",".join([f'"{f}"' for f in columns])
    where = "Awaiting_upload='yes'"
    sql = f'SELECT {field_list} FROM "{table}" WHERE {where}'
    print(sql)
    return columns, fmdb.execute(sql).fetchall()


def get_batches_awaiting_upload(fmdb):
    table = "Packeting Batches"
    # table_alias = "p"
    columns = [
        "Awaiting_upload",
        "Batch Number",
        "Packets",
        "To pack",
        "SKUFK",
    ]
    # columns = [f"{table}.{c}" for c in columns]
    field_list = ",".join([f'"{f}"' for f in columns])
    print(field_list)
    where = "Awaiting_upload='yes'"
    sql = f'SELECT {field_list} FROM "{table}" WHERE {where}'
    # sql = 'SELECT "Awaiting_upload","Batch Number","Packets","To pack" FROM "Packeting Batches" WHERE Awaiting_upload=\'yes\' '
    # 'UNION SELECT "SKU", "SKU_lrg" FROM Aquisitions'
    print(sql)

    return columns, fmdb.execute(sql).fetchall()


def get_wp_stock(wcapi):
    print(wcapi.get("products"))


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


def update_wc_stock_from_batch(fmdb, wcapi=None):
    print("Updating stock")
    headers, batches = get_batches_awaiting_upload(fmdb)
    get_wp_stock(wcapi)
    # print(headers, batches)
    # display_table(headers, batches)
