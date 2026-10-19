"""Run a check or a fix without letting a crash escape. Shared by the console and the window."""

from vs_doctor import checks


def run_check(check, config):
    try:
        return check(config)
    except Exception as error:  # noqa: BLE001 - the doctor must keep going
        return checks.fail(f"I tripped over my own feet checking {check.__name__}: {error}")


def run_fix(result, config) -> bool:
    try:
        return bool(result.fix(config))
    except Exception:  # noqa: BLE001 - a failed fix is reported, not raised
        return False


def exit_code(results) -> int:
    return 1 if any(result.status == "fail" for result in results) else 0
