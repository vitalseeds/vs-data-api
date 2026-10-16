"""
Slow, dropped and failing WooCommerce responses are retried (#51).
"""

import pytest
import requests

from vs_data_api.vs_data.wc import api
from vs_data_api.vs_data.wc.api import get_api

WC = "https://wc.test/wp-json/wc/v3"


@pytest.fixture
def wcapi():
    return get_api("https://wc.test", "ck_test", "cs_test")


def test_get_is_retried_after_a_server_error(wcapi, mocked_responses):
    mocked_responses.get(f"{WC}/products", status=503)
    mocked_responses.get(f"{WC}/products", json=[{"id": 1}])

    assert wcapi.get("products").json() == [{"id": 1}]
    assert len(mocked_responses.calls) == 2


def test_get_is_retried_after_a_dropped_connection(wcapi, mocked_responses):
    mocked_responses.get(f"{WC}/products", body=requests.exceptions.ConnectionError("dropped"))
    mocked_responses.get(f"{WC}/products", json=[])

    assert wcapi.get("products").status_code == 200


def test_get_is_retried_after_a_timeout(wcapi, mocked_responses):
    mocked_responses.get(f"{WC}/products", body=requests.exceptions.ReadTimeout("slow"))
    mocked_responses.get(f"{WC}/products", json=[])

    assert wcapi.get("products").status_code == 200


def test_put_is_retried(wcapi, mocked_responses):
    mocked_responses.put(f"{WC}/products/1", status=500)
    mocked_responses.put(f"{WC}/products/1", json={"id": 1})

    assert wcapi.put("products/1", {"stock_quantity": 3}).json() == {"id": 1}


def test_the_last_bad_response_is_returned_when_retries_run_out(wcapi, mocked_responses):
    for _ in range(api.RETRY_ATTEMPTS):
        mocked_responses.get(f"{WC}/products", status=502, json={"code": "bad_gateway"})

    response = wcapi.get("products")

    assert response.status_code == 502
    assert len(mocked_responses.calls) == api.RETRY_ATTEMPTS


def test_the_last_exception_is_raised_when_retries_run_out(wcapi, mocked_responses):
    for _ in range(api.RETRY_ATTEMPTS):
        mocked_responses.get(f"{WC}/products", body=requests.exceptions.ConnectionError("down"))

    with pytest.raises(requests.exceptions.ConnectionError):
        wcapi.get("products")
    assert len(mocked_responses.calls) == api.RETRY_ATTEMPTS


def test_client_errors_are_not_retried(wcapi, mocked_responses):
    mocked_responses.get(f"{WC}/products/9", status=404, json={"code": "woocommerce_rest_invalid_id"})

    assert wcapi.get("products/9").status_code == 404
    assert len(mocked_responses.calls) == 1


def test_post_is_retried_when_the_gateway_rejects_it(wcapi, mocked_responses):
    mocked_responses.post(f"{WC}/products/batch", status=503)
    mocked_responses.post(f"{WC}/products/batch", json={"update": []})

    assert wcapi.post("products/batch", {"update": []}).json() == {"update": []}


def test_post_is_not_repeated_after_a_server_error_or_read_timeout(wcapi, mocked_responses):
    """The server may already have applied the batch, so repeating it is not safe."""
    mocked_responses.post(f"{WC}/products/batch", status=500)

    assert wcapi.post("products/batch", {"update": []}).status_code == 500
    assert len(mocked_responses.calls) == 1

    mocked_responses.post(f"{WC}/products/batch", body=requests.exceptions.ReadTimeout("slow"))
    with pytest.raises(requests.exceptions.ReadTimeout):
        wcapi.post("products/batch", {"update": []})
    assert len(mocked_responses.calls) == 2
