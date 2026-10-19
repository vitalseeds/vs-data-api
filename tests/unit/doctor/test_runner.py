from vs_doctor import checks, runner


def test_run_check_turns_a_crash_into_a_failure():
    def check_boom(cfg):
        raise RuntimeError("kaboom")

    result = runner.run_check(check_boom, {})
    assert result.status == "fail"
    assert "I tripped over my own feet checking check_boom: kaboom" in result.message


def test_run_fix_returns_false_when_the_fix_raises():
    def fix(cfg):
        raise RuntimeError("nope")

    assert runner.run_fix(checks.fail("Broken.", fix=fix), {}) is False


def test_run_fix_returns_the_fixes_result():
    assert runner.run_fix(checks.fail("Broken.", fix=lambda cfg: True), {}) is True
    assert runner.run_fix(checks.fail("Broken.", fix=lambda cfg: False), {}) is False


def test_exit_code_is_one_only_when_something_failed():
    assert runner.exit_code([checks.ok("a"), checks.skip("b"), checks.Result("warn", "c")]) == 0
    assert runner.exit_code([checks.ok("a"), checks.fail("b")]) == 1
