# vsdata-doctor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `vsdata-doctor.exe`, a standalone first-line debugger that office staff double-click when the data app breaks. It checks FileMaker, the data server and the website, explains each problem in plain English, offers a few safe fixes, and ships as its own asset on each tagged release.

**Architecture:** A new package, `src/vs_doctor/`, that never imports `vs_data_api`. It has seven small modules, each with one job:
- `config` reads `config.ini`;
- `windows` makes the OS calls;
- `diagnose` turns raw errors into plain English;
- `fixes` performs the fixes;
- `checks` holds one short function per check and the `CHECKS` list;
- `report` does all the printing;
- `__main__` runs the loop.

The modules are plain functions, plus one small `Result` dataclass. A `CLAUDE.md` in the package lists the parts of the app the doctor relies on, so it gets updated when they change.

**Tech Stack:** Python 3.11, stdlib (`configparser`, `urllib`, `subprocess`), `rich` 13.3.1 (already a dependency), `pypyodbc` (already a dependency, imported lazily), pytest, PyInstaller.

**Spec:** [docs/superpowers/specs/2026-10-15-vsdata-doctor-design.md](../specs/2026-10-15-vsdata-doctor-design.md)

## Global Constraints

- `vs_doctor` imports only the stdlib, `rich` and `pypyodbc`. It never imports `vs_data_api`, `fastapi`, `pandas`, `numpy` or `woocommerce`, directly or indirectly.
- `pypyodbc` is imported inside `diagnose.try_odbc` only, so a missing ODBC driver manager can never stop the doctor from starting.
- Only `windows.py` calls the OS (subprocess, `ctypes`, `os.startfile`), and only `report.py` prints.
- The messages and advice staff see are plain English, with no jargon in the message line. Jokes appear only in the art and the closing quip.
- All user-visible text is printed as `rich.text.Text`, never as markup strings. Messages contain things like `[vsdata]` that `rich` would otherwise parse as markup.
- Fixes run only after `Shall I try? [y/N]`, and the default is no. Fixes never edit config, delete files or touch FileMaker data.
- `[doctor]` defaults are `service_name = VSDataAPI`, `log_file = C:\Program Files\VSData\logs\stderr.log`, `contact = Call or WhatsApp Tom.` and `docs_url =` (empty). `fm_files` is required and has no default.
- The report is saved to `%LOCALAPPDATA%\VSData\doctor-<YYYY-MM-DD-HHMMSS>.txt`, or to the config dir when `LOCALAPPDATA` is unset.
- The exit code is 0 when no check failed and 1 when any did. A crash of the doctor itself exits with 2. `--no-pause` skips the final "Press Enter".
- `make test` must stay green. Every new test is in the default suite and needs no FileMaker, WooCommerce or Windows.
- The service-or-Task-Scheduler question is postponed. This plan assumes the `VSDataAPI` NSSM service, as in `deploy/windows/install-service.ps1`.

## Review Focus

These are inputs the spec implies but no feature test exercises. Each is pinned by a test in the task named.

1. **`config.ini` saved by Notepad with a UTF-8 BOM.** The doctor should still read it, not report "a mistake in the settings file". Test in Task 1.
2. **A `%` in a password inside a connection string.** `configparser`'s default interpolation would raise, so the doctor reads with `interpolation=None`. Test in Task 1.
3. **The server running over https**, which `standalone.get_ssl_paths` turns on automatically when certificates exist. `/health` must still be reached by falling back to https with an unverified context. Test in Task 3.
4. **No ODBC driver manager, or `pypyodbc` failing to import.** This must come out as "the FileMaker ODBC driver isn't installed", not as a crash. Test in Task 3.
5. **A staff member answering the fix prompt with Enter, `Y`, ` yes ` or `n`.** Only `y` or `yes` (trimmed, any case) runs the fix. Test in Task 6.

---

### Task 1: Package skeleton and config

**Files:**
- Create: `src/vs_doctor/__init__.py`
- Create: `src/vs_doctor/config.py`
- Create: `tests/unit/doctor/__init__.py`
- Create: `tests/unit/doctor/test_config.py`
- Modify: `pyproject.toml` (`[project.scripts]`, and add `[tool.hatch.build.targets.wheel]`)
- Modify: `config/config.ini.example` (append a `[doctor]` section)

**Interfaces:**
- Produces:
  - `DOCTOR_DEFAULTS: dict[str, str]`
  - `get_config_dir() -> Path`
  - `config_path() -> Path`
  - `defaults() -> configparser.ConfigParser`
  - `read_config(path=None) -> configparser.ConfigParser`, which raises `configparser.Error` when the file is malformed
  - `missing_settings(config) -> list[str]`, with entries such as `"wc_url in [vsdata]"`
  - `fm_files(config) -> list[Path]`
  - `report_dir() -> Path`

In development, `src/` is on `sys.path` through the editable install's `.pth` file, so `import vs_doctor` works once the folder exists.

- [ ] **Step 1: Write the failing tests**

`tests/unit/doctor/__init__.py`: an empty file.

`tests/unit/doctor/test_config.py`:

```python
import configparser
import sys

import pytest

from vs_data_api import config as app_config
from vs_doctor import config


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_get_config_dir_matches_the_app(platform, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert config.get_config_dir() == app_config.get_config_dir()


def write(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)
    return path


def test_read_config_fills_doctor_defaults(tmp_path):
    cfg = config.read_config(write(tmp_path / "config.ini", "[vsdata]\nwc_url = https://shop\n"))
    assert cfg["vsdata"]["wc_url"] == "https://shop"
    assert cfg["server"]["port"] == "8432"
    assert cfg["doctor"]["service_name"] == "VSDataAPI"
    assert cfg["doctor"]["contact"] == "Call or WhatsApp Tom."
    assert cfg["doctor"]["docs_url"] == ""


def test_read_config_missing_file_gives_defaults(tmp_path):
    cfg = config.read_config(tmp_path / "nope.ini")
    assert cfg["doctor"]["log_file"] == r"C:\Program Files\VSData\logs\stderr.log"


def test_read_config_accepts_a_notepad_bom(tmp_path):
    path = write(tmp_path / "config.ini", "[vsdata]\nwc_url = https://shop\n", encoding="utf-8-sig")
    assert config.read_config(path)["vsdata"]["wc_url"] == "https://shop"


def test_read_config_allows_percent_in_passwords(tmp_path):
    path = write(tmp_path / "config.ini", "[vsdata]\nfm_connection_string = DSN=x;PWD=50%off;\n")
    assert config.read_config(path)["vsdata"]["fm_connection_string"].endswith("PWD=50%off;")


def test_read_config_raises_on_a_malformed_file(tmp_path):
    with pytest.raises(configparser.Error):
        config.read_config(write(tmp_path / "config.ini", "no section header\n"))


def test_missing_settings_lists_required_keys():
    missing = config.missing_settings(config.defaults())
    assert "wc_url in [vsdata]" in missing
    assert "fm_files in [doctor]" in missing
    assert not any("service_name" in m for m in missing)


def test_fm_files_reads_one_path_per_line(tmp_path):
    path = write(tmp_path / "config.ini", "[doctor]\nfm_files =\n    C:/fm/vs_db.fmp12\n\n    C:/fm/wc_link.fmp12\n")
    files = config.fm_files(config.read_config(path))
    assert [f.name for f in files] == ["vs_db.fmp12", "wc_link.fmp12"]


def test_report_dir_prefers_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert config.report_dir() == tmp_path / "VSData"
    monkeypatch.delenv("LOCALAPPDATA")
    assert config.report_dir() == config.get_config_dir()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --extra test pytest tests/unit/doctor/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vs_doctor'`.

