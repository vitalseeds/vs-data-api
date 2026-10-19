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


def test_muted_console_still_saves_what_was_printed(tmp_path):
    report.mute()
    report.check_line(checks.ok("Fine."))
    path = report.save(tmp_path)
    assert "Fine." in path.read_text()


def test_mute_works_when_stdout_is_none(monkeypatch):
    monkeypatch.setattr("sys.stdout", None)
    report.mute()
    report.check_line(checks.ok("Fine."))


def test_reset_forgets_earlier_output(tmp_path):
    report.mute()
    report.check_line(checks.ok("First."))
    report.reset()
    report.check_line(checks.ok("Second."))
    path = report.save(tmp_path)
    assert "First." not in path.read_text()
    assert "Second." in path.read_text()
