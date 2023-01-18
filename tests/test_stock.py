"""Test cases for the __main__ module."""
import pytest
from vs_data import stock


@pytest.mark.fmdb
def test_get_acquisitions_sku_map_from_vsdb(vsdb_connection):
    aquisitions = stock.get_acquisitions_sku_map_from_vsdb(vsdb_connection)
    assert aquisitions
    # from rich import print
    # print(aquisitions[:10])
