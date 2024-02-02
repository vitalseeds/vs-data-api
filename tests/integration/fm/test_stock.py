"""Test cases for the __main__ module."""
import datetime
import json

import pypyodbc as pyodbc
import pytest
import requests
import responses
import toml
from fastapi.testclient import TestClient
from pypika import Field, Order, Query, Schema, Table, Tables

# from objexplore import explore
from responses import _recorder, matchers
from rich import print

from tests import _add_from_file_match_params, flag_only_test_batches_for_upload
from vs_data_api.vs_data import log, stock
from vs_data_api.vs_data.fm.constants import fname as _f

TEST_BATCH_ID = 99999


# TODO: Move this to a method on a cursor class to overload pypypyodbc cursor
def param_types_from_var(sql_string: str, values: tuple):
    """
    FileMaker ODBC does not tell us what types the fields are, so quote them etc
    using argument type instead.

    (see pypyodbc for 'self.connection.support_SQLDescribeParam')
    """
    quoted_values = []
    for value in values:
        if isinstance(value, str):
            quoted_values.append(f"'{value}'")
            continue
        # TODO: test for formatting dates
        elif isinstance(value, datetime.datetime):
            quoted_values.append(f"TIMESTAMP '{value.strftime('%Y-%m-%d %H:%M:%S')}'")
        elif isinstance(value, datetime.date):
            quoted_values.append(f"DATE '{value.strftime('%Y/%m/%d')}'")
        quoted_values.append(value)

    # We used the ? placeholder for compatibility with pyodbc, so replace with {} for .format
    return sql_string.replace("?", "{}").format(*quoted_values)


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


def get_test_batch(vsdb_connection, batch_number):
    # awaiting = _f("packeting_batches", "awaiting_upload")
    # # where = f"lower({awaiting})='yes' AND b.pack_date IS NOT NULL"
    # where = f"lower({awaiting})='yes' AND B.batch_number = {batch_number}"
    # where = f"lower({awaiting})='yes' AND B.sku = 'TEST_SKU'"

    # sql = (
    #     "SELECT B.awaiting_upload,B.batch_number, B.packets, A.sku, A.wc_product_id  "
    #     'FROM "packeting_batches" B '
    #     'LEFT JOIN "acquisitions" A ON B.sku = A.SKU '
    #     f"WHERE {where} "
    #     "ORDER BY B.batch_number DESC "
    #     # "FETCH FIRST 10 ROWS ONLY "
    # )
    # log.debug(sql)

    packeting_batches, acquisitions = Tables("packeting_batches", "acquisitions")
    sql = Query.from_("packeting_batches").select("awaiting_upload", "batch_number", "packets").where(
        packeting_batches.awaiting_upload == "yes"
    ).where(
        packeting_batches.batch_number == TEST_BATCH_ID
    ).orderby("id", order=Order.desc)


    rows = vsdb_connection.cursor().execute(sql.get_sql()).fetchall()
    log.info(rows)
    return rows


def delete_test_batch(vsdb_connection, batch_number):
    sql = f'DELETE FROM "packeting_batches" WHERE batch_number = {batch_number} '
    log.debug(sql)
    vsdb_connection.cursor().execute(sql).commit()


def delete_test_acquisition(vsdb_connection, sku):
    sql = f"DELETE FROM \"acquisitions\" WHERE sku = '{sku}'"
    log.debug(sql)
    vsdb_connection.cursor().execute(sql).commit()


@pytest.mark.fmdb
def test_get_batches_awaiting_upload_join_acq(vsdb_connection):

    delete_test_batch(vsdb_connection, TEST_BATCH_ID)
    delete_test_acquisition(vsdb_connection, "TEST_SKU")

    create_test_acquisition(vsdb_connection)
    create_batch_for_upload(vsdb_connection, TEST_BATCH_ID)

    test_batch = get_test_batch(vsdb_connection, TEST_BATCH_ID)
    assert test_batch
    assert len(test_batch)==1
    log.info(test_batch)

    flag_only_test_batches_for_upload(vsdb_connection, [TEST_BATCH_ID])

    batches = stock.batch_upload.get_batches_awaiting_upload_join_acq(vsdb_connection)
    assert batches
    assert len(batches)==1


@pytest.mark.wcapi
def test_get_products_by_id(wcapi):
    product_ids = [5316, 1690, 1744, 1696, 10350]
    products = stock.batch_upload.get_wc_products_by_id(wcapi, product_ids)
    assert products


@pytest.mark.fmdb
@pytest.mark.record
@responses._recorder.record(file_path="tests/fixtures/test_wcapi_stock_batch_awaiting_upload_wc_products.toml")
def test_record__update_wc_stock_for_new_batches(wcapi, vsdb_connection, mocked_responses):
    # TODO: mark this test 'record'
    # TODO: exclude 'record' mark from default pytest
    flag_only_test_batches_for_upload(vsdb_connection, [3515, 3516, 3517])
    stock.update_wc_stock_for_new_batches(vsdb_connection, wcapi)
    # TODO: Separate first and second requests into separate toml files


@pytest.mark.fmdb
@pytest.mark.wcapi
@responses.activate
def test_update_wc_stock_for_new_batches(wcapi, vsdb_connection, mocked_responses):
    # TODO: remove when vsdb connection is mocked
    flag_only_test_batches_for_upload(vsdb_connection, [3515, 3516, 3517])

    # # Mock wcapi requests
    # _add_from_file_match_params(
    #     responses,
    #     file_path="tests/fixtures/test_wcapi_stock/batch_awaiting_upload_wc_products.toml",
    #     match=[
    #         matchers.query_param_matcher({"include": "28388.0,1716.0,10271.0"}, strict_match=False),
    #     ],
    # )
    # responses._add_from_file(file_path="tests/fixtures/test_wcapi_stock/batch_post_product_stock.toml")

    stock.update_wc_stock_for_new_batches(vsdb_connection, wcapi)

# todo: TEST that cache is invalidated in compare_wc_fm_stock


def test_fastapi_client(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "VS Data API running",
    }


def test_upload_wc_stock__none(client: TestClient):
    response = client.get("/batch/upload-wc-stock")
    assert response.status_code == 200
    assert response.json() == {"message": "No batches were updated on WooCommerce"}


def test_upload_wc_large_stock__none(client: TestClient):
    response = client.get("/batch/upload-wc-stock/variation/large")
    assert response.status_code == 200
    assert response.json() == {"message": "No large batches were updated on WooCommerce"}
