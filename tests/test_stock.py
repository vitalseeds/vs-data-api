"""Test cases for the __main__ module."""
import json

import pytest
import requests
import responses
import toml
from objexplore import explore
from responses import _recorder, matchers
from rich import print

from vs_data import log, stock

from . import _add_from_file_match_params
from . import flag_batches_for_upload

@pytest.mark.fmdb
def test_get_batches_awaiting_upload_join_acq(vsdb_connection):
    flag_batches_for_upload(vsdb_connection, [3515, 3516, 3517])
    batches = stock.batch_upload.get_batches_awaiting_upload_join_acq(vsdb_connection)
    assert batches


@pytest.mark.wcapi
def test_get_products_by_id(wcapi):
    product_ids = [5316, 1690, 1744, 1696, 10350]
    products = stock.batch_upload.get_wc_products_by_id(wcapi, product_ids)
    assert products


@pytest.mark.record
@responses._recorder.record(file_path="tests/fixtures/test_wcapi_stock_batch_awaiting_upload_wc_products.toml")
def test_record__update_wc_stock_for_new_batches(wcapi, vsdb_connection, mocked_responses):
    # TODO: mark this test 'record'
    # TODO: exclude 'record' mark from default pytest
    flag_batches_for_upload(vsdb_connection, [3515, 3516, 3517])
    stock.update_wc_stock_for_new_batches(vsdb_connection, wcapi)
    # TODO: Separate first and second requests into separate toml files


@responses.activate
def test_update_wc_stock_for_new_batches(wcapi, vsdb_connection, mocked_responses):
    # TODO: remove when vsdb connection is mocked
    flag_batches_for_upload(vsdb_connection, [3515, 3516, 3517])

    # Mock wcapi requests
    _add_from_file_match_params(responses, file_path="tests/fixtures/test_wcapi_stock/batch_awaiting_upload_wc_products.toml",
        match=[
            matchers.query_param_matcher({"include": "28388.0,1716.0,10271.0"}, strict_match=False),
        ]
    )
    responses._add_from_file(file_path="tests/fixtures/test_wcapi_stock/batch_post_product_stock.toml")

    stock.update_wc_stock_for_new_batches(vsdb_connection, wcapi)


# TEST that cache is invalidated in compare_wc_fm_stock