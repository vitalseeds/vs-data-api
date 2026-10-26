"""The lot summary pages, with FileMaker stubbed."""

from unittest.mock import patch

import pytest

from tests.fakes import FakeConnection
from vs_data_api import main

LOT_ROW = (3538, "CAR-1", "Seeds Ltd", 125.5)


@pytest.fixture
def fm(client):
    """Patch db.connection to a FakeConnection that finds lot 3538 only."""
    results = {r"lot_number\s*=\s*3538": [LOT_ROW]}
    with patch.object(main.db, "connection", side_effect=lambda cs: FakeConnection(results)):
        yield


def test_html_found(client, fm):
    response = client.get("/lot/3538")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Seeds Ltd" in response.text and "125.5 g" in response.text


def test_json_found_via_query(client, fm):
    response = client.get("/lot/3538?format=json")
    assert response.status_code == 200
    assert response.json() == {"lot_number": 3538, "sku": "CAR-1", "source": "Seeds Ltd", "final_weight_g": 125.5}


def test_json_found_via_accept_header(client, fm):
    response = client.get("/lot/3538", headers={"Accept": "application/json"})
    assert response.json()["lot_number"] == 3538


def test_unknown_lot_404_html_and_json(client, fm):
    html = client.get("/lot/1")
    assert html.status_code == 404 and "Lot 1" in html.text
    assert html.headers["content-type"].startswith("text/html")
    js = client.get("/lot/1?format=json")
    assert js.status_code == 404 and "message" in js.json()


@pytest.mark.parametrize("bad", ["abc", "-1", "0", "99999999999999999999", "1.5"])
def test_bad_lot_number_422(client, fm, bad):
    html = client.get(f"/lot/{bad}")
    assert html.status_code == 422
    assert html.headers["content-type"].startswith("text/html")
    js = client.get(f"/lot/{bad}?format=json")
    assert js.status_code == 422 and "message" in js.json()


def test_filemaker_down_503_html_and_json(client):
    with patch.object(main.db, "connection", side_effect=RuntimeError("secret ODBC detail")):
        html = client.get("/lot/3538")
        js = client.get("/lot/3538?format=json")
    assert html.status_code == 503 and js.status_code == 503
    assert "secret ODBC detail" not in html.text + js.text
    assert "FileMaker" in html.text
    assert "message" in js.json()


def test_form_page(client):
    response = client.get("/lot")
    assert response.status_code == 200 and 'name="lot_number"' in response.text


def test_form_redirects_to_lot_page(client):
    response = client.get("/lot?lot_number=3538", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/lot/3538"
