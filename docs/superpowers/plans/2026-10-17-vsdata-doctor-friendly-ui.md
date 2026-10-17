# vsdata-doctor friendly UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vsdata-doctor.exe` opens a native-looking Tkinter window (sv-ttk theme) that runs the checks and offers fixes with buttons, falling back to the existing rich console flow if the window can't start or breaks.

**Architecture:** The check, diagnose and fix modules stay untouched. A new `runner.py` holds the run/fix helpers both front ends share (moved out of `__main__.py`). A new `gui.py` drives them from a worker thread and talks to Tk only through a queue. The GUI also writes each line to the existing recording rich console (muted), so the saved report has the same name and format either way. `__main__.main` tries the GUI unless `--console` is given, and on any GUI failure shows the hidden console again and reruns everything in the console.

**Tech Stack:** Python stdlib `tkinter`, `sv-ttk`, `rich` (existing), PyInstaller (existing), pytest.

**Spec:** `docs/superpowers/specs/2026-10-17-vsdata-doctor-friendly-ui-design.md` (approved). Read `src/vs_doctor/CLAUDE.md` first.

## Global Constraints

- The doctor never imports `vs_data_api` (existing test enforces this).
- Tkinter widgets are touched only from the main thread; workers post to a `queue.Queue` that the main thread polls with `after`.
- Shipped as a single `vsdata-doctor.exe`; asset name, `build.yml` release file list unchanged.
- Theme is `sv-ttk`; if it fails to load or the window fails at start, fall back to the console. (Decision if sv-ttk fails when frozen on Windows: drop sv-ttk and use the built-in `vista` theme, not the GUI.)
- GUI shows all checks first, then a "Fix" button on each failed row that has a `fix`. A running fix shows a busy state, disables its button, and the window can't be closed until it finishes. After a fix, only that check reruns.
- Exit codes unchanged: 0 all fine, 1 any failure, 2 the doctor itself broke. `--no-pause` affects only the console. `--console` is new.
- `make test` must pass on a clean checkout: GUI tests skip if `sv_ttk` is missing or no display is available.
- Plain English tone in user-facing text, matching `report.py`.

## Review Focus

- A check or fix that raises inside the worker must show on its row and not kill the window (test in Task 3).
- sv-ttk missing or `tkinter` import failing must land in the console flow, not a traceback (Task 4).
- Window failing after some checks ran must rerun everything in the console and still save one report (Task 4).
- The saved report must contain the GUI's results even though the console is muted (Task 2).
- Running with no console attached (`sys.stdout is None` in the windowed build) must not crash rich (Task 2).

## File Structure

- Create `src/vs_doctor/runner.py`: shared `run_check`, `run_fix`, `exit_code`.
- Create `src/vs_doctor/gui.py`: worker logic (`check_all`, `fix_one`) and the Tk window (`run`, `selftest`).
- Modify `src/vs_doctor/__main__.py`: use runner, add `--console` and the GUI-or-fallback switch.
- Modify `src/vs_doctor/report.py`: `mute()`, `reset()`.
- Modify `src/vs_doctor/windows.py`: `hide_console()`, `show_console()`.
- Modify `vsdata-doctor.spec`, `pyproject.toml` (dev extra), `.github/workflows/build.yml`, `src/vs_doctor/CLAUDE.md`.
- Tests: `tests/unit/doctor/test_runner.py`, `test_gui.py`, plus edits to `test_report.py`, `test_windows.py`, `test_main.py`, `tests/smoke/test_doctor.py`.

---

### Task 1: Shared runner

**Files:**
- Create: `src/vs_doctor/runner.py`
- Modify: `src/vs_doctor/__main__.py` (remove `run_check`; import from runner)
- Test: `tests/unit/doctor/test_runner.py`

**Interfaces:**
- Produces: `run_check(check, config) -> checks.Result` (catches any exception and returns `checks.fail(f"I tripped over my own feet checking {check.__name__}: {error}")`, the existing wording); `run_fix(result, config) -> bool` (False if the fix raises); `exit_code(results) -> int` (1 if any `status == "fail"`, else 0).

- [ ] **Step 1: Write failing tests** in `test_runner.py`: `test_run_check_turns_a_crash_into_a_failure` (message contains `"I tripped over my own feet checking check_boom: kaboom"`), `test_run_fix_returns_false_when_the_fix_raises`, `test_run_fix_returns_the_fixes_result`, `test_exit_code_is_one_only_when_something_failed` (ok/warn/skip → 0, with a fail → 1).
- [ ] **Step 2: Run** `uv run pytest tests/unit/doctor/test_runner.py -v`; expect ImportError.
- [ ] **Step 3: Implement** `runner.py` per Interfaces; move the body of `__main__.run_check`. In `__main__.py` replace the local `run_check` and the `try/except` in `offer_fix` with `runner.run_check` / `runner.run_fix`, and the final return with `runner.exit_code(results)`.
- [ ] **Step 4: Run** `uv run pytest tests/unit/doctor -v`; expect all pass (existing `test_main` tests must still pass unchanged).
- [ ] **Step 5: Commit** `git commit -m "Move the doctor's run helpers into runner.py (#131)"`

