"""
Stock corrections: pushing changes to WooCommerce and recording them in FileMaker.

FileMaker is a FakeConnection (records SQL, returns canned rows); WooCommerce is
the real client with HTTP intercepted by ``responses``, so request payloads are
checked as WooCommerce receives them.
"""

import re

import pytest
from responses import matchers

from tests.fakes import FakeConnection
from vs_data_api.vs_data.stock import corrections
from vs_data_api.vs_data.wc.api import get_api

WC = "https://wc.test/wp-json/wc/v3"

# Columns as selected by get_unprocessed_stock_corrections_join_acq_stock:
# id, sku, large_packet_correction, stock_change, comment, create_line_item,
# wc_stock_updated, vs_stock_updated, wc_product_id, wc_variation_lg_id, stock_regular, stock_large
REGULAR_PLUS_3 = (7, "BeBO", None, 3.0, "found 3", 1, None, None, 101, 501, 155, 4)
REGULAR_MINUS_1 = (8, "BeBO", None, -1.0, "damaged", None, None, None, 101, 501, 155, 4)
LARGE_PLUS_5 = (9, "CaRo", 1, 5.0, "recount", 1, None, None, 202, 602, 10, 2)
LARGE_NO_VARIATION = (10, "DaLe", 1, 2.0, "recount", 1, None, None, 303, None, 10, 2)

ACQUISITIONS = {
    r'"packing_batch" FROM "acquisitions"': [("BeBO", 1234)],
    r'"Lrg_packing_batch" FROM "acquisitions"': [("CaRo", "GR12")],
}


def fm_with_corrections(*rows, results=None):
    return FakeConnection({r'FROM "stock_corrections"': list(rows), **ACQUISITIONS, **(results or {})})


@pytest.fixture
def wcapi():
    return get_api("https://wc.test", "ck_test", "cs_test")


@pytest.fixture
def wc(mocked_responses):
    """WooCommerce; every registered request must be made."""
    return mocked_responses


# WooCommerce stock before the corrections: product 101 has 20, product 202's large variation 602 has 6


def expect_regular_update(wc, product_id, stock_quantity, confirmed=True):
    wc.get(f"{WC}/products", json=[{"id": 101, "stock_quantity": 20}])
    wc.post(
        f"{WC}/products/batch",
        match=[matchers.json_params_matcher({"update": [{"id": product_id, "stock_quantity": stock_quantity}]})],
        json={"update": [{"id": product_id}] if confirmed else []},
    )


def expect_large_update(wc, product_id, variation_id, stock_quantity):
    wc.get(f"{WC}/products/202/variations/602", json={"id": 602, "stock_quantity": 6})
    wc.put(
        f"{WC}/products/{product_id}/variations/{variation_id}",
        match=[matchers.json_params_matcher({"stock_quantity": stock_quantity})],
        json={"id": variation_id},
    )


def test_nothing_to_apply(wcapi, mocked_responses):
    fm = fm_with_corrections()

    assert corrections.apply_corrections_to_wc_stock(fm, wcapi) is False
    assert fm.statements("^(UPDATE|INSERT)") == []


def test_corrections_for_one_product_are_added_up_into_one_update(wcapi, wc):
    # 20 in WooCommerce, +3 and -1
    expect_regular_update(wc, 101, 22)
    fm = fm_with_corrections(REGULAR_PLUS_3, REGULAR_MINUS_1)

    assert corrections.apply_corrections_to_wc_stock(fm, wcapi) == [7, 8]


def test_large_correction_updates_the_large_variation(wcapi, wc):
    # 6 in WooCommerce, +5
    expect_large_update(wc, 202, 602, 11)
    fm = fm_with_corrections(LARGE_PLUS_5)

    assert corrections.apply_corrections_to_wc_stock(fm, wcapi) == [9]


def test_large_correction_without_a_variation_id_is_skipped(wcapi, mocked_responses):
    fm = fm_with_corrections(LARGE_NO_VARIATION)

    # no WooCommerce request is registered, so any request would fail
    assert corrections.apply_corrections_to_wc_stock(fm, wcapi) == []
    assert fm.statements("^(UPDATE|INSERT)") == []


def test_applied_corrections_are_flagged_so_they_are_not_applied_twice(wcapi, wc):
    expect_regular_update(wc, 101, 22)
    expect_large_update(wc, 202, 602, 11)
    fm = fm_with_corrections(REGULAR_PLUS_3, REGULAR_MINUS_1, LARGE_PLUS_5)

    corrections.apply_corrections_to_wc_stock(fm, wcapi)

    flagged = fm.statements(r"SET wc_stock_updated=1")
    assert flagged == [f"UPDATE stock_corrections SET wc_stock_updated=1 WHERE id = {i}" for i in (7, 8, 9)]


