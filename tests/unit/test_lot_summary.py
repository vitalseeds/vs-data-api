from tests.fakes import FakeConnection
from vs_data_api.vs_data.lots import LotSummary, get_lot_summary


def conn(*rows):
    return FakeConnection({r'FROM "seed_lots"': list(rows)})


def test_found_lot_maps_fields():
    summary = get_lot_summary(conn((3538, "CAR-1", "Seeds Ltd", 125.5)), 3538)
    assert summary == LotSummary(lot_number=3538, sku="CAR-1", source="Seeds Ltd", final_weight_g=125.5)


def test_missing_lot_returns_none():
    assert get_lot_summary(conn(), 1) is None


def test_zero_weight_is_not_recorded():
    assert get_lot_summary(conn((1, "A", "S", 0)), 1).final_weight_g is None


def test_blank_weight_and_source_are_none():
    summary = get_lot_summary(conn((1, "A", "  ", "")), 1)
    assert summary.final_weight_g is None
    assert summary.source is None
    assert get_lot_summary(conn((1, "A", None, None)), 1).source is None


def test_query_filters_by_lot_number():
    c = conn((3538, "CAR-1", "S", 1))
    get_lot_summary(c, 3538)
    sql = c.executed[0]
    assert "lot_number" in sql and "= 3538" in sql
    assert '"Original weight"' in sql and '"Source"' in sql
