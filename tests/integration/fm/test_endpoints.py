"""Test cases for fast api endpoints."""

from fastapi.testclient import TestClient


def test_fastapi_client(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "VS Data API running",
    }


def test_upload_wc_stock__none(client: TestClient):
    response = client.get("/batch/upload-wc-stock")
    assert response.status_code == 200
    assert response.json() == {"message": "No batches were updated on WooCommerce"}


def test_upload_wc_large_stock__none(client: TestClient):
    response = client.get("/batch/upload-wc-stock/variation/large")
    assert response.status_code == 200
    assert response.json() == {"message": "No large batches were updated on WooCommerce"}
