"""vsdata-doctor: run the checks, offer fixes, save the report and wait for Enter."""

import configparser
import sys
import traceback

from vs_doctor import checks, report
from vs_doctor import config as doctor_config


def run_check(check, config):
    try:
        return check(config)
    except Exception as error:  # noqa: BLE001 - the doctor must keep going
        return checks.fail(f"I tripped over my own feet checking {check.__name__}: {error}")


def offer_fix(check, result, config):
    if not report.ask_fix():
        return result
    try:
        worked = result.fix(config)
    except Exception:  # noqa: BLE001 - a failed fix is reported, not raised
        worked = False
    report.fix_outcome(worked)
    result = run_check(check, config)
    report.check_line(result)
    return result


def load_config():
    try:
        return doctor_config.read_config()
    except configparser.Error:
        return doctor_config.defaults()  # check_config reports the mistake


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    config = load_config()
    report.header()
    results = []
    for check in checks.CHECKS:
        result = run_check(check, config)
        report.check_line(result)
        if result.status == "fail" and result.fix:
            result = offer_fix(check, result, config)
        results.append(result)
    report.summary(results, config)
    report.saved(report.save(doctor_config.report_dir()))
    if "--no-pause" not in argv:
        report.pause()
    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - last resort: the doctor itself broke
        traceback.print_exc()
        print("\nSorry, I broke. Please send a photo of this screen to whoever helps you.")
        if "--no-pause" not in sys.argv:
            input("Press Enter to close.")
        sys.exit(2)