- [ ] **Step 3: Write the implementation**

`src/vs_doctor/__init__.py`:

```python
"""vsdata-doctor: a first-line debugger for the VS Data API. See CLAUDE.md in this folder."""
```

`src/vs_doctor/config.py`:

```python
"""Find and read config.ini: the same file as the server, plus a [doctor] section."""

import configparser
import os
import sys
from pathlib import Path

DOCTOR_DEFAULTS = {
    "fm_files": "",
    "service_name": "VSDataAPI",
    "log_file": r"C:\Program Files\VSData\logs\stderr.log",
    "contact": "Call or WhatsApp Tom.",
    "docs_url": "",
}

REQUIRED = {
    "vsdata": ["fm_connection_string", "fm_link_connection_string", "wc_url", "wc_key", "wc_secret"],
    "doctor": ["fm_files"],
}


def get_config_dir() -> Path:
    """Copied from vs_data_api.config.get_config_dir (a test keeps the two in step)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "VSData"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VSData"
    else:  # Linux and others
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg_config) / "vsdata"


def config_path() -> Path:
    return get_config_dir() / "config.ini"


def defaults() -> configparser.ConfigParser:
    """A config holding only the defaults, used when config.ini can't be read."""
    # interpolation=None: a % in a password must not be treated as a variable
    config = configparser.ConfigParser(interpolation=None)
    config.read_dict({"vsdata": {}, "server": {"port": "8432"}, "doctor": DOCTOR_DEFAULTS})
    return config


def read_config(path=None) -> configparser.ConfigParser:
    """Read config.ini over the defaults. Raises configparser.Error if the file is malformed."""
    config = defaults()
    # utf-8-sig: Notepad may save the file with a byte order mark
    config.read(path or config_path(), encoding="utf-8-sig")
    return config


def missing_settings(config) -> list:
    return [
        f"{key} in [{section}]"
        for section, keys in REQUIRED.items()
        for key in keys
        if not config.get(section, key, fallback="").strip()
    ]


def fm_files(config) -> list:
    return [Path(line.strip()) for line in config["doctor"]["fm_files"].splitlines() if line.strip()]


def report_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "VSData" if local else get_config_dir()
```

- [ ] **Step 4: Register the package and document the config**

In `pyproject.toml`, add to `[project.scripts]`:

```toml
vsdata-doctor = "vs_doctor.__main__:main"
```

Then add this section after `[tool.hatch.metadata]`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/vs_data_api", "src/vs_doctor"]
```

Append to `config/config.ini.example`:

```ini

[doctor]
; Settings for vsdata-doctor, the first-line debugger (see README_standalone_install.md)
; FileMaker files that must be open, one per line (required)
fm_files =
    C:\path\to\vs_db.fmp12
    C:\path\to\wc_link.fmp12
; Name of the Windows service that runs the data server
service_name = VSDataAPI
; Server error log, scanned for recent errors
log_file = C:\Program Files\VSData\logs\stderr.log
; Who to ask for help: shown at the end of the report when something is still failing
contact = Call or WhatsApp Tom.
; Vital Seeds documentation site, suggested while waiting to hear back (optional)
; docs_url = https://...
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv sync --extra test && uv run --extra test pytest tests/unit/doctor/test_config.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/vs_doctor tests/unit/doctor pyproject.toml config/config.ini.example
git commit -m "Add vs_doctor package with config reading (#118)"
```

---

### Task 2: Windows wrappers

**Files:**
- Create: `src/vs_doctor/windows.py`
- Create: `tests/unit/doctor/test_windows.py`

**Interfaces:**
- Produces:
  - `is_windows() -> bool`
  - `running_processes() -> list[str]`
  - `filemaker_running() -> bool`
  - `service_state(name: str) -> str | None`, which returns, for example, `"RUNNING"` or `"STOPPED"`, and `None` when the service doesn't exist
  - `is_admin() -> bool`
  - `start_service(name: str) -> None`
  - `open_file(path) -> None`
  - `_run(args: list[str]) -> str`, the single subprocess call, which tests monkeypatch

- [ ] **Step 1: Write the failing tests**

`tests/unit/doctor/test_windows.py`:

```python
from vs_doctor import windows

TASKLIST = '"System","4","Services","0","144 K"\n"FileMaker Pro.exe","1234","Console","1","250,000 K"\n'
SC_RUNNING = "SERVICE_NAME: VSDataAPI\n        TYPE               : 10  WIN32_OWN_PROCESS\n        STATE              : 4  RUNNING\n"
SC_MISSING = "[SC] EnumQueryServicesStatus:OpenService FAILED 1060:\n\nThe specified service does not exist.\n"


def test_running_processes_reads_tasklist_csv(monkeypatch):
    monkeypatch.setattr(windows, "_run", lambda args: TASKLIST)
    assert windows.running_processes() == ["System", "FileMaker Pro.exe"]


def test_filemaker_running(monkeypatch):
    monkeypatch.setattr(windows, "_run", lambda args: TASKLIST)
    assert windows.filemaker_running() is True
    monkeypatch.setattr(windows, "_run", lambda args: '"System","4","Services","0","144 K"\n')
    assert windows.filemaker_running() is False


def test_service_state(monkeypatch):
    calls = []
    monkeypatch.setattr(windows, "_run", lambda args: calls.append(args) or SC_RUNNING)
    assert windows.service_state("VSDataAPI") == "RUNNING"
    assert calls == [["sc", "query", "VSDataAPI"]]


