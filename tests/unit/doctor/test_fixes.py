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
