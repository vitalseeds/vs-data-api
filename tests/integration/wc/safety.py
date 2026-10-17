"""Refuse to run write tests against anything that looks like production."""

from urllib.parse import urlparse

ALLOW_REMOTE_VAR = "VSDATA_TEST_WC_ALLOW_REMOTE"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOCAL_SUFFIXES = (".local", ".localhost")


def unsafe_reason(url: str, allow_remote: bool = False) -> str | None:
    """Return why `url` must not be written to, or None if it is safe."""
    host = urlparse(url or "").hostname
    if not host:
        return "VSDATA_TEST_WC_URL is not set to a usable URL"
    if allow_remote:
        return None
    if host in LOCAL_HOSTS or host.endswith(LOCAL_SUFFIXES):
        return None
    return f"{host} is not a local host; set {ALLOW_REMOTE_VAR}=1 to run write tests against it"