def test_service_state_none_when_not_installed(monkeypatch):
    monkeypatch.setattr(windows, "_run", lambda args: SC_MISSING)
    assert windows.service_state("VSDataAPI") is None


def test_is_admin_false_off_windows():
    if not windows.is_windows():
        assert windows.is_admin() is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --extra test pytest tests/unit/doctor/test_windows.py -v`
Expected: FAIL with `ImportError: cannot import name 'windows'`.

- [ ] **Step 3: Write the implementation**

`src/vs_doctor/windows.py`:

```python
"""Thin wrappers around the Windows calls the doctor makes. The only module that talks to the OS."""

import ctypes
import os
import subprocess
import sys


def is_windows() -> bool:
    return sys.platform == "win32"


def _run(args) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout


def running_processes() -> list:
    """Image names of running processes, e.g. ["FileMaker Pro.exe", ...]."""
    output = _run(["tasklist", "/NH", "/FO", "CSV"])
    return [line.split('","')[0].strip('"') for line in output.splitlines() if line.strip()]


def filemaker_running() -> bool:
    return any(name.lower().startswith("filemaker") for name in running_processes())


def service_state(name):
    """RUNNING, STOPPED, ... or None if there is no such service."""
    for line in _run(["sc", "query", name]).splitlines():
        if line.strip().startswith("STATE"):
            return line.split()[-1]
    return None


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):  # not Windows
        return False


def start_service(name) -> None:
    _run(["sc", "start", name])


def open_file(path) -> None:
    """Open a file with its default app, as a double-click would (FileMaker for .fmp12)."""
    os.startfile(str(path))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --extra test pytest tests/unit/doctor/test_windows.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vs_doctor/windows.py tests/unit/doctor/test_windows.py
git commit -m "Add Windows wrappers for vsdata-doctor (#118)"
```

---

### Task 3: Diagnosis

**Files:**
- Create: `src/vs_doctor/diagnose.py`
- Create: `tests/unit/doctor/test_diagnose.py`

**Interfaces:**
- Produces:
  - `database_name(connection_string: str) -> str`
  - `try_odbc(connection_string: str) -> str | None`, which returns the error text, or `None` when it connected
  - `explain_odbc_error(error: str, database: str) -> dict`, with keys `message` and `advice`
  - `get_health(port) -> dict | None`
  - `explain_health(report: dict) -> list[str]`
  - `try_website(url, key, secret) -> Exception | None`
  - `explain_http_error(error: Exception) -> dict`, with keys `message` and `advice`
  - `recent_log_errors(path, lines=200, keep=5) -> list[str]`

  The `message`/`advice` dicts are unpacked straight into `Result` by `checks.py`.

The ODBC error texts below come from `tests/unit/test_health.py`, which has `Failed to connect to listener`, and from the Windows driver manager (`IM002`). The login-failure wording is a best guess, so check it on the VM in Task 8 and add any real wording found there to `explain_odbc_error` and its test.

- [ ] **Step 1: Write the failing tests**

`tests/unit/doctor/test_diagnose.py`:

```python
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
    assert "ImportError" in error
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --extra test pytest tests/unit/doctor/test_diagnose.py -v`
Expected: FAIL with `ImportError: cannot import name 'diagnose'`.

- [ ] **Step 3: Write the implementation**

`src/vs_doctor/diagnose.py`:

```python
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
    if "im002" in text or "importerror" in text or "driver" in text and "not found" in text:
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


