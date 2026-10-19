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


def test_hide_and_show_console_do_nothing_off_windows(monkeypatch):
    monkeypatch.setattr(windows, "is_windows", lambda: False)
    assert windows.hide_console() is None
    assert windows.show_console() is None
