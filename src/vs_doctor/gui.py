"""The doctor's window. The workers run checks and fixes and report through a `post` callback;
the Tk half (below) is the only code that touches widgets, and imports tkinter lazily."""

from vs_doctor import checks, runner


def check_all(config, post):
    results = []
    for index, check in enumerate(checks.CHECKS):
        post(("checking", index, check.__name__))
        result = runner.run_check(check, config)
        post(("result", index, result))
        results.append(result)
    return results


def fix_one(index, check, result, config, post):
    post(("fixing", index))
    post(("fixed", index, runner.run_fix(result, config)))
    new_result = runner.run_check(check, config)
    post(("result", index, new_result))
    return new_result
