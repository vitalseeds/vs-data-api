"""Test cases for the __main__ module."""

import pypyodbc as pyodbc
import pytest


# @pytest.mark.fmdb
# def test_get_batches_awaiting_upload_join_acq(vsdb_connection):
#     flag_batches_for_upload(vsdb_connection, [3515, 3516, 3517])
#     batches = stock.batch_upload.get_batches_awaiting_upload_join_acq(vsdb_connection)
#     assert batches


ACQUISITIONS_SCHEMA = {
    "sku": "TEXT NOT NULL",
    "crop": "TEXT",
    "wc_product_id": "INTEGER",
    "wc_variation_lg_id": "INTEGER",
    "wc_variation_regular_id": "INTEGER",
    "not_selling_in_shop": "TEXT",
}
ACQUISITIONS_COLUMNS = ACQUISITIONS_SCHEMA.keys()

pytestmark = [pytest.mark.fmdb]


def test_connect_to_filemaker(vsdb_connection):
    """
    Tests that can access filemaker over ODBC
    """
    assert isinstance(vsdb_connection, pyodbc.Connection)
