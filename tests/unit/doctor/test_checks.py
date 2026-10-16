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


def test_check_server_running(cfg, on_windows, monkeypatch, tmp_path):
    monkeypatch.setattr(windows, "service_state", lambda name: "RUNNING")
    assert checks.check_server_running(cfg).status == "ok"
    monkeypatch.setattr(windows, "service_state", lambda name: None)
    assert "can't find the data server" in checks.check_server_running(cfg).message
    monkeypatch.setattr(windows, "service_state", lambda name: "STOPPED")
    monkeypatch.setattr(windows, "is_admin", lambda: False)
    monkeypatch.setattr(config, "report_dir", lambda: tmp_path)
    result = checks.check_server_running(cfg)
    assert result.fix is fixes.start_service_as_admin
    assert str(fixes.start_script_path()) in result.advice  # a file staff can double-click
    assert fixes.start_script_path().exists()
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
