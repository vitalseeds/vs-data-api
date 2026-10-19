"""vsdata-doctor: run the checks, offer fixes, save the report and wait for Enter."""

import configparser
import sys
import traceback

from vs_doctor import checks, gui, report, runner, windows
from vs_doctor import config as doctor_config


def offer_fix(check, result, config):
    if not report.ask_fix():
        return result
    report.fix_outcome(runner.run_fix(result, config))
    result = runner.run_check(check, config)
    report.check_line(result)
    return result


def load_config():
    try:
        return doctor_config.read_config()
    except configparser.Error:
        return doctor_config.defaults()  # check_config reports the mistake


def run_console(config, argv) -> int:
    report.header()
    results = []
    for check in checks.CHECKS:
        result = runner.run_check(check, config)
        report.check_line(result)
        if result.status == "fail" and result.fix:
            result = offer_fix(check, result, config)
        results.append(result)
    report.summary(results, config)
    report.saved(report.save(doctor_config.report_dir()))
    if "--no-pause" not in argv:
        report.pause()
    return runner.exit_code(results)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        return gui.selftest()
    config = load_config()
    if "--console" not in argv:
        windows.hide_console()
        report.mute()
        try:
            return runner.exit_code(gui.run(config))
        except Exception:  # noqa: BLE001 - any window trouble: do it all again in the console
            windows.show_console()
            report.unmute()
            report.reset()
    return run_console(config, argv)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - last resort: the doctor itself broke
        traceback.print_exc()
        print("\nSorry, I broke. Please send a photo of this screen to whoever helps you.")
        if "--no-pause" not in sys.argv:
            input("Press Enter to close.")
        sys.exit(2)
