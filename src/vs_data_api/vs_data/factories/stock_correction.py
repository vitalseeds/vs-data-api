import pypyodbc as pyodbc
from pypika import Order, Query, Table

from vs_data_api.vs_data import log
from vs_data_api.vs_data.fm.constants import tname as _t
from vs_data_api.vs_data.fm.vs_tables import StockCorrections

stock_corrections = Table(_t("stock_corrections"))


def create_stock_correction(vsdb_connection, values={}, test_comment="TEST CORRECTION"):
    data = {
        "id": 123,
        "sku": "BeBo",
        "large_packet_correction": None,
        "stock_change": 12,
        "wc_stock_updated": None,
        "vs_stock_updated": None,
        # "create_line_item": 1,
        "comment": test_comment,
    }
    data.update(values)

    q = Query.into(stock_corrections).columns(*data.keys()).insert(*data.values())
    vsdb_connection.cursor().execute(q.get_sql()).commit()

    q = Query.from_(stock_corrections).select(*data.keys()).where(
        stock_corrections.comment == test_comment
    ).orderby("id", order=Order.desc)
    correction = vsdb_connection.cursor().execute(q.get_sql()).fetchone()
    return StockCorrections(**dict(zip(data.keys(), correction)))


def delete_test_stock_corrections(vsdb_connection, test_comment="TEST CORRECTION"):
    q = Query.from_(stock_corrections).delete().where(stock_corrections.comment == test_comment)
    result = vsdb_connection.cursor().execute(q.get_sql()).commit()
    log.info(result)
