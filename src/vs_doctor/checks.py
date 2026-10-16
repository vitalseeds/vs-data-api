"""What the doctor checks. Each check takes the config and returns a Result; CHECKS lists them in order."""

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from vs_doctor import config as doctor_config
from vs_doctor import diagnose, fixes, windows

NOT_WINDOWS = "Only checked on Windows."


@dataclass
class Result:
    status: str  # "ok", "warn", "fail" or "skip"
    message: str
    advice: str = ""
    detail: str = ""  # extra lines shown dimmed, e.g. log errors
    fix: Optional[Callable] = None  # from fixes.py: fix(config) -> bool


def ok(message):
    return Result("ok", message)


def skip(message):
    return Result("skip", message)


def fail(message, advice="", fix=None):
    return Result("fail", message, advice, fix=fix)


def check_config(config):
    path = doctor_config.config_path()
    if not path.exists():
        return fail(f"I can't find the settings file at {path}.", advice="It needs setting up before anything else will work.")
    try:
        doctor_config.read_config(path)
    except configparser.Error as error:
        return fail("The settings file has a mistake in it.", advice=str(error).splitlines()[0])
    missing = doctor_config.missing_settings(config)
    if missing:
        return fail(f"The settings file is missing: {', '.join(missing)}.")
    return ok("The settings file is in place.")


def check_filemaker_open(config):
    if not windows.is_windows():
        return skip(NOT_WINDOWS)
    if windows.filemaker_running():
        return ok("FileMaker is open.")
    fix = fixes.open_filemaker if doctor_config.fm_files(config) else None
    return fail("FileMaker isn't open.", advice="Open vs_db and wc_link in FileMaker, then run me again.", fix=fix)


def check_filemaker_odbc(config):
    for key in ("fm_connection_string", "fm_link_connection_string"):
        connection_string = config["vsdata"].get(key, "")
        error = diagnose.try_odbc(connection_string)
        if error:
            database = diagnose.database_name(connection_string)
            return Result("fail", **diagnose.explain_odbc_error(error, database))
    return ok("FileMaker answers on ODBC (both databases).")


def check_server_running(config):
    if not windows.is_windows():
        return skip(NOT_WINDOWS)
    name = config["doctor"]["service_name"]
    state = windows.service_state(name)
    if state == "RUNNING":
        return ok("The data server is running.")
    if state is None:
        return fail(f"I can't find the data server ({name}) on this computer.", advice="It may not be installed here.")
    if not windows.is_admin():
        script = fixes.write_start_script(config)
        return fail(
            "The data server is switched off.",
            advice=f"I can start it, but Windows will ask you to allow it. Or double-click this file yourself: {script}",
            fix=fixes.start_service_as_admin,
        )
    return fail("The data server is switched off.", advice="Start it.", fix=fixes.start_service)


def check_server_health(config):
    report = diagnose.get_health(config["server"]["port"])
    if report is None:
        return fail("The data server isn't answering.", advice="If it was only just started, wait a minute and run me again.")
    problems = diagnose.explain_health(report)
    if not problems:
        return ok("The data server says everything is fine.")
    return fail(" ".join(problems), advice="If FileMaker passed above, the data server's own settings are wrong.")


def check_website(config):
    url = config["vsdata"].get("wc_url", "")
    if not url:
        return fail("The website address is missing from the settings file.")
    verify_ssl = config["vsdata"].get("wc_verify_ssl", "true").strip().lower() not in ("0", "false", "no", "off")
    error = diagnose.try_website(
        url, config["vsdata"].get("wc_key", ""), config["vsdata"].get("wc_secret", ""), verify_ssl
    )
    if error is None:
        return ok("The website answers.")
    return Result("fail", **diagnose.explain_http_error(error, url))


def check_server_log(config):
    path = Path(config["doctor"]["log_file"])
    if not path.exists():
        return skip(f"No server log at {path}.")
    errors = diagnose.recent_log_errors(path)
    if not errors:
        return ok("No recent errors in the server log.")
    return Result("warn", "The server log has recent errors.", advice="These are for whoever helps you.", detail="\n".join(errors))


CHECKS = [
    check_config,
    check_filemaker_open,
    check_filemaker_odbc,
    check_server_running,
    check_server_health,
    check_website,
    check_server_log,
]
