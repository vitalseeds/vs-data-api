"""Deeper diagnosis: try FileMaker, the server and the website, and turn raw errors into plain English."""

import base64
import collections
import http.client
import json
import re
import socket
import ssl
import urllib.error
import urllib.request

ODBC_TIMEOUT = 10
LOCAL_TIMEOUT = 30  # /health itself waits up to 10s on the website
WEBSITE_TIMEOUT = 10

HEALTH_NAMES = {
    "filemaker": "the vs_db FileMaker database",
    "filemaker_link": "the wc_link FileMaker database",
    "woocommerce": "the website",
}


def unexpected(error) -> dict:
    return {"message": f"Something unexpected: {error}", "advice": ""}


# --- FileMaker over ODBC ---


def database_name(connection_string: str) -> str:
    for key in ("Database", "DSN"):
        match = re.search(rf"(?:^|;)\s*{key}\s*=\s*([^;]*)", connection_string or "", flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "the database"


def try_odbc(connection_string: str):
    """Connect and disconnect. Returns the error text, or None if it worked."""
    if not connection_string.strip():
        return "connection string is not set"
    try:
        import pypyodbc  # imported here so a broken ODBC setup can't stop the doctor starting
    except Exception as error:  # noqa: BLE001 - ImportError, or pypyodbc's own OdbcNoLibrary
        return f"ODBC driver manager could not be loaded: {type(error).__name__}: {error}"
    try:
        pypyodbc.connect(connection_string, timeout=ODBC_TIMEOUT).close()
    except Exception as error:  # noqa: BLE001 - every failure is something to explain
        return f"{type(error).__name__}: {error}"
    return None


def explain_odbc_error(error: str, database: str) -> dict:
    text = error.lower()
    if "not set" in text:
        return {
            "message": f"The FileMaker settings for {database} are missing from the settings file.",
            "advice": "",
        }
    if "im002" in text or "could not be loaded" in text or ("driver" in text and "not found" in text):
        return {
            "message": "The FileMaker ODBC driver isn't installed on this computer.",
            "advice": "It needs installing from Claris before the data server can work.",
        }
    if "listener" in text:
        return {
            "message": f"FileMaker isn't sharing {database} over ODBC.",
            "advice": f"Make sure {database} is open in FileMaker, then choose File > Sharing > "
            "Enable ODBC/JDBC and switch sharing on for it.",
        }
    if "password" in text or "login" in text or "account" in text:
        return {
            "message": f"FileMaker rejected the user name or password for {database}.",
            "advice": "The password in the settings file may be out of date.",
        }
    return unexpected(error)


# --- the data server's /health ---


def _get_json(url: str):
    context = ssl._create_unverified_context() if url.startswith("https") else None  # self-signed is fine
    try:
        with urllib.request.urlopen(url, timeout=LOCAL_TIMEOUT, context=context) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code == 503:  # /health answers 503, with the same body, when degraded
            return json.loads(error.read())
        raise


def get_health(port):
    """The local server's /health report, over http or https, or None if it doesn't answer."""
    for scheme in ("http", "https"):
        try:
            return _get_json(f"{scheme}://localhost:{port}/health")
        except (OSError, ValueError, http.client.HTTPException):
            continue
    return None


def explain_health(report: dict) -> list:
    """One sentence per failing check in a vs_data_api.health report."""
    return [
        f"The data server can't reach {HEALTH_NAMES.get(name, name)}."
        for name, check in report.get("checks", {}).items()
        if not check.get("ok")
    ]


# --- the website ---


def try_website(url: str, key: str, secret: str):
    """Make one small authenticated WooCommerce request. Returns the error, or None if it worked."""
    request = urllib.request.Request(f"{url.rstrip('/')}/wp-json/wc/v3/products?per_page=1&_fields=id")
    token = base64.b64encode(f"{key}:{secret}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")
    request.add_header("User-Agent", "vsdata-doctor")
    try:
        urllib.request.urlopen(request, timeout=WEBSITE_TIMEOUT).close()
    except (OSError, http.client.HTTPException) as error:
        return error
    return None


def explain_http_error(error, url: str = "") -> dict:
    if isinstance(error, urllib.error.HTTPError):
        if error.code in (401, 403):
            return {
                "message": "The website rejected our key.",
                "advice": "The WooCommerce key in the settings file may have been changed or removed."
                + (f" Keys are managed at {url.rstrip('/')}/wp-admin/admin.php?page=wc-settings&tab=advanced&section=keys" if url else ""),
            }
        if error.code == 404:
            return {
                "message": "I can't find the shop at the website address in the settings file.",
                "advice": "The wc_url setting may be wrong.",
            }
        if error.code >= 500:
            return {
                "message": f"The website is having problems (error {error.code}).",
                "advice": "Wait a few minutes and run me again.",
            }
        return unexpected(error)
    reason = getattr(error, "reason", error)
    if isinstance(reason, socket.gaierror):
        return {
            "message": "I can't find the website.",
            "advice": "Check the internet is working: can you open any website?",
        }
    if isinstance(reason, TimeoutError):
        return {
            "message": "The website is taking too long to answer.",
            "advice": "Check the internet is working, then run me again.",
        }
    return unexpected(error)


# --- the server log ---


def recent_log_errors(path, lines=200, keep=5) -> list:
    """The last few error lines among the last `lines` lines of the log."""
    with open(path, encoding="utf-8", errors="replace") as log:
        tail = collections.deque(log, maxlen=lines)
    errors = [line.rstrip() for line in tail if any(word in line for word in ("ERROR", "Traceback", "Exception"))]
    return errors[-keep:]
