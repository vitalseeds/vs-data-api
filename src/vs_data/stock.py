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


def update_wc_stock_from_batch(fmdb, wcapi=None):
    print("Updating stock")
    headers, batches = get_batches_awaiting_upload(fmdb)
    display_table(headers, batches)
