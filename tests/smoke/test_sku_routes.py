"""The SKU lot list pages, with FileMaker stubbed."""

from datetime import date
from unittest.mock import patch

import pytest

from tests.fakes import FakeConnection
from vs_data_api import main

ROWS = [
    (10, "OnWl", date(2024, 1, 1), 500, 120),
    (11, "OnWl", date(2026, 2, 1), 500, "0"),
    (12, "OnWl", None, 250, ""),
]


@pytest.fixture
def fm(client):
    results = {r"UPPER\(\"sku\"\) = 'ONWL'": ROWS}
    with patch.object(main.db, "connection", side_effect=lambda cs: FakeConnection(results)):
        yield


def test_html_lists_lots_with_links_newest_first(client, fm):
    response = client.get("/sku/onwl")
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "<h1>OnWl</h1>" in html
    assert html.index('href="/lot/11"') < html.index('href="/lot/10"') < html.index('href="/lot/12"')
    assert "01 / 02 / 26" in html and "no date" in html
    assert '<td class="num">500 g</td><td class="num">120 g</td>' in html
    assert '<td class="num">250 g</td><td class="num">not recorded</td>' in html
    assert html.index(">Initial</th>") < html.index(">Current</th>")


def test_only_zero_current_weight_is_struck_through(client, fm):
    html = client.get("/sku/OnWl").text
    assert html.count('class="used"') == 1
    assert html.index('class="used"') < html.index('href="/lot/11"') < html.index('href="/lot/10"')


def test_sku_page_has_its_own_box_and_toggle(client, fm):
    html = client.get("/sku/OnWl").text
    assert 'name="sku"' in html and 'action="/sku"' in html and 'value="OnWl"' in html
    assert 'inputmode="text"' in html and "const prefix = '/sku'" in html
    assert '<a class="switch" href="/lot" title="Switch search"><s>lot</s> / <b>sku</b></a>' in html


def test_lot_page_toggle_goes_to_sku_with_lot_bold(client):
    html = client.get("/lot").text
    assert '<a class="switch" href="/sku" title="Switch search"><b>lot</b> / <s>sku</s></a>' in html
    assert 'inputmode="numeric"' in html and "const prefix = '/lot'" in html


def test_json(client, fm):
    body = client.get("/sku/OnWl?format=json").json()
    assert body["sku"] == "OnWl"
    assert body["lots"][0] == {"lot_number": 11, "date_received": "2026-02-01", "initial_weight_g": 500.0, "current_weight_g": 0.0}
    assert body["lots"][2]["current_weight_g"] is None


def test_unknown_sku_404_html_and_json(client, fm):
    html = client.get("/sku/Nope")
    assert html.status_code == 404 and "No lots found for SKU Nope" in html.text
    js = client.get("/sku/Nope?format=json")
    assert js.status_code == 404 and "message" in js.json()


def test_sku_is_escaped_in_the_page(client, fm):
    html = client.get("/sku/<b>x").text
    assert "<b>x" not in html and "&lt;b&gt;x" in html


def test_too_long_sku_422(client, fm):
    assert client.get("/sku/" + "a" * 51).status_code == 422


def test_filemaker_down_503(client):
    with patch.object(main.db, "connection", side_effect=RuntimeError("secret ODBC detail")):
        html = client.get("/sku/OnWl")
        js = client.get("/sku/OnWl?format=json")
    assert html.status_code == 503 and js.status_code == 503
    assert "secret ODBC detail" not in html.text + js.text


def test_unreadable_weight_is_500_not_503(client):
    results = {r'FROM "seed_lots"': [(10, "OnWl", None, 500, "approx 100")]}
    with patch.object(main.db, "connection", side_effect=lambda cs: FakeConnection(results)):
        response = client.get("/sku/OnWl")
    assert response.status_code == 500 and "be read" in response.text


def test_form_page_and_redirect(client):
    assert 'name="sku"' in client.get("/sku").text
    response = client.get("/sku?sku=OnWl", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/sku/OnWl"
