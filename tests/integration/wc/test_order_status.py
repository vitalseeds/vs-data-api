"""
Order calls the app makes, against a real non-production WooCommerce (LocalWP).

Run with HPOS off, then on (#116):  uv run --extra test pytest tests/integration/wc --wcapi
"""

import pytest

from vs_data_api.vs_data.orders.status import wc_orders_update_status

pytestmark = [pytest.mark.wcapi]


def get_order(wcapi, order_id):
    response = wcapi.get(f"orders/{order_id}")
    assert response.status_code == 200, f"{response.status_code} {response.text[:200]}"
    return response.json()


def test_read_order(wcapi, staging_order):
    order = get_order(wcapi, staging_order)

    assert order["id"] == staging_order
    assert order["status"] == "pending"
    for key in ("order_key", "date_completed", "date_completed_gmt"):
        assert key in order


def test_batch_update_to_completed(wcapi, staging_order):
    updates = wc_orders_update_status(wcapi, [{"link_wc_order_id": staging_order}], target_status="completed")

    assert updates, "batch update returned nothing: check the key has write access and permalinks are not Plain"
    (update,) = updates
    assert update["id"] == staging_order
    assert update["status"] == "completed"
    assert update["order_key"]
    assert update["date_completed"]
    assert update["date_completed_gmt"]


def test_update_is_persisted(wcapi, staging_order):
    (update,) = wc_orders_update_status(wcapi, [{"link_wc_order_id": staging_order}], target_status="completed")

    order = get_order(wcapi, staging_order)

    assert order["status"] == "completed"
    assert order["date_completed"] == update["date_completed"]


def test_other_status_round_trips(wcapi, staging_order):
    updates = wc_orders_update_status(wcapi, [{"link_wc_order_id": staging_order}], target_status="processing")

    assert [u["status"] for u in updates] == ["processing"]
    assert get_order(wcapi, staging_order)["status"] == "processing"


def test_list_orders_filtered_by_status(safe_wcapi, staging_order):
    response = safe_wcapi.get("orders", params={"status": "pending", "include": str(staging_order)})

    assert response.status_code == 200
    orders = response.json()
    assert [o["id"] for o in orders] == [staging_order]
    assert {o["status"] for o in orders} == {"pending"}


def test_report_hpos_state(safe_wcapi, capsys):
    """Informational: records whether HPOS is on, so before/after runs are labelled."""
    response = safe_wcapi.get("system_status")
    hpos = "unknown"
    if response.status_code == 200:
        hpos = response.json().get("settings", {}).get("HPOS_enabled", "unknown")
    with capsys.disabled():
        print(f"\nHPOS enabled: {hpos}")
