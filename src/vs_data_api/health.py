"""
Health checks for the services vs-data depends on.

Used by the ``/health`` endpoint (and ``vs doctor``-style tooling). Each check
returns a small dict, never raises, and never includes credentials: connection
strings are reduced to ``server``/``database``.
"""

import re
import time

import pypyodbc as pyodbc

from vs_data_api.vs_data.wc import api as wc_api

WC_TIMEOUT_SECONDS = 10


def describe_connection_string(connection_string: str) -> dict:
    """Return the non-secret parts (server, database or dsn) of a connection string."""
    parts = {}
    for key in ("DSN", "Server", "Port", "Database"):
        match = re.search(rf"(?:^|;)\s*{key}\s*=\s*([^;]*)", connection_string or "", flags=re.IGNORECASE)
        if match:
            parts[key.lower()] = match.group(1).strip()
    return parts


def _timed(check):
    """Run check() and return {"ok": bool, "ms": int, ...}; exceptions become ok=False."""
    started = time.perf_counter()
    try:
        result = check() or {}
        result["ok"] = True
    except Exception as exc:  # noqa: BLE001 - a health check must report, not raise
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    result["ms"] = round((time.perf_counter() - started) * 1000)
    return result


def check_fm(connection_string: str) -> dict:
    """Open (and close) a connection to FileMaker."""

    def connect():
        if not connection_string:
            raise ValueError("connection string is not set")
        connection = pyodbc.connect(connection_string)
        connection.close()

    result = _timed(connect)
    result.update(describe_connection_string(connection_string))
    return result


def check_wc(url: str, key: str, secret: str, verify_ssl: bool = True) -> dict:
    """Request the WooCommerce REST API root, with a short timeout."""

    def request():
        api = wc_api.get_api(url, key, secret, verify_ssl=verify_ssl)
        api.timeout = WC_TIMEOUT_SECONDS
        api.get("").raise_for_status()

    result = _timed(request)
    result["url"] = url
    return result


def run_checks(settings) -> dict:
    """Check main db, link db and WooCommerce. ``status`` is ``ok`` or ``degraded``."""
    checks = {
        "filemaker": check_fm(settings.fm_connection_string),
        "filemaker_link": check_fm(settings.fm_link_connection_string),
        "woocommerce": check_wc(
            settings.vsdata_wc_url, settings.vsdata_wc_key, settings.vsdata_wc_secret, settings.vsdata_wc_verify_ssl
        ),
    }
    status = "ok" if all(c["ok"] for c in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
