"""Test cases for the __main__ module."""
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
from vs_data_api.vs_data.factories import (
    create_stock_correction,
    delete_test_stock_corrections,
)
from vs_data_api.vs_data.fm.constants import fname as _f
from vs_data_api.vs_data.stock.corrections import apply_corrections_to_wc_stock

TEST_CORRECTION_ID = 99999
TEST_COMMENT = "TEST CORRECTION"


# @pytest.mark.fmdb
def test_apply_stock_corrections(wcapi, vsdb_connection):

    delete_test_stock_corrections(vsdb_connection, TEST_COMMENT)
    correction = create_stock_correction(vsdb_connection)
    correction2 = create_stock_correction(vsdb_connection, {
        "id": 1234,
        "sku": "BRSE",
        "create_line_item": None,
        "comment": TEST_COMMENT,
    })
    assert correction

    applied_corrections = stock.apply_corrections_to_wc_stock(vsdb_connection, wcapi)

    assert applied_corrections
    assert applied_corrections[0] == correction.id
    assert applied_corrections[1] == correction2.id
    # Will fail if test database has other corrections ready to upload
    assert applied_corrections == [123, 1234]

# @pytest.mark.wcapi
# def test_get_products_by_id(wcapi):
#     product_ids = [5316, 1690, 1744, 1696, 10350]
#     products = stock.batch_upload.get_wc_products_by_id(wcapi, product_ids)
#     assert products
