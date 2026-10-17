# vsdata-doctor friendly UI (#131)

Status: draft for approval. Follows the doctor design in `2026-10-15-vsdata-doctor-design.md` (#118).

## Intent

Office staff run `vsdata-doctor.exe` as a first-line debugger. The rich console output is robust but a command-line window alienates them. Give the doctor a friendly, native-looking window, without making a debugging tool that can break itself.

## Goals

- Double-click opens a normal Windows-looking window that runs the checks, shows pass/fail per check, offers fixes with buttons, and shows where the report was saved.
- If the window cannot start (Tk missing, theme fails to load, any exception during start-up), the doctor falls back to the existing rich console flow automatically, with no duplicated check logic.
- Checks and fixes run off the UI thread so the WooCommerce/FileMaker timeouts never freeze the window.

## Non-goals

- No remote access. The doctor is not used over SSH; the developer uses the site health commands and endpoints directly.
- No web server, Kivy, or Textual front end (judged more fragile for a debugging tool).
- Sending the report to the developer is a later extra (a "Copy report" button first), not part of this work.

## Anti-goals

- The GUI must never be a reason the doctor can't report. A GUI bug that hides results is worse than the console.
- The doctor must still never import `vs_data_api` (existing test).

## Decisions

- **Toolkit: Tkinter** (stdlib, so no big dependency) with **[sv-ttk](https://pypi.org/project/sv-ttk/)** for a Windows 11 look. This is my pick, not a confirmed match for the Python Bytes package the user remembered.
- **Console stays as the fallback**, and is also reachable with a flag (e.g. `--console`), so staff can be told "run it with --console" if the window misbehaves.
- **Architecture:** `checks.py`, `diagnose.py`, `fixes.py` stay unchanged and know nothing about the UI. A new module `gui.py` drives the same `checks.CHECKS` and `run_check`/fix functions that `__main__.py` uses. `report.py` stays the console renderer. Where `__main__.py` mixes the run loop with console output, the builder should pull the loop out so both front ends share it (builder's call on the shape).
- `gui.py` must be documented in `src/vs_doctor/CLAUDE.md`.

## Spike result (throwaway, not kept)

A small sv-ttk window with a worker thread feeding a queue was built with PyInstaller `--onefile --noconsole` on macOS. The frozen binary started, and the active theme was `sun-valley-light`; the `sv_ttk` Tcl and sprite files were bundled automatically. **Not yet verified on Windows**, which is the real target; that is the first task of the build.

## Constraints and things to change

- `vsdata-doctor.spec` currently lists `tkinter` in `excludes` and builds with `console=True`. Both must change. A windowed build has no console, so the console fallback needs one (builder's call: `console=True` with the console hidden when the GUI opens, or a second console entry point/exe).
- Add `sv-ttk` to the doctor's build dependencies only. Check `build.yml` installs it.
- Tk callbacks and widgets are touched only from the main thread; workers post results through a queue polled with `after`.
- Keep the last-resort handler: if the GUI crashes, show the error in a message box and fall back to the console flow, saving the report either way.

## Left to the builder

- Layout, wording and colours; whether to follow the system light/dark setting.
- Whether the fix prompt is a button on each failed row or a dialog.
- How the console is kept available in the windowed build.
- Tests: logic stays unit-tested through the existing modules; the GUI gets a smoke test (construct the window, run checks with fakes, then destroy it) that is skipped if no display is available.

## Open questions for the user

- Does sv-ttk match the package you remember?
- Windows 10 vs 11 on the office machines (sv-ttk mimics Windows 11 either way).
