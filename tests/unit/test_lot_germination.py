from datetime import date

from tests.fakes import FakeConnection
from vs_data_api.vs_data.lots import get_germ_tests, get_lot_summary, latest_result
from vs_data_api.vs_data.lots.germination import GermTest

# column order: Date, Result, Seed count, test_number, Notes
GERM = r'FROM "Germ_tests"'


def conn(*rows):
    return FakeConnection({GERM: list(rows)})


def test_tests_newest_first():
    tests = get_germ_tests(conn((date(2025, 1, 1), 80, "50", 1, "a"), (date(2026, 1, 1), 90, "50", 2, "b")), 1)
    assert [t.date for t in tests] == [date(2026, 1, 1), date(2025, 1, 1)]
    assert tests[0] == GermTest(date=date(2026, 1, 1), result=90, seed_count="50", notes="b")


def test_no_date_sorts_last():
    tests = get_germ_tests(conn((None, 70, "", 5, ""), (date(2020, 1, 1), 80, "", 1, "")), 1)
    assert [t.date for t in tests] == [date(2020, 1, 1), None]


def test_same_date_ordered_by_test_number_descending():
    d = date(2026, 1, 1)
    tests = get_germ_tests(conn((d, 10, "", 1, ""), (d, 20, "", 2, "")), 1)
    assert [t.result for t in tests] == [20, 10]


def test_blank_result_is_none_but_zero_is_kept():
    tests = get_germ_tests(conn((date(2026, 2, 1), "", "", 2, ""), (date(2026, 1, 1), 0, "", 1, None)), 1)
    assert [t.result for t in tests] == [None, 0]
    assert tests[1].notes is None and tests[0].seed_count is None


def test_latest_result_is_none_when_latest_test_has_no_result():
    tests = get_germ_tests(conn((date(2026, 2, 1), None, "", 2, ""), (date(2026, 1, 1), 90, "", 1, "")), 1)
    assert latest_result(tests) is None


def test_latest_result_none_when_no_tests():
    assert latest_result([]) is None


def test_latest_result_zero_is_a_result():
    assert latest_result([GermTest(date=None, result=0, seed_count=None, notes=None)]) == 0


def test_query_filters_by_lot_number():
    c = conn()
    get_germ_tests(c, 3538)
    assert "Lot_numberFK = 3538" in c.executed[0] and '"Germ_tests"' in c.executed[0]


def test_summary_includes_tests_and_result():
    c = FakeConnection(
        {r'FROM "seed_lots"': [(3538, "CAR-1", "S", 1)], GERM: [(date(2026, 1, 1), 88.5, "50", 1, "ok")]}
    )
    summary = get_lot_summary(c, 3538)
    assert summary.germ_result == 88.5
    assert len(summary.germ_tests) == 1


def test_missing_lot_makes_no_germ_query():
    c = FakeConnection({GERM: [(date(2026, 1, 1), 1, "", 1, "")]})
    assert get_lot_summary(c, 1) is None
    assert len(c.executed) == 1
