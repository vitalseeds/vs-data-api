"""Checks the seed_lots field names used by the lot summary against a real FileMaker."""

import pytest

from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.lots import LotSummary, get_germ_tests, get_lot_summary


@pytest.mark.fmdb
def test_lot_summary_fields_exist(vsdb_connection):
    rows = db.select(vsdb_connection, "seed_lots", ["lot_number"])
    assert rows, "seed_lots has no rows to check"
    summary = get_lot_summary(vsdb_connection, rows[0]["lot_number"])
    assert isinstance(summary, LotSummary)


@pytest.mark.fmdb
def test_germ_tests_fields_exist(vsdb_connection):
    rows = db.select(vsdb_connection, "germ_tests", ["lot_number"])
    assert rows, "Germ_tests has no rows to check"
    tests = get_germ_tests(vsdb_connection, rows[0]["lot_number"])
    assert tests
