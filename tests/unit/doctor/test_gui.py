import pytest

from vs_doctor import checks, gui


def named(name, check):
    check.__name__ = name
    return check


@pytest.fixture
def events():
    return []


def test_check_all_posts_each_check_in_order(monkeypatch, events):
    monkeypatch.setattr(checks, "CHECKS", [named("check_a", lambda cfg: checks.ok("A")), named("check_b", lambda cfg: checks.ok("B"))])
    results = gui.check_all({}, events.append)
    assert [e[:2] for e in events] == [("checking", 0), ("result", 0), ("checking", 1), ("result", 1)]
    assert [r.message for r in results] == ["A", "B"]


def test_a_crashing_check_becomes_a_failed_row_and_the_rest_still_run(monkeypatch, events):
    def check_boom(cfg):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(checks, "CHECKS", [check_boom, lambda cfg: checks.ok("Still here.")])
    results = gui.check_all({}, events.append)
    assert results[0].status == "fail" and "kaboom" in results[0].message
    assert results[1].message == "Still here."


def test_fix_one_reruns_only_that_check(monkeypatch, events):
    calls = {"a": 0, "b": 0}
    state = {"fixed": False}

    def check_a(cfg):
        calls["a"] += 1
        return checks.ok("A fine.") if state["fixed"] else checks.fail("A broken.", fix=fix)

    def check_b(cfg):
        calls["b"] += 1
        return checks.ok("B")

    def fix(cfg):
        state["fixed"] = True
        return True

    monkeypatch.setattr(checks, "CHECKS", [check_a, check_b])
    results = gui.check_all({}, events.append)
    events.clear()
    new = gui.fix_one(0, check_a, results[0], {}, events.append)
    assert new.message == "A fine."
    assert calls == {"a": 2, "b": 1}
    assert [e[0] for e in events] == ["fixing", "fixed", "result"]


def test_fix_one_reports_a_failed_fix(events):
    broken = checks.fail("Broken.", fix=lambda cfg: False)
    new = gui.fix_one(0, lambda cfg: broken, broken, {}, events.append)
    assert ("fixed", 0, False) in events
    assert new is broken


def test_window_smoke():
    pytest.importorskip("sv_ttk")
    tkinter = pytest.importorskip("tkinter")
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError:
        pytest.skip("no display available")
    assert gui.selftest() == 0
