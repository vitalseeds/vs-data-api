"""
Smoke tests for every API endpoint, with FileMaker and WooCommerce stubbed.

Each endpoint is called through FastAPI's TestClient with ``db.connection``
returning a fake connection and the domain function it delegates to patched
(``autospec`` so a call with the wrong arguments fails). They check that the
endpoint starts, passes the right connection and arguments, and returns the
response FileMaker expects. The domain logic itself is covered elsewhere.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.fakes import FakeConnection
from vs_data_api import main
from vs_data_api.vs_data.orders import OrderUpdateFailed

FM = "fm"
LINK = "link"


# path, function the endpoint delegates to, its return value, connection used,
# expected response (subset of the JSON body)
ENDPOINTS = [
    (
        "/batch/awaiting_upload",
        "vs_data_api.vs_data.stock.get_batches_awaiting_upload_join_acq",
        [{"batch_number": 1}],
        FM,
        {"batches": [{"batch_number": 1}]},
    ),
    (
        "/batch/upload-wc-stock",
        "vs_data_api.vs_data.stock.update_wc_stock_for_new_batches",
        [1, 2],
        FM,
        {"batches": [1, 2], "message": "2 products were updated on WooCommerce"},
    ),
    (
        "/batch/upload-wc-stock/variation/large",
        "vs_data_api.vs_data.stock.update_wc_stock_for_new_batches",
        [1],
        FM,
        {"batches": [1], "message": "1 product variations were updated on WooCommerce"},
    ),
    (
        "/orders/selected/update/status/completed",
        "vs_data_api.vs_data.orders.update_packed_orders_status",
        [{"id": 1}, {"id": 2}],
        LINK,
        {"success": True, "orders": [{"id": 1}, {"id": 2}], "message": "2 orders were updated on WooCommerce"},
    ),
    (
        "/products/variations/update-wc-price",
        "vs_data_api.vs_data.products.price.push_variation_prices_to_wc",
        ([{"id": 1}], "audit.log"),
        FM,
        {"variations": [{"id": 1}]},
    ),
    (
        "/stock/apply-corrections",
        "vs_data_api.vs_data.stock.apply_corrections_to_wc_stock",
        [7, 8],
        FM,
        {"applied_corrections": [7, 8]},
    ),
    (
        "/orders/wholesale/export",
        "vs_data_api.vs_data.orders.wholesale.export_wholesale_orders",
        [{"sku": "A"}, {"sku": "B"}, {"sku": "C"}],
        LINK,
        {"message": "3 line items were exported."},
    ),
]

# Same endpoints when there is nothing to do
ENDPOINTS_NOTHING_TO_DO = [
    ("/batch/upload-wc-stock", "vs_data_api.vs_data.stock.update_wc_stock_for_new_batches", False),
    ("/batch/upload-wc-stock/variation/large", "vs_data_api.vs_data.stock.update_wc_stock_for_new_batches", False),
    ("/orders/selected/update/status/completed", "vs_data_api.vs_data.orders.update_packed_orders_status", None),
    ("/products/variations/update-wc-price", "vs_data_api.vs_data.products.price.push_variation_prices_to_wc", (None, None)),
    ("/stock/apply-corrections", "vs_data_api.vs_data.stock.apply_corrections_to_wc_stock", False),
    ("/orders/wholesale/export", "vs_data_api.vs_data.orders.wholesale.export_wholesale_orders", None),
]

# Endpoints covered by tests in this file (or test_health.py)
COVERED = {path for path, *_ in ENDPOINTS} | {
    "/",
    "/health",
    "/product/{product_id}",
    "/stock/report/all",
    "/products/import-wc-product-ids",
    "/orders/selected/update/status/{target_status}",
}
COVERED.discard("/orders/selected/update/status/completed")


@pytest.fixture
def connections(client):
    """Patch db.connection; returns {connection string: FakeConnection} for the ones opened."""
    settings = client.app.dependency_overrides[main.get_settings]()
    opened = {}

    def fake_connection(connection_string):
        opened[connection_string] = FakeConnection(connect_string=connection_string)
        return opened[connection_string]

    with patch.object(main.db, "connection", side_effect=fake_connection):
        yield opened, settings


@pytest.fixture
def client_raising():
    """A client that returns the app's 500 response instead of raising."""
    return TestClient(main.app, raise_server_exceptions=False)


