# Lot summary page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve a read-only, phone-friendly summary of one seed lot at `/lot/{lot_number}` (HTML, or JSON on request), read from FileMaker.

**Architecture:** A lookup function in a new `vs_data/lots` package queries `seed_lots` through the existing `db.select`. A separate module renders HTML. A FastAPI `APIRouter` in its own module ties them together and is included in `main.app`. No new dependencies: HTML is built with `html.escape`.

**Tech Stack:** FastAPI, pypyodbc via `vs_data.fm.db`, pytest with `tests/fakes.FakeConnection`.

**Spec:** `docs/superpowers/specs/2026-10-26-lot-summary-design.md`

## Global Constraints

- Lookup by lot number only; read-only; no login.
- Source = FileMaker `Source`; Final weight = FileMaker `Original weight`, in grams, shown with a "g" unit.
- Final weight of 0 or empty, and empty Source, show "not recorded".
- Unknown lot: 404 plain page. Non-integer lot number: 422 plain page. FileMaker unreachable: 503 plain-English page, no raw ODBC error.
- JSON via `?format=json` or `Accept: application/json`; JSON requests get JSON errors `{"message": ...}`.
- `GET /lot` is a form that sends the user to `/lot/<number>`.
- Default test suite must pass with no FileMaker (`make test`); a real-FileMaker check carries the `fmdb` marker.
- Follow repo style: small single-responsibility modules, plain functions.

## Review Focus

- Lot number with whitespace, letters, a negative or huge number (`/lot/abc`, `/lot/-1`, `/lot/99999999999999999999`): 422, never a 500 or a SQL error.
- Source containing HTML (`<script>`): escaped in the page.
- Weight stored as `0`, `None`, or `""`: "not recorded", not "0 g".
- Weight with decimals (`125.5`) and whole values (`125.0`): `125.5 g` and `125 g`.
- FileMaker down while requesting HTML vs JSON: 503 in the matching format.

---

### Task 1: Field mapping and lot lookup

**Files:**
- Modify: `src/vs_data_api/vs_data/fm/vs_tables.py` (the `SeedLots` class)
- Create: `src/vs_data_api/vs_data/lots/__init__.py`, `src/vs_data_api/vs_data/lots/summary.py`
- Test: `tests/unit/test_lot_summary.py`

**Interfaces:**
- Produces: `LotSummary` (pydantic `BaseModel`): `lot_number: int`, `sku: str | None`, `source: str | None`, `final_weight_g: float | None`.
- Produces: `get_lot_summary(connection, lot_number: int) -> LotSummary | None`. `None` when no row. `final_weight_g` is `None` for 0, `None` or `""`; `source` is `None` for `None` or blank.
- `vs_data_api.vs_data.lots` re-exports both names.

- [ ] **Step 1: Write failing tests** in `tests/unit/test_lot_summary.py` using `FakeConnection({r'FROM "seed_lots"': [(lot, sku, source, weight)]})`. Tests: `test_found_lot_maps_fields` (`(3538, "CAR-1", "Seeds Ltd", 125.5)` gives those values); `test_missing_lot_returns_none` (no rows); `test_zero_weight_is_not_recorded`; `test_blank_weight_and_source_are_none` (`""` and `None`); `test_query_filters_by_lot_number` (executed SQL contains `"lot_number" = 3538` or the equivalent your `where` produces, and quotes `"Original weight"`).
- [ ] **Step 2: Run** `pytest tests/unit/test_lot_summary.py -v`. Expected: FAIL (import error).
- [ ] **Step 3: Add to `SeedLots`** `source: str = "Source"` and `original_weight: float = "Original weight"`. Implement `get_lot_summary` with `db.select(connection, "seed_lots", ["lot_number", "sku", "source", "original_weight"], where=f"lot_number = {int(lot_number)}")`. Column order in the fake rows must match that list.
- [ ] **Step 4: Run** the same command. Expected: PASS. Also run `pytest tests/unit/test_fmdb_constants.py -v` (field maps still valid).
- [ ] **Step 5: Commit** `git add -A && git commit -m "Look up a seed lot summary from FileMaker (#132)"`

### Task 2: HTML and plain-message rendering

**Files:**
- Create: `src/vs_data_api/lot_page.py`
- Test: `tests/unit/test_lot_page.py`

