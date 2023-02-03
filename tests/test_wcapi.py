"""Test cases for the __main__ module."""
import pytest
from vs_data import stock, log
from vs_data.fm import constants
import toml
import json
from rich import print

import responses
from responses import _recorder
import requests

# import betamax
# CASSETTE_LIBRARY_DIR = "tests/fixtures/cassettes2"



# @pytest.mark.wcapi
# def test_get_products_by_id(wcapi):
#     product_ids = [5316, 1690, 1744, 1696, 10350]
#     products = stock.batch_upload.get_products_by_id(wcapi, product_ids)
#     # log.debug(products)
#     assert products



def flag_batches_for_upload(connection):
    fm_table = constants.tname("packeting_batches")
    awaiting_upload = constants.fname("packeting_batches", "awaiting_upload")
    batch_number = constants.fname("packeting_batches", "batch_number")
    sql = ""
    for batch in [3515, 3516, 3517]:
        sql = f"UPDATE {fm_table} SET {awaiting_upload}='Yes' WHERE {batch_number} = {batch}"
        cursor = connection.cursor()
        log.info(sql)
        cursor.execute(sql)
        log.info(cursor.rowcount)
    connection.commit()

# @responses._recorder.record(file_path="tests/fixtures/batch_awaiting_upload_wc_products.json")
@responses.activate
def test_update_wc_stock_for_new_batches(wcapi, vsdb_connection, mocked_responses):
    flag_batches_for_upload(vsdb_connection)
    # responses.patch("http://vitalseedscouk.local/wp-json/wc/v3/products?include=28388.0%2C1716.0%2C10271.0")
    # responses.get("http://vitalseedscouk.local/wp-json/wc/v3/products")
    responses.get("http://vitalseedscouk.local")
    responses.patch("http://vitalseedscouk.local/wp-json/wc/v3/products/batch")
    responses._add_from_file(file_path="tests/fixtures/batch_awaiting_upload_wc_products.json")
    stock.update_wc_stock_for_new_batches(vsdb_connection, wcapi)


# def test_api(mocked_responses):
#     mocked_responses.get(
#         "http://twitter.com/api/1/foobar",
#         body="{}",
#         status=200,
#         content_type="application/json",
#     )
#     resp = requests.get("http://twitter.com/api/1/foobar")
#     assert resp.status_code == 200
