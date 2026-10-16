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


# --- developer settings (.env) ---


def write_env(tmp_path, text):
    return write(tmp_path / ".env", text)


def test_parse_env_file(tmp_path):
    path = write_env(
        tmp_path,
        '# comment\nexport VSDATA_WC_URL="https://shop"\nVSDATA_WC_KEY=ck # note\nEMPTY=\nVSDATA_PWD="a=b"\njunk\n',
    )
    assert config.parse_env_file(path) == {
        "VSDATA_WC_URL": "https://shop",
        "VSDATA_WC_KEY": "ck",
        "EMPTY": "",
        "VSDATA_PWD": "a=b",
    }


def test_read_config_falls_back_to_the_env_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "no-ini-here")
    for name in ("VSDATA_WC_URL", "VSDATA_PORT"):
        monkeypatch.delenv(name, raising=False)
    path = write_env(
        tmp_path,
        "VSDATA_WC_URL=https://dev\nVSDATA_WC_VERIFY_SSL=false\nVSDATA_PORT=8080\nVSDATA_DOCTOR_SERVICE_NAME=vs_data_api\n",
    )
    monkeypatch.setenv("VSDATA_ENV_FILE", str(path))
    cfg = config.read_config()
    assert config.env_file_used(cfg) == path
    assert cfg["vsdata"]["wc_url"] == "https://dev"
    assert cfg["vsdata"]["wc_verify_ssl"] == "false"
    assert cfg["server"]["port"] == "8080"
    assert cfg["doctor"]["service_name"] == "vs_data_api"
    assert "fm_files in [doctor]" not in config.missing_settings(cfg)


def test_real_environment_beats_the_env_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path / "no-ini-here")
    path = write_env(tmp_path, "VSDATA_WC_URL=https://file\n")
    monkeypatch.setenv("VSDATA_ENV_FILE", str(path))
    monkeypatch.setenv("VSDATA_WC_URL", "https://env")
    assert config.read_config()["vsdata"]["wc_url"] == "https://env"


def test_config_ini_wins_over_the_env_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path)
    write(tmp_path / "config.ini", "[vsdata]\nwc_url = https://ini\n")
    monkeypatch.setenv("VSDATA_ENV_FILE", str(write_env(tmp_path, "VSDATA_WC_URL=https://dev\n")))
    cfg = config.read_config()
    assert config.env_file_used(cfg) is None
    assert cfg["vsdata"]["wc_url"] == "https://ini"