**Interfaces:**
- Consumes: `LotSummary` from Task 1.
- Produces: `render_lot(summary: LotSummary) -> str` (full HTML document, `<meta name="viewport" content="width=device-width, initial-scale=1">`, lot number as `<h1>`, a label/value row each for SKU, Source, Final weight).
- Produces: `render_form() -> str` (form with a number input, GET to `/lot`, whose handler redirects; see Task 3 for how it submits).
- Produces: `render_message(title: str, message: str) -> str` (plain page used for 404, 422 and 503).
- Produces: `format_weight(grams: float | None) -> str`: `"not recorded"` for `None`; otherwise `"125.5 g"` / `"125 g"`.

- [ ] **Step 1: Write failing tests**: `test_format_weight` (`None` gives `not recorded`; `125.5` gives `125.5 g`; `125.0` gives `125 g`); `test_render_lot_shows_fields` (contains lot number, SKU, source, `125.5 g`, and the viewport meta); `test_missing_values_say_not_recorded` (source and sku `None` each render `not recorded`); `test_source_is_escaped` (source `<script>x</script>` appears only as `&lt;script&gt;`); `test_render_message_escapes_text`.
- [ ] **Step 2: Run** `pytest tests/unit/test_lot_page.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the four functions with `html.escape` on every dynamic value and one small shared `_page(title, body)` helper holding the document shell and minimal mobile CSS (readable font size, no horizontal scroll). `format_weight` uses `f"{grams:g}"`.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git commit -am "Render the lot summary page (#132)"` (after `git add`).

### Task 3: Routes

**Files:**
- Create: `src/vs_data_api/lot_routes.py`
- Modify: `src/vs_data_api/main.py` (import and `app.include_router(lot_routes.router)`, next to the other setup)
- Test: `tests/smoke/test_lot_routes.py`; `tests/integration/fm/test_lot_summary_fm.py` (`@pytest.mark.fmdb`)

**Interfaces:**
- Consumes: `get_lot_summary`, `render_lot`, `render_form`, `render_message`.
- Produces: `router = APIRouter()` with `GET /lot` and `GET /lot/{lot_number}`.
- `GET /lot`: with no query returns the form; with `?lot_number=N` returns a redirect (303) to `/lot/N`. This lets the plain GET form work without JavaScript.
- `GET /lot/{lot_number}` takes `lot_number: str` and parses it with `str.strip()` and `int()`; anything non-integer, non-positive or above 2147483647 is a 422. Opens `db.connection(settings.fm_connection_string)` in a `with` block, as other routes do (get settings with `Depends(main.get_settings)` equivalent: to avoid a circular import, create the dependency by importing `get_settings` lazily or moving nothing; the simplest option is `from vs_data_api.main import get_settings` inside the route module only if `main` imports the router at the bottom).
- Format: JSON when `format=json` or the `Accept` header contains `application/json`, else HTML. JSON success body is `summary.model_dump()`; JSON errors are `{"message": ...}`.
- Any exception raised while connecting or querying becomes 503 with the plain message "Can't reach FileMaker right now. Check that FileMaker is open on the office PC." and logs the real error with `log.error`.

- [ ] **Step 1: Write failing tests** with `TestClient(main.app)`, patching `vs_data_api.vs_data.fm.db.connection` to return a `FakeConnection` (pattern as in `tests/smoke/test_api.py`) and `lot_routes.get_lot_summary` where convenient. Tests: `test_html_found` (200, `text/html`, contains the source and `125.5 g`); `test_json_found_via_query` and `test_json_found_via_accept_header`; `test_unknown_lot_404_html_and_json`; parametrized `test_bad_lot_number_422` for `abc`, `-1`, `0`, `99999999999999999999`, `1.5`, in HTML and JSON; `test_filemaker_down_503_html_and_json` (connection raises `RuntimeError("secret ODBC detail")`, body must not contain `secret ODBC detail`); `test_form_page` and `test_form_redirects_to_lot_page` (`follow_redirects=False`, 303, `Location: /lot/3538`).
- [ ] **Step 2: Run** `pytest tests/smoke/test_lot_routes.py -v`. Expected: FAIL (404s).
- [ ] **Step 3: Implement** `lot_routes.py` and include the router in `main.py`.
- [ ] **Step 4: Run** `pytest tests/smoke/test_lot_routes.py -v` and then `make test`. Expected: all PASS.
- [ ] **Step 5: Add the `fmdb` test**: fetch a known real lot with `get_lot_summary` against the real connection fixture (see `tests/integration/fm/test_stock.py` for the fixture name) and assert it returns a `LotSummary` with an int `lot_number`. It is excluded by default; run it with the FileMaker marker only if FileMaker is reachable, otherwise say it was not run.
- [ ] **Step 6: Commit** `git commit -m "Serve lot summary at /lot (#132)"` after `git add`.

---

Not touched: vsdata-doctor (no config key, `/health`, service name, log path, port or release asset changes).
