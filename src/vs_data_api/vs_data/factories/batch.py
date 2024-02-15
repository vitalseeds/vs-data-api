import datetime

from pypika import Field, Order, Query, Schema, Table, Tables

from vs_data_api.vs_data import log
from vs_data_api.vs_data.factories.utils import param_types_from_var


# TODO: batch factory
def create_batch_for_upload(vsdb_connection, batch_number):
    sku = "TEST_SKU"
    packets = 10
    awaiting_upload = "yes"
    wc_product_id = 12345
    pack_date = datetime.date.today()

    sql = "INSERT INTO packeting_batches (sku, batch_number, packets, awaiting_upload, pack_date) VALUES (?, ?, ?, ?, ?)"
    values = (sku, batch_number, packets, awaiting_upload, pack_date)

    # sql = (
    #     "INSERT INTO packeting_batches (sku, batch_number, packets, awaiting_upload) "
    #     f"VALUES ('{sku}', {batch_number}, {packets}, '{awaiting_upload}')"
    # )
    # log.debug(sql)
    log.debug(sql)
    cursor: pyodbc.Cursor = vsdb_connection.cursor()

    cursor.execute(param_types_from_var(sql, values))
    # cursor.execute(sql, *values)
    cursor.commit()