### Task 2: Report support for a muted console

**Files:**
- Modify: `src/vs_doctor/report.py`
- Test: `tests/unit/doctor/test_report.py`

**Interfaces:**
- Produces: `report.mute() -> None` (point the recording console's output at an in-memory buffer so it records but prints nothing and never touches a missing `sys.stdout`); `report.reset() -> None` (discard everything recorded so far).

- [ ] **Step 1: Write failing tests:** `test_muted_console_still_saves_what_was_printed` (call `mute()`, `check_line(checks.ok("Fine."))`, `save(tmp_path)` and assert the file text contains `"Fine."`); `test_mute_works_when_stdout_is_none` (monkeypatch `sys.stdout` to `None`, call `mute()` then `check_line`, no exception); `test_reset_forgets_earlier_output` (print, `reset()`, print other, saved file lacks the first). Use the existing test file's console fixture style.
- [ ] **Step 2: Run** `uv run pytest tests/unit/doctor/test_report.py -v`; expect the new tests to fail.
- [ ] **Step 3: Implement** `mute` and `reset` in `report.py`. For `reset`, `console.export_text(clear=True)` discards the record.
- [ ] **Step 4: Run** the same tests; expect pass.
- [ ] **Step 5: Commit** `git commit -m "Let the doctor report record without printing (#131)"`

### Task 3: GUI worker logic (no Tk)

**Files:**
- Create: `src/vs_doctor/gui.py` (worker half only in this task)
- Test: `tests/unit/doctor/test_gui.py`

**Interfaces:**
- Consumes: `runner.run_check`, `runner.run_fix`, `checks.CHECKS`.
- Produces: `check_all(config, post) -> list[Result]`, where `post(event)` is called with `("checking", index, check_name)` before each check and `("result", index, Result)` after it; returns the results in order. `fix_one(index, check, result, config, post) -> Result` posts `("fixing", index)`, runs `runner.run_fix`, posts `("fixed", index, worked)`, reruns the check via `runner.run_check`, posts `("result", index, new_result)` and returns it.

- [ ] **Step 1: Write failing tests** (monkeypatch `checks.CHECKS` with fakes): `test_check_all_posts_each_check_in_order` (events are `checking 0, result 0, checking 1, result 1`); `test_a_crashing_check_becomes_a_failed_row_and_the_rest_still_run`; `test_fix_one_reruns_only_that_check` (the other check's counter stays at 1); `test_fix_one_reports_a_failed_fix` (`("fixed", 0, False)` is posted and the rerun result is returned).
- [ ] **Step 2: Run** `uv run pytest tests/unit/doctor/test_gui.py -v`; expect ImportError.
- [ ] **Step 3: Implement** the two functions in `gui.py`; keep `import tkinter` out of module top level so the worker half imports without Tk (the window half imports it lazily inside its functions).
- [ ] **Step 4: Run** the tests; expect pass.
- [ ] **Step 5: Commit** `git commit -m "Add the doctor GUI's check and fix workers (#131)"`

### Task 4: The Tk window and the console fallback

**Files:**
- Modify: `src/vs_doctor/gui.py` (window half), `src/vs_doctor/windows.py`, `src/vs_doctor/__main__.py`
- Test: `tests/unit/doctor/test_gui.py`, `test_windows.py`, `test_main.py`, `tests/smoke/test_doctor.py`

**Interfaces:**
- Consumes: Task 1–3 functions; `report.mute/reset/check_line/summary/save/saved`.
- Produces:
  - `windows.hide_console() -> None` and `windows.show_console() -> None` (no-ops when not on Windows or when `GetConsoleWindow()` is 0; otherwise `ShowWindow(hwnd, 0)` / `ShowWindow(hwnd, 5)` through `ctypes`).
  - `gui.GuiUnavailable(Exception)`.
  - `gui.run(config) -> list[Result]`: opens the window titled "Vital Seeds Doctor", applies `sv_ttk.set_theme("light")`, shows a row per check (status mark, message, advice, dimmed detail), runs `check_all` on a worker thread polled through `after(100, ...)`, then shows a "Fix" button on each failed row with a `fix`, then a footer with the contact line, docs URL and a closing quip. It also feeds `report.check_line` and `report.summary` so the saved report matches the console's, then calls `report.saved(report.save(...))` and shows the saved path and a "Close" button. Raises `GuiUnavailable` for any failure to start or any exception inside the window (set `root.report_callback_exception` to record it, then raise after the main loop ends). Returns the final results when the window is closed normally.
  - `gui.selftest() -> int`: creates the window, applies the theme, calls `update()`, destroys it, returns 0, or 2 on any failure. Used by the CI step in Task 5.
  - `__main__.main(argv)`: `--selftest` → `sys.exit`-style return of `gui.selftest()`; `--console` → existing console flow; otherwise `windows.hide_console()`, `report.mute()`, `gui.run(config)` and return `runner.exit_code(results)`. On `Exception` from importing or running the GUI (including a missing `sv_ttk` or `tkinter`): `windows.show_console()`, undo the mute (restore a real console output; a small `report.unmute()` is fine if needed), `report.reset()`, and run the console flow from scratch. The `__main__` last-resort handler stays and still returns 2.

- [ ] **Step 1: Write failing tests:**
  - `test_windows.py`: `test_hide_and_show_console_do_nothing_off_windows` (monkeypatch `is_windows` to False; both return `None`).
  - `test_main.py`: change every existing `doctor.main(["--no-pause"])` to `doctor.main(["--console", "--no-pause"])`; add `test_gui_failure_falls_back_to_the_console` (monkeypatch `gui.run` to raise `RuntimeError`; with one fake ok check the return is 0, `"Fine."` appears once in `report.console.export_text()` and exactly one report file is in `tmp_path`); `test_missing_sv_ttk_falls_back_to_the_console` (monkeypatch `gui.run` to raise `ImportError`; same assertions); `test_gui_is_used_when_available` (monkeypatch `gui.run` to return `[checks.ok("x")]`; return 0 and `gui.run` was called); `test_gui_exit_code_one_when_a_check_failed`; `test_selftest_flag_returns_the_selftest_code`.
  - `test_gui.py`: `test_window_smoke` guarded with `pytest.importorskip("sv_ttk")` and a skip when `tkinter.Tk()` raises `TclError`: call `gui.selftest()` and assert `0`.
  - `tests/smoke/test_doctor.py`: pass `--console` to the subprocess args so it never opens a window.
- [ ] **Step 2: Run** `uv run pytest tests/unit/doctor tests/smoke/test_doctor.py -v`; expect the new tests to fail.
- [ ] **Step 3: Implement** the window, `selftest`, the `windows` functions and the `main` switch per Interfaces. Layout, wording, fonts and colours are the builder's call (`ttk.Frame`, one `ttk.Label` per row; use `Accent.TButton` for Fix). Keep any file write and message text going through `report.py` so there is one report.
- [ ] **Step 4: Run** `uv run pytest tests/unit/doctor tests/smoke/test_doctor.py -v` and `make test`; expect all pass.
- [ ] **Step 5: Manual look** (macOS or Windows with a display): `uv run python -m vs_doctor`. Confirm the window opens, rows fill in, a failing check shows a Fix button, and the report path is shown. Then `uv run python -m vs_doctor --console --no-pause` still prints the console report.
- [ ] **Step 6: Commit** `git commit -m "Add the friendly Tkinter window with console fallback (#131)"`

### Task 5: Build, CI and docs

**Files:**
- Modify: `vsdata-doctor.spec`, `pyproject.toml`, `.github/workflows/build.yml`, `src/vs_doctor/CLAUDE.md`

- [ ] **Step 1:** Add `"sv-ttk"` to the `dev` extra in `pyproject.toml` (the build job runs `uv sync --extra dev`); `uv lock` if the repo keeps a lock file.
- [ ] **Step 2:** In `vsdata-doctor.spec` remove `"tkinter"` from `excludes`, add `hiddenimports` `"sv_ttk"` and `datas` from `PyInstaller.utils.hooks.collect_data_files("sv_ttk")`, and keep `console=True` (the window hides the console at start). Update the docstring/comment to say why.
- [ ] **Step 3:** In `build.yml` add a step after "Build vsdata-doctor": run `dist/vsdata-doctor.exe --selftest` and fail the job on a non-zero exit. Windows runners have a desktop session, so Tk should start; if it can't, note that and keep the step as `continue-on-error: true` rather than dropping it.
- [ ] **Step 4:** Update `src/vs_doctor/CLAUDE.md`: add `runner` and `gui` to the module list, mention `--console` and `--selftest`, and add a surface-area row for the sv-ttk/Tk bundling in the release asset.
- [ ] **Step 5: Build locally** `uv run pyinstaller vsdata-doctor.spec` then `dist/vsdata-doctor --selftest` (macOS/Linux with a display) and expect exit 0.
- [ ] **Step 6: Commit** `git commit -m "Bundle Tk and sv-ttk in the doctor exe and smoke-test it in CI (#131)"`
- [ ] **Step 7: Manual check on an office PC (owner):** download the built `vsdata-doctor.exe` from the workflow artifact, double-click it; confirm the window opens with the Windows 11 look, the console is hidden after a brief flash, a failing check can be fixed from its button, and `vsdata-doctor.exe --console` still works. If the sv-ttk look fails when frozen on Windows, switch the theme call to the built-in `vista` theme and update the spec doc.

---

**Self-review:** every spec section maps to a task: goals (window, fallback, threads) → Tasks 3–4; non-goals need no work; single exe, hidden console → Tasks 4–5; builder calls (fix order, busy state, fallback boundary, exit codes, Windows verification, dependency placement) → Tasks 3–5 and Global Constraints. Names used across tasks (`run_check`, `run_fix`, `exit_code`, `check_all`, `fix_one`, `mute`, `reset`, `hide_console`, `show_console`, `GuiUnavailable`, `selftest`) are defined once in Interfaces. `report.unmute()` is mentioned as optional in Task 4 so the implementer can choose how to restore a real console.
