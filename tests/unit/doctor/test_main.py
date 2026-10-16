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
