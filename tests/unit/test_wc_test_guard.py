import pytest

from tests.integration.wc.safety import unsafe_reason


@pytest.mark.parametrize(
    "url",
    [
        "http://vitalseeds.local",
        "http://vitalseeds.local/",
        "https://vitalseeds.local:8443",
        "http://localhost:8888",
        "http://127.0.0.1",
        "http://[::1]:8080",
        "http://shop.localhost",
    ],
)
def test_local_hosts_are_safe(url):
    assert unsafe_reason(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://www.vitalseeds.co.uk",
        "http://vitalseeds.local.example.com",
        "http://notlocal",
        "http://example.com/.local",
        "https://wc.invalid",
    ],
)
def test_other_hosts_are_unsafe(url):
    reason = unsafe_reason(url)
    assert reason and "VSDATA_TEST_WC_ALLOW_REMOTE" in reason


def test_remote_host_allowed_with_opt_in():
    assert unsafe_reason("https://staging.example.com", allow_remote=True) is None


@pytest.mark.parametrize("allow_remote", [False, True])
def test_unset_url_is_unsafe_even_with_opt_in(allow_remote):
    assert "not set" in unsafe_reason("", allow_remote=allow_remote)