def explain_http_error(error) -> dict:
    if isinstance(error, urllib.error.HTTPError):
        if error.code in (401, 403):
            return {
                "message": "The website rejected our key.",
                "advice": "The WooCommerce key in the settings file may have been changed or removed.",
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --extra test pytest tests/unit/doctor/test_diagnose.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vs_doctor/diagnose.py tests/unit/doctor/test_diagnose.py
git commit -m "Add vsdata-doctor diagnosis of ODBC, /health, website and log errors (#118)"
```

---

### Task 4: Fixes

**Files:**
- Create: `src/vs_doctor/fixes.py`
- Create: `tests/unit/doctor/test_fixes.py`

**Interfaces:**
- Consumes:
  - `config.fm_files(config)` (Task 1)
  - `windows.open_file`, `windows.filemaker_running`, `windows.start_service` and `windows.service_state` (Task 2)
- Produces:
  - `wait_until(condition, seconds) -> bool`
  - `open_filemaker(config) -> bool`
  - `start_service(config) -> bool`

  Every fix has the signature `fix(config) -> bool`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/doctor/test_fixes.py`:

```python
from pathlib import Path

import pytest

from vs_doctor import config, fixes, windows


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fixes.time, "sleep", lambda seconds: None)


def test_wait_until():
    answers = iter([False, False, True])
    assert fixes.wait_until(lambda: next(answers), seconds=5) is True
    assert fixes.wait_until(lambda: False, seconds=3) is False


def test_open_filemaker_opens_each_file(monkeypatch):
    cfg = config.defaults()
    cfg["doctor"]["fm_files"] = "\nC:/fm/vs_db.fmp12\nC:/fm/wc_link.fmp12"
    opened = []
    monkeypatch.setattr(windows, "open_file", opened.append)
    monkeypatch.setattr(windows, "filemaker_running", lambda: True)
    assert fixes.open_filemaker(cfg) is True
    assert opened == [Path("C:/fm/vs_db.fmp12"), Path("C:/fm/wc_link.fmp12")]


def test_start_service_waits_for_running(monkeypatch):
    cfg = config.defaults()
    started = []
    states = iter(["START_PENDING", "RUNNING"])
    monkeypatch.setattr(windows, "start_service", started.append)
    monkeypatch.setattr(windows, "service_state", lambda name: next(states))
    assert fixes.start_service(cfg) is True
    assert started == ["VSDataAPI"]


def test_start_service_gives_up(monkeypatch):
    monkeypatch.setattr(windows, "start_service", lambda name: None)
    monkeypatch.setattr(windows, "service_state", lambda name: "STOPPED")
    assert fixes.start_service(config.defaults()) is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --extra test pytest tests/unit/doctor/test_fixes.py -v`
Expected: FAIL with `ImportError: cannot import name 'fixes'`.

- [ ] **Step 3: Write the implementation**

`src/vs_doctor/fixes.py`:

```python
"""The fixes the doctor offers. Each takes the config and returns True if it worked."""

import time

from vs_doctor import config as doctor_config
from vs_doctor import windows


def wait_until(condition, seconds) -> bool:
    """Check condition() once a second for up to `seconds`."""
    for _ in range(seconds):
        if condition():
            return True
        time.sleep(1)
    return condition()


def open_filemaker(config) -> bool:
    """Open the FileMaker files (which starts FileMaker) and wait for it to appear."""
    for path in doctor_config.fm_files(config):
        windows.open_file(path)
    return wait_until(windows.filemaker_running, seconds=60)


def start_service(config) -> bool:
    """Start the data server's service (needs admin) and wait for it to be running."""
    name = config["doctor"]["service_name"]
    windows.start_service(name)
    return wait_until(lambda: windows.service_state(name) == "RUNNING", seconds=30)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --extra test pytest tests/unit/doctor/test_fixes.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vs_doctor/fixes.py tests/unit/doctor/test_fixes.py
git commit -m "Add vsdata-doctor fixes: open FileMaker, start the service (#118)"
```

---

### Task 5: Checks

**Files:**
- Create: `src/vs_doctor/checks.py`
- Create: `tests/unit/doctor/test_checks.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4, with the signatures listed there.
- Produces:
  - `Result(status, message, advice="", detail="", fix=None)`, where `status` is one of `"ok"`, `"warn"`, `"fail"` or `"skip"`
  - the helpers `ok(message)`, `skip(message)` and `fail(message, advice="", fix=None)`
  - the seven `check_*(config) -> Result` functions
  - `CHECKS: list`

- [ ] **Step 1: Write the failing tests**

`tests/unit/doctor/test_checks.py`:

```python
import pytest

from vs_doctor import checks, config, diagnose, fixes, windows


@pytest.fixture
def cfg():
    c = config.defaults()
    c["vsdata"].update(
        {
            "fm_connection_string": "Driver={FileMaker ODBC};Database=vs_db;",
            "fm_link_connection_string": "Driver={FileMaker ODBC};Database=wc_link;",
            "wc_url": "https://shop",
            "wc_key": "ck",
            "wc_secret": "cs",
        }
    )
    c["doctor"]["fm_files"] = "\nC:/fm/vs_db.fmp12\nC:/fm/wc_link.fmp12"
    return c


@pytest.fixture
def on_windows(monkeypatch):
    monkeypatch.setattr(windows, "is_windows", lambda: True)


def test_checks_run_in_root_cause_order():
    assert [c.__name__ for c in checks.CHECKS] == [
        "check_config",
        "check_filemaker_open",
        "check_filemaker_odbc",
        "check_server_running",
        "check_server_health",
        "check_website",
        "check_server_log",
    ]


def test_check_config(cfg, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path)
    assert "can't find the settings file" in checks.check_config(cfg).message
    (tmp_path / "config.ini").write_text("not ini")
    result = checks.check_config(cfg)
    assert (result.status, result.message) == ("fail", "The settings file has a mistake in it.")
    (tmp_path / "config.ini").write_text("[vsdata]\n")
    assert checks.check_config(cfg).status == "ok"
    assert "wc_url in [vsdata]" in checks.check_config(config.defaults()).message


def test_windows_only_checks_skip_elsewhere(cfg, monkeypatch):
    monkeypatch.setattr(windows, "is_windows", lambda: False)
    assert checks.check_filemaker_open(cfg).status == "skip"
    assert checks.check_server_running(cfg).status == "skip"


def test_check_filemaker_open(cfg, on_windows, monkeypatch):
    monkeypatch.setattr(windows, "filemaker_running", lambda: True)
    assert checks.check_filemaker_open(cfg).status == "ok"
    monkeypatch.setattr(windows, "filemaker_running", lambda: False)
    result = checks.check_filemaker_open(cfg)
    assert (result.message, result.fix) == ("FileMaker isn't open.", fixes.open_filemaker)
    cfg["doctor"]["fm_files"] = ""
    assert checks.check_filemaker_open(cfg).fix is None  # nothing to open


def test_check_filemaker_odbc(cfg, monkeypatch):
    monkeypatch.setattr(diagnose, "try_odbc", lambda cs: None)
    assert checks.check_filemaker_odbc(cfg).status == "ok"
    monkeypatch.setattr(diagnose, "try_odbc", lambda cs: "Error: listener" if "wc_link" in cs else None)
    assert checks.check_filemaker_odbc(cfg).message == "FileMaker isn't sharing wc_link over ODBC."


def test_check_server_running(cfg, on_windows, monkeypatch):
    monkeypatch.setattr(windows, "service_state", lambda name: "RUNNING")
    assert checks.check_server_running(cfg).status == "ok"
    monkeypatch.setattr(windows, "service_state", lambda name: None)
    assert "can't find the data server" in checks.check_server_running(cfg).message
    monkeypatch.setattr(windows, "service_state", lambda name: "STOPPED")
    monkeypatch.setattr(windows, "is_admin", lambda: False)
    result = checks.check_server_running(cfg)
    assert result.fix is None and "Run as administrator" in result.advice
    monkeypatch.setattr(windows, "is_admin", lambda: True)
    assert checks.check_server_running(cfg).fix is fixes.start_service


def test_check_server_health(cfg, monkeypatch):
    monkeypatch.setattr(diagnose, "get_health", lambda port: None)
    assert checks.check_server_health(cfg).message == "The data server isn't answering."
    monkeypatch.setattr(diagnose, "get_health", lambda port: {"status": "ok", "checks": {"filemaker": {"ok": True}}})
    assert checks.check_server_health(cfg).status == "ok"
    monkeypatch.setattr(diagnose, "get_health", lambda port: {"checks": {"woocommerce": {"ok": False}}})
    assert checks.check_server_health(cfg).message == "The data server can't reach the website."


def test_check_website(cfg, monkeypatch):
    monkeypatch.setattr(diagnose, "try_website", lambda url, key, secret: None)
    assert checks.check_website(cfg).status == "ok"
    monkeypatch.setattr(diagnose, "try_website", lambda url, key, secret: TimeoutError())
    assert "too long" in checks.check_website(cfg).message
    cfg["vsdata"]["wc_url"] = ""
    assert "missing" in checks.check_website(cfg).message


def test_check_server_log(cfg, tmp_path):
    cfg["doctor"]["log_file"] = str(tmp_path / "missing.log")
    assert checks.check_server_log(cfg).status == "skip"
    log = tmp_path / "stderr.log"
    log.write_text("INFO fine\n")
    cfg["doctor"]["log_file"] = str(log)
    assert checks.check_server_log(cfg).status == "ok"
    log.write_text("ERROR boom\n")
    result = checks.check_server_log(cfg)
    assert (result.status, result.detail) == ("warn", "ERROR boom")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --extra test pytest tests/unit/doctor/test_checks.py -v`
Expected: FAIL with `ImportError: cannot import name 'checks'`.

- [ ] **Step 3: Write the implementation**

`src/vs_doctor/checks.py`:

```python
"""What the doctor checks. Each check takes the config and returns a Result; CHECKS lists them in order."""

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from vs_doctor import config as doctor_config
from vs_doctor import diagnose, fixes, windows

NOT_WINDOWS = "Only checked on Windows."


@dataclass
class Result:
    status: str  # "ok", "warn", "fail" or "skip"
    message: str
    advice: str = ""
    detail: str = ""  # extra lines shown dimmed, e.g. log errors
    fix: Optional[Callable] = None  # from fixes.py: fix(config) -> bool


def ok(message):
    return Result("ok", message)


def skip(message):
    return Result("skip", message)


def fail(message, advice="", fix=None):
    return Result("fail", message, advice, fix=fix)


def check_config(config):
    path = doctor_config.config_path()
    if not path.exists():
        return fail(f"I can't find the settings file at {path}.", advice="It needs setting up before anything else will work.")
    try:
        doctor_config.read_config(path)
    except configparser.Error as error:
        return fail("The settings file has a mistake in it.", advice=str(error).splitlines()[0])
    missing = doctor_config.missing_settings(config)
    if missing:
        return fail(f"The settings file is missing: {', '.join(missing)}.")
    return ok("The settings file is in place.")


def check_filemaker_open(config):
    if not windows.is_windows():
        return skip(NOT_WINDOWS)
    if windows.filemaker_running():
        return ok("FileMaker is open.")
    fix = fixes.open_filemaker if doctor_config.fm_files(config) else None
    return fail("FileMaker isn't open.", advice="Open vs_db and wc_link in FileMaker, then run me again.", fix=fix)


def check_filemaker_odbc(config):
    for key in ("fm_connection_string", "fm_link_connection_string"):
        connection_string = config["vsdata"].get(key, "")
        error = diagnose.try_odbc(connection_string)
        if error:
            database = diagnose.database_name(connection_string)
            return Result("fail", **diagnose.explain_odbc_error(error, database))
    return ok("FileMaker answers on ODBC (both databases).")


def check_server_running(config):
    if not windows.is_windows():
        return skip(NOT_WINDOWS)
    name = config["doctor"]["service_name"]
    state = windows.service_state(name)
    if state == "RUNNING":
        return ok("The data server is running.")
    if state is None:
        return fail(f"I can't find the data server ({name}) on this computer.", advice="It may not be installed here.")
    if not windows.is_admin():
        return fail(
            "The data server is switched off.",
            advice="Close me, right-click vsdata-doctor and choose Run as administrator, then I can start it.",
        )
    return fail("The data server is switched off.", advice="Start it.", fix=fixes.start_service)


def check_server_health(config):
    report = diagnose.get_health(config["server"]["port"])
    if report is None:
        return fail("The data server isn't answering.", advice="If it was only just started, wait a minute and run me again.")
    problems = diagnose.explain_health(report)
    if not problems:
        return ok("The data server says everything is fine.")
    return fail(" ".join(problems), advice="If FileMaker passed above, the data server's own settings are wrong.")


def check_website(config):
    url = config["vsdata"].get("wc_url", "")
    if not url:
        return fail("The website address is missing from the settings file.")
    error = diagnose.try_website(url, config["vsdata"].get("wc_key", ""), config["vsdata"].get("wc_secret", ""))
    if error is None:
        return ok("The website answers.")
    return Result("fail", **diagnose.explain_http_error(error))


def check_server_log(config):
    path = Path(config["doctor"]["log_file"])
    if not path.exists():
        return skip(f"No server log at {path}.")
    errors = diagnose.recent_log_errors(path)
    if not errors:
        return ok("No recent errors in the server log.")
    return Result("warn", "The server log has recent errors.", advice="These are for whoever helps you.", detail="\n".join(errors))


CHECKS = [
    check_config,
    check_filemaker_open,
    check_filemaker_odbc,
    check_server_running,
    check_server_health,
    check_website,
    check_server_log,
]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --extra test pytest tests/unit/doctor/test_checks.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vs_doctor/checks.py tests/unit/doctor/test_checks.py
git commit -m "Add vsdata-doctor checks (#118)"
```

---

### Task 6: Report

**Files:**
- Create: `src/vs_doctor/report.py`
- Create: `tests/unit/doctor/test_report.py`

**Interfaces:**
- Consumes: `checks.Result` (Task 5) and `config` (Task 1).
- Produces:
  - `console`, the module-level `rich.console.Console(record=True)`
  - `header()`
  - `check_line(result)`
  - `ask_fix() -> bool`
  - `fix_outcome(worked: bool)`
  - `summary(results, config)`
  - `save(folder: Path) -> Path`
  - `saved(path)`
  - `pause()`

- [ ] **Step 1: Write the failing tests**

`tests/unit/doctor/test_report.py`:

```python
import io

import pytest
from rich.console import Console

from vs_doctor import checks, config, report


@pytest.fixture(autouse=True)
def fresh_console(monkeypatch):
    console = Console(record=True, file=io.StringIO(), width=100, safe_box=True, emoji=False, highlight=False)
    monkeypatch.setattr(report, "console", console)
    return console


def text():
    return report.console.export_text(clear=False)


def test_check_line_marks_and_keeps_brackets():
    report.check_line(checks.fail("The settings file is missing: wc_url in [vsdata]."))
    report.check_line(checks.Result("warn", "Log errors.", detail="ERROR one\nERROR two"))
    out = text()
    assert "XX" in out and "wc_url in [vsdata]." in out  # brackets are not eaten as markup
    assert "!!" in out and "      ERROR two" in out


@pytest.mark.parametrize(("answer", "expected"), [("", False), ("n", False), ("y", True), ("Y", True), (" yes ", True)])
def test_ask_fix_defaults_to_no(monkeypatch, answer, expected):
    monkeypatch.setattr(report.console, "input", lambda prompt: answer)
    assert report.ask_fix() is expected


def test_summary_all_ok():
    report.summary([checks.ok("Fine."), checks.skip("Only checked on Windows.")], config.defaults())
    assert "What to do" not in text()


def test_summary_lists_failures_contact_and_docs():
    cfg = config.defaults()
    cfg["doctor"]["docs_url"] = "https://docs.example"
    report.summary([checks.ok("Fine."), checks.fail("FileMaker isn't open.", "Open it.")], cfg)
    out = text()
    assert "What to do" in out
    assert "1. FileMaker isn't open. Open it." in out
    assert "Still stuck? Call or WhatsApp Tom." in out
    assert "https://docs.example" in out


def test_summary_leaves_out_docs_when_unset():
    report.summary([checks.fail("Broken.")], config.defaults())
    assert "docs may help" not in text()


def test_save_writes_the_report(tmp_path):
    report.header()
    report.check_line(checks.ok("Fine."))
    path = report.save(tmp_path / "VSData")
    assert path.name.startswith("doctor-") and path.suffix == ".txt"
    assert "Fine." in path.read_text()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --extra test pytest tests/unit/doctor/test_report.py -v`
Expected: FAIL with `ImportError: cannot import name 'report'`.

- [ ] **Step 3: Write the implementation**

`src/vs_doctor/report.py`:

```python
"""Everything the user sees: the art, a line per check, the summary, and the saved report."""

import datetime
import random
from textwrap import indent

from rich.console import Console
from rich.text import Text

# record=True keeps a copy of everything printed, for save()
console = Console(record=True, safe_box=True, emoji=False, highlight=False)

SEEDLING = r"""
      _
    _(_)_      vsdata-doctor
   (_)@(_)     Let's see what's poorly.
     (_)\
        |
   ~~~~~~~~~
"""

WILTED = r"""
        ,
     __/
    (__  )~
       \|
   ~~~~~~~~~
"""

HAPPY_QUIPS = [
    "Everything is growing nicely.",
    "Clean bill of health!",
    "Nothing wrong here. Have a biscuit.",
]

SAD_QUIPS = [
    "Bloomin technology eh",
    "Every gardener has a bad day.",
    "We'll have this blooming again soon.",
]

MARKS = {"ok": ("OK", "green"), "warn": ("!!", "yellow"), "fail": ("XX", "red"), "skip": ("--", "dim")}


def header():
    console.print(Text(SEEDLING, style="green"))


def check_line(result):
    mark, style = MARKS[result.status]
    console.print(Text.assemble((f" {mark} ", f"bold {style}"), " ", result.message))
    if result.detail:
        console.print(Text(indent(result.detail, "      "), style="dim"))


def ask_fix() -> bool:
    answer = console.input(Text("      Shall I try? [y/N] "))
    return answer.strip().lower() in ("y", "yes")


def fix_outcome(worked: bool):
    if worked:
        console.print(Text("      That worked.", style="green"))
    else:
        console.print(Text("      That didn't work, sorry.", style="red"))


def summary(results, config):
    failures = [result for result in results if result.status == "fail"]
    console.print()
    if not failures:
        console.print(Text(random.choice(HAPPY_QUIPS), style="bold green"))
        return
    console.print(Text(WILTED, style="yellow"))
    console.print(Text("What to do:", style="bold"))
    for number, result in enumerate(failures, start=1):
        console.print(Text(f"  {number}. {result.message} {result.advice}".rstrip()))
    console.print()
    console.print(Text(f"Still stuck? {config['doctor']['contact']}", style="bold"))
    docs_url = config["doctor"]["docs_url"].strip()
    if docs_url:
        console.print(Text(f"While you wait, the Vital Seeds docs may help: {docs_url}"))
    console.print(Text(random.choice(SAD_QUIPS), style="italic"))


def save(folder):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"doctor-{datetime.datetime.now():%Y-%m-%d-%H%M%S}.txt"
    console.save_text(str(path), clear=False)
    return path


def saved(path):
    console.print(Text(f"\nI've saved this report to {path}. Send it to whoever helps you.", style="dim"))


def pause():
    console.input(Text("\nPress Enter to close."))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --extra test pytest tests/unit/doctor/test_report.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vs_doctor/report.py tests/unit/doctor/test_report.py
git commit -m "Add vsdata-doctor report output (#118)"
```

---

### Task 7: Main loop, smoke test and isolation

**Files:**
- Create: `src/vs_doctor/__main__.py`
- Create: `tests/unit/doctor/test_main.py`
- Create: `tests/smoke/test_doctor.py`
- Modify: `Makefile` (add a `doctor` target and add it to `.PHONY`)

**Interfaces:**
- Consumes: `checks.CHECKS`, `checks.Result`, everything in `report`, and `config.read_config`, `config.defaults` and `config.report_dir`.
- Produces: `main(argv=None) -> int`, `run_check(check, config) -> Result` and `offer_fix(check, result, config) -> Result`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/doctor/test_main.py`:

```python
import io
import subprocess
import sys

import pytest
from rich.console import Console

from vs_doctor import __main__ as doctor
from vs_doctor import checks, config, report


@pytest.fixture(autouse=True)
def quiet(monkeypatch, tmp_path):
    monkeypatch.setattr(report, "console", Console(record=True, file=io.StringIO(), width=100))
    monkeypatch.setattr(config, "report_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "read_config", lambda path=None: config.defaults())


def test_a_crashing_check_does_not_stop_the_run(monkeypatch):
    def check_boom(cfg):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(checks, "CHECKS", [check_boom, lambda cfg: checks.ok("Still here.")])
    assert doctor.main(["--no-pause"]) == 1
    out = report.console.export_text()
    assert "I tripped over my own feet checking check_boom: kaboom" in out
    assert "Still here." in out


def test_exit_code_zero_when_nothing_failed(monkeypatch):
    monkeypatch.setattr(checks, "CHECKS", [lambda cfg: checks.ok("Fine."), lambda cfg: checks.skip("Skipped.")])
    assert doctor.main(["--no-pause"]) == 0


def test_fix_is_offered_and_check_rerun(monkeypatch):
    state = {"fixed": False}

    def fix(cfg):
        state["fixed"] = True
        return True

    def check_thing(cfg):
        return checks.ok("Now fine.") if state["fixed"] else checks.fail("Broken.", fix=fix)

    monkeypatch.setattr(checks, "CHECKS", [check_thing])
    monkeypatch.setattr(report, "ask_fix", lambda: True)
    assert doctor.main(["--no-pause"]) == 0
    out = report.console.export_text()
    assert "That worked." in out and "Now fine." in out


def test_declined_fix_is_not_run(monkeypatch):
    def fix(cfg):
        raise AssertionError("fix ran without permission")

    monkeypatch.setattr(checks, "CHECKS", [lambda cfg: checks.fail("Broken.", fix=fix)])
    monkeypatch.setattr(report, "ask_fix", lambda: False)
    assert doctor.main(["--no-pause"]) == 1


def test_a_crashing_fix_counts_as_not_worked(monkeypatch):
    def fix(cfg):
        raise OSError("access denied")

    monkeypatch.setattr(checks, "CHECKS", [lambda cfg: checks.fail("Broken.", fix=fix)])
    monkeypatch.setattr(report, "ask_fix", lambda: True)
    assert doctor.main(["--no-pause"]) == 1
    assert "That didn't work, sorry." in report.console.export_text()


def test_doctor_never_imports_the_main_app():
    code = (
        "import sys, vs_doctor.__main__; "
        "print(sorted(m for m in sys.modules "
        "if m.split('.')[0] in ('vs_data_api', 'fastapi', 'pandas', 'numpy', 'woocommerce')))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"
```

`tests/smoke/test_doctor.py`:

```python
import os
import subprocess
import sys

from vs_doctor import config


def test_doctor_runs_end_to_end_and_saves_a_report(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    config_dir = config.get_config_dir()
    config_dir.mkdir(parents=True)
    (config_dir / "config.ini").write_text(
        "[vsdata]\n"
        "fm_connection_string = DSN=doctor_smoke_missing\n"
        "fm_link_connection_string = DSN=doctor_smoke_missing\n"
        "wc_url = https://wc.invalid\nwc_key = ck\nwc_secret = cs\n"
        "[server]\nport = 1\n"
        "[doctor]\nfm_files = C:/fm/vs_db.fmp12\n"
        f"log_file = {tmp_path / 'none.log'}\n"
    )

    run = subprocess.run(
        [sys.executable, "-m", "vs_doctor", "--no-pause"], capture_output=True, text=True, timeout=180, env=os.environ
    )

    assert "Traceback" not in run.stdout + run.stderr
    assert run.returncode == 1  # ODBC, server and website all fail here
    assert "What to do" in run.stdout
    reports = list((tmp_path / "local" / "VSData").glob("doctor-*.txt"))
    assert len(reports) == 1
    assert "The settings file is in place." in reports[0].read_text()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --extra test pytest tests/unit/doctor/test_main.py tests/smoke/test_doctor.py -v`
Expected: FAIL with `ImportError: cannot import name '__main__'`, and the smoke test failing with `No module named vs_doctor.__main__`.

- [ ] **Step 3: Write the implementation**

`src/vs_doctor/__main__.py`:

```python
"""vsdata-doctor: run the checks, offer fixes, save the report and wait for Enter."""

import configparser
import sys
import traceback

from vs_doctor import checks, report
from vs_doctor import config as doctor_config


def run_check(check, config):
    try:
        return check(config)
    except Exception as error:  # noqa: BLE001 - the doctor must keep going
        return checks.fail(f"I tripped over my own feet checking {check.__name__}: {error}")


def offer_fix(check, result, config):
    if not report.ask_fix():
        return result
    try:
        worked = result.fix(config)
    except Exception:  # noqa: BLE001 - a failed fix is reported, not raised
        worked = False
    report.fix_outcome(worked)
    result = run_check(check, config)
    report.check_line(result)
    return result


def load_config():
    try:
        return doctor_config.read_config()
    except configparser.Error:
        return doctor_config.defaults()  # check_config reports the mistake


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    config = load_config()
    report.header()
    results = []
    for check in checks.CHECKS:
        result = run_check(check, config)
        report.check_line(result)
        if result.status == "fail" and result.fix:
            result = offer_fix(check, result, config)
        results.append(result)
    report.summary(results, config)
    report.saved(report.save(doctor_config.report_dir()))
    if "--no-pause" not in argv:
        report.pause()
    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - last resort: the doctor itself broke
        traceback.print_exc()
        print("\nSorry, I broke. Please send a photo of this screen to whoever helps you.")
        if "--no-pause" not in sys.argv:
            input("Press Enter to close.")
        sys.exit(2)
```

The test lambdas have the `__name__` `<lambda>`. Only `check_boom` relies on `check.__name__`, and it is a named function.

In `Makefile`, add `doctor` to `.PHONY`, then add this target after `test-wc`:

```make
doctor: ## Run vsdata-doctor locally (Windows-only checks are skipped elsewhere)
	uv run python -m vs_doctor
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --extra test pytest tests/unit/doctor tests/smoke/test_doctor.py -v`
Expected: all PASS.

Run: `make test`
Expected: all PASS, with 22 deselected as before.

- [ ] **Step 5: Try it by hand**

Run: `uv run python -m vs_doctor --no-pause`
Expected: on the Mac, the seedling, the Windows checks marked `--`, a plain-English line for each failure, the "What to do" list, and the path of the saved report. There is no traceback.

- [ ] **Step 6: Commit**

```bash
git add src/vs_doctor/__main__.py tests/unit/doctor/test_main.py tests/smoke/test_doctor.py Makefile
git commit -m "Add vsdata-doctor main loop, smoke test and make doctor (#118)"
```

---

### Task 8: Package, release, document and the surface-area list

**Files:**
- Create: `vsdata-doctor.spec`
- Create: `src/vs_doctor/CLAUDE.md`
- Modify: `.github/workflows/build.yml`
- Modify: `CLAUDE.md` (root: add a `vsdata-doctor` section)
- Modify: `README_standalone_install.md` (add a "First-line debugging: vsdata-doctor" section)

**Interfaces:**
- Consumes: `src/vs_doctor/__main__.py` (Task 7).
- Produces: the `dist/vsdata-doctor[.exe]` executable, and the `vsdata-doctor.exe` release asset.

- [ ] **Step 1: Write the PyInstaller spec**

`vsdata-doctor.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for vsdata-doctor, the first-line debugger (see src/vs_doctor/CLAUDE.md).

Build: uv run pyinstaller vsdata-doctor.spec
Output: dist/vsdata-doctor[.exe] (single file)
"""

a = Analysis(
    ["src/vs_doctor/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=["pypyodbc"],  # imported lazily in diagnose.try_odbc
    hookspath=[],
    runtime_hooks=[],
    # Keep the doctor independent of the main app and its heavy dependencies
    excludes=["vs_data_api", "fastapi", "starlette", "uvicorn", "pandas", "numpy", "woocommerce", "tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="vsdata-doctor",
    debug=False,
    strip=False,
    upx=True,
    console=True,
)
```

- [ ] **Step 2: Build it locally and run it**

Run: `uv run --extra dev pyinstaller vsdata-doctor.spec && ./dist/vsdata-doctor --no-pause`
Expected: the build succeeds and the binary prints the same report as `make doctor`, with no traceback. The binary is a macOS one here; the Windows exe comes from CI.

- [ ] **Step 3: Add it to the release workflow**

In `.github/workflows/build.yml`, in `build-windows`, add this step after "Build executable":

```yaml
      - name: Build vsdata-doctor
        run: uv run pyinstaller vsdata-doctor.spec
```

Change the upload step's `path` so it includes both executables:

```yaml
          path: |
            dist/vsdata-server.exe
            dist/vsdata-doctor.exe
```

In the `release` job's "Create GitHub Release" step, change `files`:

```yaml
          files: |
            vsdata-server.exe
            vsdata-doctor.exe
```

`build.py --clean` empties `dist/` first, so it must keep running before the doctor build, as above.

- [ ] **Step 4: Write the surface-area list**

`src/vs_doctor/CLAUDE.md`:

```markdown
# vs_doctor (vsdata-doctor)

A first-line debugger for office staff, shipped as `vsdata-doctor.exe` on each
release. It must always run, so it never imports `vs_data_api` (a test enforces
this). Spec: docs/superpowers/specs/2026-10-15-vsdata-doctor-design.md (#118).

Keep it simple: one job per module (config, windows, diagnose, fixes, checks,
report, __main__). Deeper logic goes in `diagnose.py` or `fixes.py`, not in
`checks.py`.

## Surface area: what the doctor relies on

If you change any of these in the app, update the doctor (and this list) in the
same change.

| What | Defined in the app | Used by |
|---|---|---|
| Config file location | `vs_data_api.config.get_config_dir` (copied; parity test) | `config.py` |
| `[vsdata]` keys `fm_connection_string`, `fm_link_connection_string`, `wc_url`, `wc_key`, `wc_secret` | `config/config.ini.example`, `vs_data_api.config.load_ini_config` | `config.py`, `checks.py` |
| `[server] port` (default 8432) | `vs_data_api.standalone` | `checks.check_server_health` |
| `GET /health`: 200 ok or 503 degraded, body `{"status", "checks": {"filemaker", "filemaker_link", "woocommerce": {"ok", "error"}}}` | `vs_data_api.health.run_checks`, `main.get_health` (contract test) | `diagnose.get_health`, `diagnose.explain_health` |
| http or https on localhost (https when certificates exist) | `vs_data_api.standalone.get_ssl_paths` | `diagnose.get_health` |
| Service name `VSDataAPI` | `deploy/windows/install-service.ps1`, `update.ps1` | `[doctor] service_name` default, `windows.service_state` |
| Log file `C:\Program Files\VSData\logs\stderr.log` | `deploy/windows/install-service.ps1` (NSSM `AppStderr`) | `[doctor] log_file` default |
| WooCommerce REST: `GET /wp-json/wc/v3/products` with basic auth | `vs_data_api.vs_data.wc` | `diagnose.try_website` |
| FileMaker process name starts with `FileMaker`; ODBC error texts | FileMaker Pro and its ODBC driver | `windows.filemaker_running`, `diagnose.explain_odbc_error` |
| Release asset `vsdata-doctor.exe` | `.github/workflows/build.yml`, `vsdata-doctor.spec` | — |
```

In the root `CLAUDE.md`, add this after the `## Tests` section:

```markdown
## vsdata-doctor

`src/vs_doctor` is a standalone debugger for office staff (#118). It relies on
parts of the app: config keys, `/health`, the service name, log path, port and
release assets. They're listed in `src/vs_doctor/CLAUDE.md`. When a change
touches any of them, update the doctor and that list in the same change.
```

- [ ] **Step 5: Document it for installers**

In `README_standalone_install.md`, add this section before "## Configuration Reference":

```markdown
## First-line debugging: vsdata-doctor

`vsdata-doctor.exe` is attached to each release next to `vsdata-server.exe`.
Copy it to `C:\Program Files\VSData\` and put a shortcut on the desktop. When
something stops working, staff double-click it. It checks FileMaker, the data
server and the website, explains any problem in plain English, offers to fix a
few safe ones, and saves a report to `%LOCALAPPDATA%\VSData\`.

It reads the same `config.ini`. Add a `[doctor]` section (see
`config/config.ini.example`): `fm_files` (the FileMaker files, one per line) is
required, while `service_name`, `log_file`, `contact` and `docs_url` are
optional. To start the service it needs to be run as administrator
(right-click, *Run as administrator*).
```

- [ ] **Step 6: Run the whole suite**

Run: `make test`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add vsdata-doctor.spec .github/workflows/build.yml src/vs_doctor/CLAUDE.md CLAUDE.md README_standalone_install.md
git commit -m "Build and release vsdata-doctor, document it and its surface area (#118)"
```

- [ ] **Step 8: Check it by hand on the Windows VM (`../windows10-vm`)**

These steps need the VM and can't be done in CI. Record the results in the PR.

1. Build in the VM, with `uv run pyinstaller vsdata-doctor.spec`, or download the exe from a workflow run.
2. Add a `[doctor]` section to `%APPDATA%\VSData\config.ini` that points at the VM's FileMaker files.
3. Run the exe once with everything working. Expect all `OK` and a cheerful closing line.
4. Run it again under each of these conditions, one at a time, and note the message each gives:
   - FileMaker closed;
   - ODBC sharing off for `wc_link`;
   - the service stopped, both as a normal user and as an administrator;
   - the network adapter disabled;
   - a wrong FileMaker password in `config.ini`.
5. If any ODBC error wording falls through to "Something unexpected", add it to `diagnose.explain_odbc_error` with a test, and commit.
```

---

## Self-review notes

- **Spec coverage:**
  - Each of the seven checks is in Task 5, and the fixes are in Task 4.
  - The admin advice is in `check_server_running`, in Task 5.
  - The report file, `--no-pause`, the contact line and `docs_url` are in Task 6 and Task 7.
  - The ASCII-only art is in Task 6.
  - Isolation and parity are in Task 7 and Task 1.
  - The `/health` contract is in Task 3.
  - Release packaging and `make doctor` are in Task 8 and Task 7.
  - The surface-area `CLAUDE.md` is in Task 8.
  - The service-or-Task-Scheduler question remains open, as the spec says.
- **Deliberate details beyond the spec:**
  - `Result.status` is a string rather than a bool, because the report needs warn and skip.
  - `/health` is tried over http and then https.
  - The exit code is 0, 1 or 2.

  All three were folded back into the spec.
