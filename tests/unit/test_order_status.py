"""
Updating the status of orders selected in the link database.

The link database is a FakeConnection; WooCommerce is the real client with HTTP
intercepted by ``responses``.
"""

import re

import pytest
from responses import matchers

from tests.fakes import FakeConnection
from vs_data_api.vs_data.orders import status
from vs_data_api.vs_data.wc.api import get_api

WC = "https://wc.test/wp-json/wc/v3"
SELECTED_ORDERS = r'FROM "Orders"'


@pytest.fixture
def wcapi():
    return get_api("https://wc.test", "ck_test", "cs_test")


def link_db(*order_ids):
    return FakeConnection({SELECTED_ORDERS: [(order_id, "A Customer", "packing", "Yes") for order_id in order_ids]})


def expect_batch_update(wc, order_ids, target_status, date_completed="2023-02-14T13:47:24"):
    wc.post(
        f"{WC}/orders/batch",
        match=[matchers.json_params_matcher({"update": [{"id": i, "status": target_status} for i in order_ids]})],
        json={
            "update": [
                {"id": i, "order_key": f"wc_order_{i}", "status": target_status, "date_completed": date_completed}
                for i in order_ids
            ]
        },
    )


def test_no_selected_orders_does_nothing(wcapi, mocked_responses):
    linkdb = link_db()

    assert status.update_packed_orders_status(linkdb, wcapi) is None
    assert linkdb.statements("^UPDATE") == []


def test_completed_orders_are_updated_in_woocommerce_then_the_link_db(wcapi, mocked_responses):
    expect_batch_update(mocked_responses, [46011, 46012], "completed")
    linkdb = link_db(46011, 46012)

    updated = status.update_packed_orders_status(linkdb, wcapi)

    assert [order["id"] for order in updated] == [46011, 46012]
    assert linkdb.statements("^UPDATE") == [
        "UPDATE \"Orders\" SET order_status='completed', selected='', "
        "DateCompleted=TIMESTAMP '2023-02-14 13:47:24', DateCompletedGMT=TIMESTAMP '2023-02-14 13:47:24' "
        f'WHERE "_kf_WooCommerceID" = {order_id}'
        for order_id in (46011, 46012)
    ]


def test_completed_order_without_a_completion_date_uses_now(wcapi, mocked_responses):
    expect_batch_update(mocked_responses, [46011], "completed", date_completed=None)
    linkdb = link_db(46011)

    status.update_packed_orders_status(linkdb, wcapi)

    [update] = linkdb.statements("^UPDATE")
    assert re.search(r"DateCompleted=TIMESTAMP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'", update)


def test_other_statuses_are_set_on_all_selected_orders(wcapi, mocked_responses):
    expect_batch_update(mocked_responses, [46011], "processing")
    linkdb = link_db(46011)

    status.update_packed_orders_status(linkdb, wcapi, target_status="processing")

    assert linkdb.statements("^UPDATE") == [
        "UPDATE \"Orders\" SET selected='', order_status='processing' WHERE selected='yes' OR selected='Yes'"
    ]


def test_link_db_is_not_changed_if_woocommerce_fails(wcapi, mocked_responses):
    """Orders stay selected so the update can be retried."""
    mocked_responses.post(f"{WC}/orders/batch", status=500, json={"code": "error"})
    linkdb = link_db(46011)

    assert status.update_packed_orders_status(linkdb, wcapi) is None
    assert linkdb.statements("^UPDATE") == []


def test_orders_are_sent_in_batches_of_100(wcapi, mocked_responses):
    """WooCommerce rejects batch requests of more than 100 items."""
    order_ids = list(range(1, 151))
    expect_batch_update(mocked_responses, order_ids[:100], "completed")
    expect_batch_update(mocked_responses, order_ids[100:], "completed")
    linkdb = link_db(*order_ids)

    updated = status.update_packed_orders_status(linkdb, wcapi)

    assert len(updated) == 150
