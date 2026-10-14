"""
Pushing regular and large variation prices from the VS database to WooCommerce.
"""

import csv

import pytest
from responses import matchers

from tests.fakes import FakeConnection
from vs_data_api.vs_data.products import price
from vs_data_api.vs_data.wc.api import get_api

WC = "https://wc.test/wp-json/wc/v3"

# sku, wc_product_id, wc_variation_lg_id, wc_variation_regular_id, price, lg_variation_price
BEBO = ("BeBO", 101, 502, 501, 2.95, 12.5)


@pytest.fixture
def wcapi():
    return get_api("https://wc.test", "ck_test", "cs_test")


@pytest.fixture
def audit_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path))
    return tmp_path


def expect_price(wc, product_id, variation_id, regular_price, sku):
    wc.put(
        f"{WC}/products/{product_id}/variations/{variation_id}",
        match=[matchers.json_params_matcher({"regular_price": regular_price})],
        json={"id": variation_id, "sku": sku, "regular_price": regular_price, "permalink": f"https://shop/{sku}"},
    )


def test_only_acquisitions_with_a_large_price_are_selected():
    fm = FakeConnection()

    price.get_acquisitions_with_large_variation(fm)

    assert fm.executed[0].endswith('WHERE Large_price IS NOT NULL')


def test_regular_and_large_prices_are_pushed_to_their_variations(wcapi, mocked_responses, audit_dir):
    expect_price(mocked_responses, 101, 501, "2.95", "BeBO")
    expect_price(mocked_responses, 101, 502, "12.5", "BeBOGr")
    fm = FakeConnection({r'FROM "acquisitions"': [BEBO]})

    variations, audit_log_path = price.push_variation_prices_to_wc(wcapi, fm)

    assert [v["sku"] for v in variations] == ["BeBO"]
    with open(audit_log_path) as audit_log:
        rows = list(csv.DictReader(audit_log))
    assert rows == [
        {"sku": "BeBO", "id": "501", "regular_price": "2.95", "permalink": "https://shop/BeBO"},
        {"sku": "BeBOGr", "id": "502", "regular_price": "12.5", "permalink": "https://shop/BeBOGr"},
    ]
    assert audit_log_path.startswith(str(audit_dir))


def test_a_failed_product_does_not_stop_the_others_or_count_as_updated(wcapi, mocked_responses, audit_dir):
    # BeBO's regular variation id is unknown to WooCommerce
    mocked_responses.put(f"{WC}/products/101/variations/501", status=400, json={"code": "woocommerce_rest_invalid_id"})
    expect_price(mocked_responses, 202, 601, "3.5", "CaRo")
    expect_price(mocked_responses, 202, 602, "14.0", "CaRoGr")
    fm = FakeConnection({r'FROM "acquisitions"': [BEBO, ("CaRo", 202, 602, 601, 3.5, 14.0)]})

    variations, _ = price.push_variation_prices_to_wc(wcapi, fm)

    assert [v["sku"] for v in variations] == ["CaRo"]
