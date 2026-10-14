import os

import pytest

from tests.integration.wc.safety import ALLOW_REMOTE_VAR, unsafe_reason
from vs_data_api.config import TestSettings


@pytest.fixture
def staging_order(wcapi):
    """A pending order created for one test and force-deleted afterwards."""
    url = TestSettings().vsdata_wc_url
    reason = unsafe_reason(url, allow_remote=os.environ.get(ALLOW_REMOTE_VAR) == "1")
    if reason:
        pytest.skip(reason)

    response = wcapi.post(
        "orders",
        {"status": "pending", "set_paid": False, "fee_lines": [{"name": "vs-data-api HPOS test", "total": "1.00"}]},
    )
    assert response.status_code == 201, f"could not create order: {response.status_code} {response.text[:200]}"
    order_id = response.json()["id"]
    try:
        yield order_id
    finally:
        wcapi.delete(f"orders/{order_id}", params={"force": True})
