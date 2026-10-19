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
        [sys.executable, "-m", "vs_doctor", "--console", "--no-pause"], capture_output=True, text=True, timeout=180, env=os.environ
    )

    assert "Traceback" not in run.stdout + run.stderr
    assert run.returncode == 1  # ODBC, server and website all fail here
    assert "What to do" in run.stdout
    reports = list((tmp_path / "local" / "VSData").glob("doctor-*.txt"))
    assert len(reports) == 1
    assert "The settings file is in place." in reports[0].read_text()
