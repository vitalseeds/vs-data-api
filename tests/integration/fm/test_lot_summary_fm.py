"""Checks the seed_lots field names used by the lot summary against a real FileMaker."""

import pytest

from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.lots import LotSummary, get_lot_summary


@pytest.mark.fmdb
def test_lot_summary_fields_exist(vsdb_connection):
    rows = db.select(vsdb_connection, "seed_lots", ["lot_number"])
    assert rows, "seed_lots has no rows to check"
    summary = get_lot_summary(vsdb_connection, rows[0]["lot_number"])
    assert isinstance(summary, LotSummary)
