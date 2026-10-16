import io
import json
import socket
import sys
import types
import urllib.error
from unittest.mock import MagicMock, patch

from vs_data_api import health
from vs_doctor import diagnose

# --- ODBC ---


def test_database_name():
    assert diagnose.database_name("Driver={FileMaker ODBC};Server=localhost;Database=vs_db;UID=u;PWD=p;") == "vs_db"
    assert diagnose.database_name("DSN=wc_link_odbc;UID=u") == "wc_link_odbc"
    assert diagnose.database_name("") == "the database"


def test_try_odbc_without_connection_string():
    assert "not set" in diagnose.try_odbc("  ")


def test_try_odbc_ok_and_failure(monkeypatch):
    fake = types.SimpleNamespace(connect=MagicMock())
    monkeypatch.setitem(sys.modules, "pypyodbc", fake)
    assert diagnose.try_odbc("DSN=x") is None
    fake.connect.return_value.close.assert_called_once()
    fake.connect.side_effect = RuntimeError("Failed to connect to listener (2)")
    assert "listener (2)" in diagnose.try_odbc("DSN=x")


def test_try_odbc_reports_a_driver_manager_that_wont_load(monkeypatch):
    monkeypatch.setitem(sys.modules, "pypyodbc", None)  # makes "import pypyodbc" raise ImportError
    error = diagnose.try_odbc("DSN=x")
    assert "driver isn't installed" in diagnose.explain_odbc_error(error, "vs_db")["message"]


def test_explain_odbc_error():
    explain = diagnose.explain_odbc_error
    assert "missing from the settings file" in explain("connection string is not set", "vs_db")["message"]
    assert "driver isn't installed" in explain("Error: [IM002] Data source name not found", "vs_db")["message"]
    sharing = explain("Error: [FileMaker] Failed to connect to listener (2)", "vs_db")
    assert sharing["message"] == "FileMaker isn't sharing vs_db over ODBC."
    assert "Enable ODBC/JDBC" in sharing["advice"]
    assert "password" in explain("Error: [FileMaker] Login failed: invalid account or password", "vs_db")["message"]
    assert explain("Error: gremlins", "vs_db")["message"] == "Something unexpected: Error: gremlins"


# --- /health ---


class FakeResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_get_health_ok(monkeypatch):
    urls = []
    monkeypatch.setattr(diagnose.urllib.request, "urlopen", lambda url, **kw: urls.append(url) or FakeResponse({"status": "ok"}))
    assert diagnose.get_health("8432") == {"status": "ok"}
    assert urls == ["http://localhost:8432/health"]


def test_get_health_reads_a_503_body(monkeypatch):
    body = json.dumps({"status": "degraded", "checks": {}}).encode()

    def urlopen(url, **kw):
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, io.BytesIO(body))

    monkeypatch.setattr(diagnose.urllib.request, "urlopen", urlopen)
    assert diagnose.get_health("8432")["status"] == "degraded"


def test_get_health_falls_back_to_https(monkeypatch):
    def urlopen(url, **kw):
        if url.startswith("http:"):
            raise ConnectionResetError("server speaks TLS")
        assert kw["context"] is not None  # self-signed certificates are accepted
        return FakeResponse({"status": "ok"})

    monkeypatch.setattr(diagnose.urllib.request, "urlopen", urlopen)
    assert diagnose.get_health("8432") == {"status": "ok"}


def test_get_health_none_when_nothing_answers(monkeypatch):
    def urlopen(url, **kw):
        raise urllib.error.URLError(ConnectionRefusedError())

    monkeypatch.setattr(diagnose.urllib.request, "urlopen", urlopen)
    assert diagnose.get_health("8432") is None


def test_explain_health_reads_real_health_output():
    """Contract test: a change to vs_data_api.health's report shape breaks this."""
    settings = MagicMock()
    settings.fm_connection_string = "DSN=vs_db"
    settings.fm_link_connection_string = "DSN=wc_link"
    settings.vsdata_wc_url, settings.vsdata_wc_key, settings.vsdata_wc_secret = "https://wc.invalid", "k", "s"
    with patch.object(health.pyodbc, "connect", side_effect=[MagicMock(), RuntimeError("listener")]), patch.object(
        health.wc_api, "get_api", side_effect=RuntimeError("down")
    ):
        report = health.run_checks(settings)
    assert diagnose.explain_health(report) == [
        "The data server can't reach the wc_link FileMaker database.",
        "The data server can't reach the website.",
    ]
    with patch.object(health.pyodbc, "connect"), patch.object(health.wc_api, "get_api"):
        assert diagnose.explain_health(health.run_checks(settings)) == []


# --- website ---


def test_try_website_sends_basic_auth(monkeypatch):
    seen = {}

    def urlopen(request, **kw):
        seen["url"], seen["auth"] = request.full_url, request.get_header("Authorization")
        return FakeResponse([])

    monkeypatch.setattr(diagnose.urllib.request, "urlopen", urlopen)
    assert diagnose.try_website("https://shop/", "ck", "cs") is None
    assert seen["url"] == "https://shop/wp-json/wc/v3/products?per_page=1&_fields=id"
    assert seen["auth"].startswith("Basic ")


def test_explain_http_error():
    explain = diagnose.explain_http_error
    assert explain(urllib.error.HTTPError("u", 401, "no", {}, None))["message"] == "The website rejected our key."
    assert "address in the settings file" in explain(urllib.error.HTTPError("u", 404, "nf", {}, None))["message"]
    rejected = explain(urllib.error.HTTPError("u", 401, "no", {}, None), "https://shop/")
    assert "https://shop/wp-admin/admin.php?page=wc-settings&tab=advanced&section=keys" in rejected["advice"]
    assert "error 502" in explain(urllib.error.HTTPError("u", 502, "bad", {}, None))["message"]
    assert explain(urllib.error.URLError(socket.gaierror()))["message"] == "I can't find the website."
    assert "too long" in explain(urllib.error.URLError(TimeoutError()))["message"]
    assert "too long" in explain(TimeoutError())["message"]
    assert explain(ValueError("odd"))["message"] == "Something unexpected: odd"


# --- log ---


def test_recent_log_errors(tmp_path):
    log = tmp_path / "stderr.log"
    log.write_text("INFO fine\nERROR one\nINFO fine\nTraceback (most recent call last):\nERROR two\n")
    assert diagnose.recent_log_errors(log) == ["ERROR one", "Traceback (most recent call last):", "ERROR two"]
    assert diagnose.recent_log_errors(log, keep=1) == ["ERROR two"]
    assert diagnose.recent_log_errors(log, lines=2) == ["Traceback (most recent call last):", "ERROR two"]