def test_correction_not_confirmed_by_woocommerce_is_left_for_next_time(wcapi, wc):
    expect_regular_update(wc, 101, 23, confirmed=False)
    fm = fm_with_corrections(REGULAR_PLUS_3)

    assert corrections.apply_corrections_to_wc_stock(fm, wcapi) == []
    assert fm.statements("^(UPDATE|INSERT)") == []


def test_local_stock_is_amended_by_the_total_change(wcapi, wc):
    expect_regular_update(wc, 101, 22)
    expect_large_update(wc, 202, 602, 11)
    fm = fm_with_corrections(REGULAR_PLUS_3, REGULAR_MINUS_1, LARGE_PLUS_5)

    corrections.apply_corrections_to_wc_stock(fm, wcapi)

    assert fm.statements(r"^UPDATE stock ") == [
        "UPDATE stock SET stock_regular = stock_regular + 2 WHERE LOWER(sku)=LOWER('BeBO')",
        "UPDATE stock SET stock_large = stock_large + 5 WHERE LOWER(sku)=LOWER('CaRo')",
    ]


def test_left_in_batch_is_amended_on_the_current_batch(wcapi, wc):
    expect_regular_update(wc, 101, 22)
    expect_large_update(wc, 202, 602, 11)
    fm = fm_with_corrections(REGULAR_PLUS_3, REGULAR_MINUS_1, LARGE_PLUS_5)

    corrections.apply_corrections_to_wc_stock(fm, wcapi)

    assert fm.statements("left_in_batch") == [
        "UPDATE packeting_batches SET left_in_batch=left_in_batch + 3 WHERE batch_number=1234",
        "UPDATE packeting_batches SET left_in_batch=left_in_batch + -1 WHERE batch_number=1234",
        # large batch numbers are strings
        "UPDATE large_batches SET left_in_batch=left_in_batch + 5 WHERE batch_number='GR12'",
    ]


def test_left_in_batch_is_skipped_when_there_is_no_current_batch():
    # eg a product that is not packed in batches, such as a calendar
    fm = FakeConnection()

    assert corrections.amend_left_in_batch(fm, "Calendar", 3) is None
    assert fm.statements("^UPDATE") == []


def test_line_item_records_the_correction_as_an_order_quantity(wcapi, wc, monkeypatch):
    monkeypatch.setattr(corrections, "ADMIN_EMAIL", "admin@test")
    expect_regular_update(wc, 101, 22)
    expect_large_update(wc, 202, 602, 11)
    fm = fm_with_corrections(REGULAR_PLUS_3, REGULAR_MINUS_1, LARGE_PLUS_5)

    corrections.apply_corrections_to_wc_stock(fm, wcapi)

    [insert] = fm.statements("INSERT INTO LineItems_Orders")
    values = insert.split("VALUES ")[1]
    date = r"DATE '\d{4}/\d{2}/\d{2}'"
    # quantity is the inverse of the stock change; stock level is the local stock plus the change.
    # Correction 8 asked for no line item.
    assert re.fullmatch(
        rf"\('BeBO', 'Regular packet', {date}, -3, 'admin@test', 7, 'found 3', 'Correction', 158\), "
        rf"\('CaRo', 'Large pack', {date}, -5, 'admin@test', 9, 'recount', 'Correction', 7\)",
        values,
    )


def test_every_applied_correction_is_flagged_as_applied_locally(wcapi, wc):
    """Local stock is amended for all of them, with or without a line item."""
    expect_regular_update(wc, 101, 22)
    fm = fm_with_corrections(REGULAR_PLUS_3, REGULAR_MINUS_1)

    corrections.apply_corrections_to_wc_stock(fm, wcapi)

    flagged = fm.statements(r"SET vs_stock_updated=1")
    assert sorted(flagged) == [f"UPDATE stock_corrections SET vs_stock_updated=1 WHERE id = {i}" for i in (7, 8)]


def test_comment_with_an_apostrophe_is_quoted(wcapi, wc):
    expect_regular_update(wc, 101, 23)
    fm = fm_with_corrections((7, "BeBO", None, 3.0, "Fred's recount", 1, None, None, 101, 501, 155, 4))

    corrections.apply_corrections_to_wc_stock(fm, wcapi)

    [insert] = fm.statements("INSERT INTO LineItems_Orders")
    assert "'Fred''s recount'" in insert
