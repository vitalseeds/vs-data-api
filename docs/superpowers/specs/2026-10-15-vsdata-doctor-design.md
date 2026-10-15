# vsdata-doctor: a first-line debugger for non-technical staff, spec for #118

**Date:** 2026-10-15
**Status:** draft, for review
**Issue:** #118 (project 5)

## Goal

When something stops working and no developer is around, someone in the
office double-clicks **vsdata-doctor** on the production Windows PC. It runs a
short list of checks and says in plain English what is wrong and what to do,
for example "FileMaker isn't open. Open vs_db and wc_link, then try again." For
a few safe problems it offers to fix them itself.

It must always run, including when the API server is broken, so it is a
**separate executable** that never imports `vs_data_api`. It lives in this repo
so its assumptions (service name, port, config keys, `/health` shape) change in
the same commits as the app, and it ships as its own asset on each tagged
release.

**Guiding rule: keep it simple and readable.** Split the code into a few
modules, each with an obvious name and one responsibility, so a reader can tell
from the file list where things are. Each module is plain functions, with no
classes beyond one small dataclass and no registry or plugin layer. When a
feature would need a new abstraction, leave the feature out.

## Decisions

| Question | Decision |
|---|---|
| Who runs it | Staff, by double-clicking `vsdata-doctor.exe` (desktop shortcut). The window stays open until Enter is pressed. |
| Fixes | Mostly diagnosis. For a few safe fixes it asks `Shall I try? [y/N]` first, defaulting to no. |
| Depth | It checks ODBC itself, so it still works when the server is down. |
| UI | `rich`, with colour, a little ASCII art and a joke. No Textual. |
| Config | The same `config.ini` as the server, plus a `[doctor]` section. |

## Structure

```
src/vs_doctor/
  __main__.py   entry point: runs the checks, offers fixes, waits for Enter
  config.py     finds and reads config.ini, with defaults for [doctor]
  checks.py     what is checked: a short function per check, and the CHECKS list
  diagnose.py   deeper diagnosis: turns raw errors into plain English
  fixes.py      the fixes: opening FileMaker, starting the service
  windows.py    thin wrappers for OS calls: tasklist, sc, is_admin, startfile
  report.py     everything the user sees: art, jokes, coloured lines, summary,
                saving the report file
```

The responsibilities are as follows:

- **`checks.py`** reads as a list of what the doctor tests. Each check is a few
  lines that return a `Result` (a small dataclass: `ok`, `message`, `advice`,
  `fix`). Anything more involved is one call into `diagnose.py`, `fixes.py` or
  `windows.py`. `CHECKS` at the bottom lists the check functions in order.
- **`diagnose.py`** and **`fixes.py`** are where sophistication is allowed to
  grow: matching ODBC error strings, interpreting `/health`, scanning the log,
  and any extra steps a fix needs, such as waiting for the service to come up.
  None of this leaks into `checks.py`.
- **`windows.py`** is the only module that calls the OS. That keeps the
  Windows-specific parts in one place and gives tests one thing to monkeypatch.
- **`report.py`** is the only module that prints. Checks and fixes return data
  and `report.py` decides how it looks, so changing the art or the jokes never
  touches the logic.
- **`config.py`**: `read_config()` returns a plain `ConfigParser` with the
  `[doctor]` defaults filled in. `get_config_dir()` is copied from
  `vs_data_api.config`, so the doctor needs nothing from the main app.
- **`__main__.py`** is the main loop of about 30 lines. For each check it calls
  the check, passes the result to `report`, and if there is a fix it asks, runs
  the fix and re-runs the check. At the end it saves the report and waits for
  Enter.

For example, in `checks.py`:

```python
def check_filemaker_odbc(config):
    error = diagnose.try_odbc(config["vsdata"]["fm_connection_string"])
    if error is None:
        return Result(ok=True, message="FileMaker answers on ODBC.")
    return Result(ok=False, **diagnose.explain_odbc_error(error))


def check_server_running(config):
    if windows.service_is_running(config["doctor"]["service_name"]):
        return Result(ok=True, message="The data server is running.")
    return Result(ok=False, message="The data server is switched off.",
                  advice="Start it.", fix=fixes.start_service)
```

Imports are limited to the stdlib, `rich` and `pypyodbc`. HTTP uses
`urllib.request` with short timeouts.

The main loop wraps each check and each fix in a `try/except`. When one
crashes, it prints "I tripped over my own feet checking X" and the run continues. That
is the only error handling it needs.

## Config

The doctor reads the existing sections. `[vsdata]` provides the connection
strings and the WooCommerce URL, key and secret, and `[server]` provides the
port. A new `[doctor]` section holds the rest.

```ini
[doctor]
; FileMaker files that must be open, one per line (required)
fm_files =
    C:\path\to\vs_db.fmp12
    C:\path\to\wc_link.fmp12
service_name = VSDataAPI
log_file = C:\Program Files\VSData\logs\stderr.log
; Who to ask for help: shown at the end of the report when something is still
; failing, and after advice to get help
contact = Call or WhatsApp Tom
; Vital Seeds documentation site, suggested while waiting to hear back
docs_url = https://docs.example.com
```

- `fm_files` is required, with no default: the paths are machine-specific, so
  they are set in each PC's `config.ini`. If it is missing, `check_config` says
  so, and the FileMaker checks report that they can't run without it.
