# Lot germination results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a lot's germination result and a dated list of its germination tests on `/lot/{lot_number}` and in its JSON.

**Architecture:** A `Germ_tests` mapping and a second query in `vs_data/lots`, folded into `LotSummary`; the HTML renderer and JSON get the new fields. No new route.

**Tech Stack:** as the lot summary plan (FastAPI, pydantic, `db.select`, `FakeConnection`).

**Spec:** `docs/superpowers/specs/2026-10-26-lot-summary-design.md`, section "Step 2"

## Global Constraints

- Result = `Result` of the latest test (by `Date`, ties by `test_number`) that has one; blank, `None` or `""` is no result. A `Result` of 0 is a real result (unlike weight).
- Test list newest first; test with no `Result` shows "in progress"; no tests shows "No germination tests yet".
- Result displays as a percentage ("85%", "87.5%"); this unit is a guess, confirmed in Task 2.
- Read-only; Pass/Borderline/Fail and `seed_lots.Notes` are out of scope.
- A bad value in a test row gives the existing 500 "can't be read" message (`ValidationError` path), not a 503.
- `make test` must pass with no FileMaker; one `fmdb` test checks the field names.
- Test and note text is HTML-escaped.

## Review Focus

- Lot with no tests: "No germination tests yet", result "not recorded", no error.
- Tests exist but none has a result: result "not recorded", all rows "in progress".
- Result of 0 and of 100: shown as "0%" / "100%", not "not recorded".
- Two tests on the same date: stable order (by `test_number`), latest result picked deterministically.
- Test with no `Date`: listed last, shown as "no date", never crashes sorting.
- Notes or seed count containing HTML: escaped.

---

### Task 1: Germination tests lookup

**Files:**
- Modify: `src/vs_data_api/vs_data/fm/vs_tables.py` (add `GermTests`, `table_name = "Germ_tests"`)
- Create: `src/vs_data_api/vs_data/lots/germination.py`
- Modify: `src/vs_data_api/vs_data/lots/summary.py`, `src/vs_data_api/vs_data/lots/__init__.py`
- Test: `tests/unit/test_lot_germination.py`; extend `tests/unit/test_lot_summary.py`

**Interfaces:**
- `GermTests` fields: `lot_number = "Lot_numberFK"`, `date = "Date"`, `result = "Result"`, `seed_count = "Seed count"`, `test_number = "test_number"`, `notes = "Notes"`.
- Produces: `GermTest` (pydantic): `date: datetime.date | None`, `result: float | None`, `seed_count: str | None`, `notes: str | None`.
- Produces: `get_germ_tests(connection, lot_number: int) -> list[GermTest]`, newest first (no date last, then `test_number` descending), blank values as `None`.
- Produces: `latest_result(tests: list[GermTest]) -> float | None`: result of the first test with a non-`None` result.
- `LotSummary` gains `germ_tests: list[GermTest]` and `germ_result: float | None`; `get_lot_summary` fills both only when the lot exists (one extra query).

- [ ] **Step 1: Write failing tests** with `FakeConnection({r'FROM "Germ_tests"': rows, r'FROM "seed_lots"': [...]})`: `test_tests_newest_first`; `test_no_date_sorts_last`; `test_same_date_ordered_by_test_number`; `test_blank_result_is_none_but_zero_is_kept`; `test_latest_result_skips_tests_without_result`; `test_latest_result_none_when_no_results`; `test_summary_includes_tests_and_result`; `test_missing_lot_makes_no_germ_query` (only one SQL statement executed). Row order must match the selected column list.
- [ ] **Step 2: Run** `uv run --extra test pytest tests/unit/test_lot_germination.py tests/unit/test_lot_summary.py -q`. Expected: FAIL (import errors).
- [ ] **Step 3: Implement** the mapping, `get_germ_tests` (`db.select` with `where=f"Lot_numberFK = {int(lot_number)}"`, sort in Python so ordering rules are testable), `latest_result`, and the `LotSummary` fields. Keep existing step 1 tests passing (their fake has no `Germ_tests` rows, so the list is empty).
- [ ] **Step 4: Run** the same command plus `tests/unit/test_fmdb_constants.py`. Expected: PASS.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Look up germination tests for a lot (#132)"`.

### Task 2: Show it on the page and in JSON

**Files:**
- Modify: `src/vs_data_api/lot_page.py`
- Test: `tests/unit/test_lot_page.py`, `tests/smoke/test_lot_routes.py`, `tests/integration/fm/test_lot_summary_fm.py`

**Interfaces:**
- Consumes: `LotSummary.germ_result`, `LotSummary.germ_tests`, `GermTest` from Task 1.
- Produces: `format_result(percent: float | None) -> str` (`"not recorded"` for `None`; `"85%"`, `"87.5%"`, `"0%"`); `render_lot` gains a "Germination result" row and a "Germination tests" section.

- [ ] **Step 1: Write failing tests**: `test_format_result` (`None`, `85`, `87.5`, `0`, `100`); `test_render_lot_lists_tests_newest_first` (dates appear in order); `test_in_progress_when_no_result`; `test_no_tests_message`; `test_test_notes_and_seed_count_escaped`; `test_test_without_date_says_no_date`; smoke: `test_json_includes_germination` (`germ_result` and `germ_tests` keys, ISO dates) and `test_unreadable_germ_result_is_500_not_503` (text in `Result`). Fmdb: extend the existing test to call `get_germ_tests` for a lot.
- [ ] **Step 2: Run** `uv run --extra test pytest tests/unit/test_lot_page.py tests/smoke/test_lot_routes.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `format_result` and the renderer changes (escape every dynamic value; the tests section sits below the existing fields; phone-friendly, one card or line per test).
- [ ] **Step 4: Run** `uv run --extra test pytest -q`. Expected: all PASS.
- [ ] **Step 5: Check the result unit** against real data if FileMaker is reachable (`Result` as 0-100 or a 0-1 fraction); if it is a fraction, change `format_result` and its tests before finishing, and record the ruling in the commit message.
- [ ] **Step 6: Commit** `git add -A && git commit -m "Show germination result and test list on the lot page (#132)"`.

---

Not touched: vsdata-doctor (no config key, `/health`, service name, log path, port or release asset changes).
