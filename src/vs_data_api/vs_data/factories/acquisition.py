import pypyodbc as pyodbc
from pypika import Field, Order, Query, Schema, Table, Tables

from vs_data_api.vs_data import log
from vs_data_api.vs_data.factories.utils import param_types_from_var


# TODO: acquisition factory
def create_test_acquisition(vsdb_connection):
    sku = "TEST_SKU"
    wc_product_id = 12345
    wc_variation_lg_id = 54321
    wc_variation_regular_id = 54322
    price = 9.99
    lg_variation_price = 99

    sql = (
        "INSERT INTO acquisitions (sku, wc_product_id, wc_variation_lg_id, wc_variation_regular_id) "
        f"VALUES ('{sku}', {wc_product_id}, {wc_variation_lg_id}, {wc_variation_regular_id})"
    )
    log.debug(sql)

    cursor: pyodbc.Cursor = vsdb_connection.cursor()
    cursor.execute(sql)
    cursor.commit()