- `service_name` and `log_file` default to the values shown.
- `contact` defaults to "Call or WhatsApp Tom."
- `docs_url` is optional and has no default, because the site isn't live yet.
  When it is set, the line after the contact reads "While you wait, the Vital
  Seeds docs may help: <docs_url>". When it is unset, that line is left out.

`config/config.ini.example` and `README_standalone_install.md` gain this
section.

## Checks

Each check is one function in `checks.py`, run in this order. When a check
fails, the doctor still runs the rest. The messages say which one to fix first, because the list
is ordered so that root causes come first.

| # | Function | Failure message (example) | Offered fix |
|---|---|---|---|
| 1 | `check_config` | "I can't find the settings file at …" | — |
| 2 | `check_filemaker_open` (`tasklist` shows FileMaker Pro) | "FileMaker isn't open." | Open the `fm_files`, which starts FileMaker with them |
| 3 | `check_filemaker_odbc` (connects to the main and link databases) | "FileMaker is open but sharing (ODBC) is off for vs_db." or "FileMaker rejected the password." | — |
| 4 | `check_server_running` (`sc query`) | "The data server is switched off." | Start the service |
| 5 | `check_server_health` (`GET /health`) | "The data server is running but not answering." or "The server can't reach FileMaker, but I can. <contact>" | — |
| 6 | `check_website` (`GET {wc_url}/wp-json/wc/v3`) | "The website isn't answering. Is the internet working?" | — |
| 7 | `check_server_log` (last error lines in `log_file`) | Warning that shows the last error lines | — |

Comparing checks 3 and 5 matters most. If the doctor can reach FileMaker but
the server can't, the problem is the server's config. If neither can,
FileMaker is the problem.

The error matching lives in `diagnose.py`, for example `explain_odbc_error`,
`explain_health` and `recent_log_errors`. Each starts as a simple `if` chain
over a handful of known error strings, and an unrecognised error is shown as
"Something unexpected: <error>".

### Fixes

Each fix is one function in `fixes.py`, and it returns `True` or `False`
depending on whether the fix worked.

- These run only after `Shall I try? [y/N]`.
- Starting the service needs admin rights. If the doctor isn't running as
  admin, it says "Close me, right-click vsdata-doctor and choose *Run as
  administrator*". It does not relaunch itself elevated.
- After a fix, the main loop re-runs that one check and reports whether the fix
  worked.
- Any extra steps a fix needs, such as waiting for the service to come up,
  stay inside `fixes.py`.

## Output (`report.py`)

- A seedling in ASCII art, then one coloured line per check: `OK`, `!!` or
  `--`, followed by the message.
- A "What to do" list with the advice for the failures only, then the contact
  line and, if set, the docs link.
- A cheerful closing line when everything is ok, a wilted seedling otherwise.
  The jokes stay in the art and the closing line. Advice is always plain.
- Only ASCII characters, so the old Windows console renders it correctly.
- The same text is saved to `%LOCALAPPDATA%\VSData\doctor-<timestamp>.txt`,
  using `rich`'s `Console(record=True)` and `save_text`. The doctor prints the
  path so staff can send the file on.
- Last comes "Press Enter to close". There is a `--no-pause` flag for tests.

## Packaging and release

- Add a `vsdata-doctor.spec` file (single file, console) with entry
  `src/vs_doctor/__main__.py`.
- In `.github/workflows/build.yml`, add one step that runs
  `pyinstaller vsdata-doctor.spec` and adds `vsdata-doctor.exe` to the release
  files.
- `make doctor` runs `uv run python -m vs_doctor` locally.
- The doctor is installed by copying the exe next to the server and adding a
  desktop shortcut, by hand. Updating it automatically through `update.ps1` is
  left for later.

## Testing

All of these are in the default suite: no FileMaker, no WooCommerce, and they
run on macOS. They live in `tests/unit/vs_doctor/`, with one test
file per module.

- `diagnose.py`: the error matching is pure functions, tested directly with
  sample error strings.
- `fixes.py` and `checks.py`: tested with `windows.py` monkeypatched.
- Each check: a passing case and its main failure messages.
- `/health` contract: real `health.run_checks` output, built with fakes, is
  passed to `diagnose.explain_health`, so a change to `/health` breaks this
  test.
- Isolation: importing `vs_doctor` in a subprocess leaves `vs_data_api` out of
  `sys.modules`.
- `get_config_dir()` returns the same path as `vs_data_api.config`'s.
- Smoke: `python -m vs_doctor --no-pause` with a temp config dir exits 0 and
  writes a report.

Manual check on the Windows VM: run the built exe with FileMaker closed, the
service stopped, and the network off, one at a time.

## Out of scope

- Editing config, touching FileMaker data, or relaunching itself elevated.
- Auto-updating the doctor (`update.ps1`).
- macOS or Linux support beyond the tests running there.
- Sending the report anywhere.
- Linking individual checks to specific pages on the docs site. This could be
  added later, once the site exists, as an optional `docs` path on `Result`.

## Open questions

1. Does production run the server as the `VSDataAPI` service or from Task
   Scheduler (`startup/`)? This spec assumes the service. The answer affects
   only `check_server_running`, `fixes.start_service` and the default
   `service_name`. (Postponed.)
