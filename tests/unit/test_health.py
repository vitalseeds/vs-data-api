from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from vs_data_api import health
from vs_data_api.main import app

PWD_STRING = "Driver={FileMaker ODBC};Server=127.0.0.1;Port=2399;Database=test_vs_db;UID=vsdata;PWD=s3cret;"


def test_describe_connection_string_hides_credentials():
    parts = health.describe_connection_string(PWD_STRING)
    assert parts == {"server": "127.0.0.1", "port": "2399", "database": "test_vs_db"}
    assert "s3cret" not in str(parts)
    assert health.describe_connection_string("DSN=vs_db_odbc;UID=u;PWD=p") == {"dsn": "vs_db_odbc"}
    assert health.describe_connection_string("") == {}


def test_check_fm_ok_closes_connection():
    with patch.object(health.pyodbc, "connect") as connect:
        result = health.check_fm(PWD_STRING)
    connect.assert_called_once_with(PWD_STRING)
    connect.return_value.close.assert_called_once()
    assert result["ok"] is True
    assert result["database"] == "test_vs_db"
    assert "ms" in result


def test_check_fm_failure_is_reported_not_raised():
    with patch.object(health.pyodbc, "connect", side_effect=RuntimeError("Failed to connect to listener (3)")):
        result = health.check_fm(PWD_STRING)
    assert result["ok"] is False
    assert "listener (3)" in result["error"]
    assert "s3cret" not in str(result)


def test_check_fm_without_connection_string():
    result = health.check_fm("")
    assert result["ok"] is False
    assert "not set" in result["error"]


def test_check_wc_uses_short_timeout():
    api = MagicMock()
    with patch.object(health.wc_api, "get_api", return_value=api):
        result = health.check_wc("http://wc.example", "k", "s")
    assert result["ok"] is True
    assert api.timeout == health.WC_TIMEOUT_SECONDS
    api.get.assert_called_once_with("")
    assert result["url"] == "http://wc.example"
    assert "k" not in result.get("error", "")


def _settings():
    s = MagicMock()
    s.fm_connection_string = PWD_STRING
    s.fm_link_connection_string = PWD_STRING.replace("test_vs_db", "test_link_db")
    s.vsdata_wc_url, s.vsdata_wc_key, s.vsdata_wc_secret = "http://wc.example", "k", "s"
    return s


def test_run_checks_degraded_when_any_check_fails():
    ok = {"ok": True, "ms": 1}
    bad = {"ok": False, "error": "x", "ms": 1}
    with patch.object(health, "check_fm", side_effect=[ok, bad]), patch.object(health, "check_wc", return_value=ok):
        report = health.run_checks(_settings())
    assert report["status"] == "degraded"
    assert report["checks"]["filemaker_link"]["ok"] is False


def test_health_endpoint_status_codes():
    from vs_data_api.main import get_settings

    app.dependency_overrides[get_settings] = _settings
    try:
        client = TestClient(app)
        with patch.object(health, "run_checks", return_value={"status": "ok", "checks": {}}):
            assert client.get("/health").status_code == 200
        with patch.object(health, "run_checks", return_value={"status": "degraded", "checks": {}}):
            response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["status"] == "degraded"
    finally:
        app.dependency_overrides.pop(get_settings, None)