def test_every_endpoint_has_a_smoke_test():
    """Add new endpoints to ENDPOINTS (or COVERED) when they are created."""
    routes = {route.path for route in main.app.routes if "GET" in getattr(route, "methods", ())}
    routes -= {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    assert routes - COVERED == set()


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "VS Data API running"}


def test_product_stub(client):
    response = client.get("/product/123")
    assert response.status_code == 200
    assert response.json() == {"product": 123}


@pytest.mark.parametrize("path, target, returns, database, expected", ENDPOINTS)
def test_endpoint(client, connections, path, target, returns, database, expected):
    opened, settings = connections
    connection_string = settings.fm_connection_string if database == FM else settings.fm_link_connection_string

    with patch(target, autospec=True, return_value=returns) as delegate:
        response = client.get(path)

    assert response.status_code == 200, response.text
    body = response.json()
    for key, value in expected.items():
        assert body[key] == value
    # called once, with the connection for the right database, which is then closed
    assert list(opened) == [connection_string]
    assert delegate.call_count == 1
    assert any(arg is opened[connection_string] for arg in delegate.call_args.args)
    assert opened[connection_string].closed


@pytest.mark.parametrize("path, target, returns", ENDPOINTS_NOTHING_TO_DO)
def test_endpoint_with_nothing_to_do(client, connections, path, target, returns):
    with patch(target, autospec=True, return_value=returns):
        response = client.get(path)

    assert response.status_code == 200, response.text
    assert response.json()["message"].startswith("No ")


def test_large_upload_targets_the_large_variation(client, connections):
    with patch("vs_data_api.vs_data.stock.update_wc_stock_for_new_batches", autospec=True, return_value=[]) as upload:
        client.get("/batch/upload-wc-stock/variation/large")

    assert upload.call_args.kwargs["product_variation"] == "large"


def test_order_status_is_passed_through(client, connections):
    with patch("vs_data_api.vs_data.orders.update_packed_orders_status", autospec=True, return_value=[]) as update:
        client.get("/orders/selected/update/status/processing")

    assert update.call_args.kwargs["target_status"] == "processing"


def test_failed_order_update_returns_a_readable_message(client, connections):
    failure = OrderUpdateFailed("None are selected.", updated=[])
    with patch("vs_data_api.vs_data.orders.update_packed_orders_status", autospec=True, side_effect=failure):
        response = client.get("/orders/selected/update/status/completed")

    assert response.json() == {"success": False, "orders": [], "message": "None are selected."}


def test_stock_report_is_a_csv_download(client, connections, tmp_path):
    report = tmp_path / "report.csv"
    report.write_text("sku,stock\nBeBO,3\n")

    with patch("vs_data_api.vs_data.stock.compare_wc_fm_stock", autospec=True, return_value=str(report)):
        response = client.get("/stock/report/all")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.text == "sku,stock\nBeBO,3\n"


def test_import_wc_product_ids_reports_both_counts(client, connections):
    opened, settings = connections
    with patch.object(
        main, "import_wc_product_ids_from_linkdb", autospec=True, return_value=(["a", "b"], ["x", "y", "z"])
    ):
        response = client.get("/products/import-wc-product-ids")

    assert response.status_code == 200
    message = response.json()["message"]
    assert "2 regular product skus imported" in message
    assert "3 variation skus imported" in message
    assert set(opened) == {settings.fm_connection_string, settings.fm_link_connection_string}


def test_error_returns_a_message_filemaker_can_show(client_raising, connections):
    """Any exception becomes a 500 with a JSON message, not an HTML error page."""
    with patch(
        "vs_data_api.vs_data.stock.apply_corrections_to_wc_stock",
        autospec=True,
        side_effect=RuntimeError("WooCommerce timed out"),
    ):
        response = client_raising.get("/stock/apply-corrections")

    assert response.status_code == 500
    message = response.json()["message"]
    assert "/stock/apply-corrections" in message
    assert "WooCommerce timed out" in message
