"""Test cases for fast api endpoints."""

import pytest
from fastapi.testclient import TestClient
from starlette.responses import FileResponse


def test_get_product_by_id(client: TestClient):
    # This is not currently implemented
    response = client.get("/product/123")
    assert response.status_code == 200
    assert response.json() == {"product": 123}


def test_get_awaiting_upload(client: TestClient):
    response = client.get("/batch/awaiting_upload")
    assert response.status_code == 200
    assert "batches" in response.json()


def test_upload_wc_stock(client: TestClient):
    response = client.get("/batch/upload-wc-stock")
    assert response.status_code == 200
    data = response.json()
    assert "batches" in data
    assert "message" in data


# def test_upload_wc_stock__none(client: TestClient):
#     response = client.get("/batch/upload-wc-stock")
#     assert response.status_code == 200
#     assert response.json() == {"message": "No batches were updated on WooCommerce"}


def test_upload_wc_stock_variation_large(client: TestClient):
    response = client.get("/batch/upload-wc-stock/variation/large")
    assert response.status_code == 200
    data = response.json()
    assert "batches" in data
    assert "message" in data


# def test_upload_wc_large_stock__none(client: TestClient):
#     response = client.get("/batch/upload-wc-stock/variation/large")
#     assert response.status_code == 200
#     assert response.json() == {"message": "No large batches were updated on WooCommerce"}


# TODO: mock the FileResponse constructor
# @pytest.mark.slow
# @pytest.mark.timeout(60)
# def test_download(client: TestClient):
#     response = client.get("/stock/report/all")
#     assert response.status_code == 200
#     assert isinstance(response, FileResponse)


def test_update_status_selected_orders(client: TestClient):
    response = client.get("/orders/selected/update/status/complete")
    assert "message" in response.json()


@pytest.mark.slow
@pytest.mark.timeout(60)
def test_update_wc_variation_prices(client: TestClient):
    response = client.get("/products/variations/update-wc-price")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "variations" in data


def test_apply_stock_corrections_wc(client: TestClient):
    response = client.get("/stock/apply-corrections")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "applied_corrections" in data


def test_export_wholesale_orders(client: TestClient):
    response = client.get("/orders/wholesale/export")
    assert "message" in response.json()
