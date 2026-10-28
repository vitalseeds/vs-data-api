from datetime import date

import pytest
from pydantic import ValidationError

from tests.fakes import FakeConnection
from vs_data_api.vs_data.lots import get_sku_lots


def conn(*rows):
    return FakeConnection({r'FROM "seed_lots"': list(rows)})


# lot_number, sku, date_received, original_weight, current_weight
def test_no_lots_returns_none():
    assert get_sku_lots(conn(), "OnWl") is None


def test_newest_received_first_undated_last():
    rows = [
        (1, "OnWl", date(2024, 1, 1), 500, 100),
        (2, "OnWl", date(2026, 5, 1), 500, 500),
        (3, "OnWl", None, 500, 5),
        (4, "OnWl", date(2025, 3, 1), 500, 0),
    ]
    assert [lot.lot_number for lot in get_sku_lots(conn(*rows), "OnWl").lots] == [2, 4, 1, 3]


def test_same_date_higher_lot_number_first():
    rows = [(1, "A", date(2025, 1, 1), 1, 1), (2, "A", date(2025, 1, 1), 1, 1)]
    assert [lot.lot_number for lot in get_sku_lots(conn(*rows), "A").lots] == [2, 1]


def test_sku_is_as_stored_not_as_typed():
    assert get_sku_lots(conn((1, "OnWl", None, 1, 1)), "onwl").sku == "OnWl"


def test_lookup_is_case_insensitive_and_escaped():
    c = conn((1, "OnWl", None, 1, 1))
    get_sku_lots(c, "onwl")
    assert "UPPER(\"sku\") = 'ONWL'" in c.executed[0]
    c = conn()
    get_sku_lots(c, "x' OR '1'='1")
    assert "'X'' OR ''1''=''1'" in c.executed[0]


@pytest.mark.parametrize("current,expected", [("350g", 350), ("0", 0), (0, 0), (12.5, 12.5), ("", None), (None, None), (" 7 g", 7)])
def test_current_weight_parsing(current, expected):
    lot = get_sku_lots(conn((1, "A", None, 500, current)), "A").lots[0]
    assert lot.current_weight_g == expected


def test_zero_current_weight_is_kept_blank_is_none():
    lots = get_sku_lots(conn((1, "A", None, 500, 0), (2, "A", None, 500, "")), "A").lots
    assert {lot.lot_number: lot.current_weight_g for lot in lots} == {1: 0, 2: None}


def test_zero_or_blank_initial_weight_is_none():
    assert get_sku_lots(conn((1, "A", None, 0, 1)), "A").lots[0].initial_weight_g is None


def test_unreadable_weight_raises_validation_error():
    with pytest.raises(ValidationError):
        get_sku_lots(conn((1, "A", None, 500, "approx 100")), "A")
