import pytest

from vs_data_api.config import Settings


@pytest.fixture
def required_env(monkeypatch):
    monkeypatch.setenv("VSDATA_FM_CONNECTION_STRING", "x")
    monkeypatch.setenv("VSDATA_FM_LINK_CONNECTION_STRING", "x")
    monkeypatch.setenv("VSDATA_WC_URL", "https://site.test")
    monkeypatch.setenv("VSDATA_WC_KEY", "ck")
    monkeypatch.setenv("VSDATA_WC_SECRET", "cs")
    monkeypatch.delenv("VSDATA_WC_VERIFY_SSL", raising=False)


def test_verify_ssl_defaults_to_true(required_env):
    assert Settings().vsdata_wc_verify_ssl is True


def test_wc_verify_ssl_false_from_environment(required_env, monkeypatch):
    # config.ini's wc_verify_ssl becomes VSDATA_WC_VERIFY_SSL
    monkeypatch.setenv("VSDATA_WC_VERIFY_SSL", "false")
    assert Settings().vsdata_wc_verify_ssl is False
