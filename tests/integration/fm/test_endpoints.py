"""Test cases for fast api endpoints."""

import pytest
from fastapi.testclient import TestClient

ENDPOINTS = [
    "/",
    "/product/123",  # /product/{product_id}
    "/batch/awaiting_upload",
    "/batch/upload-wc-stock",
    "/batch/upload-wc-stock/variation/large",
    "/stock/apply-corrections",
    "/orders/wholesale/export",
]

ENDPOINTS__SLOW = [
    "/products/variations/update-wc-price",
    "/stock/report/all",
    "/orders/selected/update/status/{target_status}",  # /orders/selected/update/status/{target_status}
]



def test_fastapi_client(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "VS Data API running",
    }


@pytest.mark.fmdb
@pytest.mark.wcapi
@pytest.mark.timeout()
@pytest.mark.parametrize("endpoint_path", ENDPOINTS)
def test_all_endpoints(client, endpoint_path):
    response = client.get(endpoint_path)
    assert response.status_code == 200

@pytest.mark.fmdb
@pytest.mark.wcapi
@pytest.mark.slow
@pytest.mark.timeout(60)
@pytest.mark.parametrize("endpoint_path", ENDPOINTS__SLOW)
def test_all_slow_endpoints(client, endpoint_path):
    response = client.get(endpoint_path)
    assert response.status_code == 200


def test_upload_wc_stock__none(client: TestClient):
    response = client.get("/batch/upload-wc-stock")
    assert response.status_code == 200
    assert response.json() == {"message": "No batches were updated on WooCommerce"}


def test_upload_wc_large_stock__none(client: TestClient):
    response = client.get("/batch/upload-wc-stock/variation/large")
    assert response.status_code == 200
    assert response.json() == {"message": "No large batches were updated on WooCommerce"}
