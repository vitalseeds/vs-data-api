# WooCommerce Order Status Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `wcapi`-only tests that read and update an order on the local LocalWP site (`http://vitalseeds.local`) through the REST API, so the app's order calls can be checked with HPOS off and on (#116).

**Architecture:** A new `tests/integration/wc/` package holds a host-safety guard, a throw-away-order fixture and the tests. The tests call the real `wc_orders_update_status` and the real `get_api` client, so they exercise exactly what production does. The guard is a pure function with a unit test in the default suite.

**Tech Stack:** pytest (markers `wcapi`), `woocommerce` python client, python-dotenv `.env`, `uv`/`make`.

**Spec:** [docs/superpowers/specs/2026-10-14-wc-order-status-staging-test-design.md](../specs/2026-10-14-wc-order-status-staging-test-design.md)

## Global Constraints

- Tests are marked `wcapi` and must be excluded from `make test` (CLAUDE.md, #113). `make test` must still pass on a clean checkout.
- No FileMaker, no VM: only `VSDATA_TEST_WC_URL`, `VSDATA_TEST_WC_KEY`, `VSDATA_TEST_WC_SECRET`.
- Never write to production: host must be `localhost`, `127.0.0.1`, `::1` or `*.local`; any other host needs `VSDATA_TEST_WC_ALLOW_REMOTE=1`.
- Use `http://vitalseeds.local`; `get_api` is **not** changed (no `verify_ssl` argument).
- Throw-away order created per test and deleted with `force=true`, even when the test fails.
- In `.env`, aliases use braces: `VSDATA_TEST_WC_URL=${VSDATA_WC_URL}` (bare `$VAR` is not expanded).
- Board: #117 is on project 15 only. Set it to **In Progress** when implementation starts and **In Review** when the PR is open (`--owner vitalseeds --project 15`).

## Review Focus

- A failing assertion mid-test must still delete the throw-away order (teardown in a fixture, not at the end of the test).
- A bad key or wrong URL (401/404) must fail with a clear message, not pass silently: `wc_orders_update_status` returns `None` and the batch decorator then returns `[]` on a non-200 response, so tests assert a non-empty result.
- Look-alike hosts must not pass the guard: `vitalseeds.local.example.com`, `notlocal`, `example.com/.local`.
- Statuses other than `completed` have an empty `date_completed`; the `processing` test must not assert one.
- Running with `--wcapi` but no `VSDATA_TEST_WC_*` values (dummy `https://wc.invalid`) must skip with the guard reason, not error.

---

## File Structure

- Create `tests/integration/wc/__init__.py`: package marker.
- Create `tests/integration/wc/safety.py`: `unsafe_reason(url, allow_remote)`; pure, no I/O.
- Create `tests/integration/wc/conftest.py`: `staging_order` fixture (skip guard, create, yield id, delete).
- Create `tests/integration/wc/test_order_status.py`: the `wcapi` tests.
- Create `tests/unit/test_wc_test_guard.py`: unit tests for the guard (default suite).
- Modify `Makefile`: add `test-wc` target.
- Modify `.env.example`: document the aliasing.
- Modify `README.md`: short "WooCommerce tests against LocalWP" note.

---

### Task 1: Host safety guard

**Files:**
- Create: `tests/integration/wc/__init__.py` (empty)
- Create: `tests/integration/wc/safety.py`
- Test: `tests/unit/test_wc_test_guard.py`

**Interfaces:**
- Produces: `unsafe_reason(url: str, allow_remote: bool = False) -> str | None`. Returns `None` when the URL is safe to write to, otherwise a human-readable reason (used as the skip message).
- Produces: `ALLOW_REMOTE_VAR = "VSDATA_TEST_WC_ALLOW_REMOTE"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_wc_test_guard.py
import pytest

from tests.integration.wc.safety import unsafe_reason


@pytest.mark.parametrize(
    "url",
    [
        "http://vitalseeds.local",
        "http://vitalseeds.local/",
        "https://vitalseeds.local:8443",
        "http://localhost:8888",
        "http://127.0.0.1",
        "http://[::1]:8080",
        "http://shop.localhost",
    ],
)
def test_local_hosts_are_safe(url):
    assert unsafe_reason(url) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://www.vitalseeds.co.uk",
        "http://vitalseeds.local.example.com",
        "http://notlocal",
        "http://example.com/.local",
        "https://wc.invalid",
        "",
    ],
)
def test_other_hosts_are_unsafe(url):
    reason = unsafe_reason(url)
    assert reason and "VSDATA_TEST_WC_ALLOW_REMOTE" in reason


def test_remote_host_allowed_with_opt_in():
    assert unsafe_reason("https://staging.example.com", allow_remote=True) is None
    assert unsafe_reason("", allow_remote=True) is not None  # still need a url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --extra test pytest tests/unit/test_wc_test_guard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.integration.wc'`

- [ ] **Step 3: Write minimal implementation**

```python
# tests/integration/wc/safety.py
"""Refuse to run write tests against anything that looks like production."""

from urllib.parse import urlparse

ALLOW_REMOTE_VAR = "VSDATA_TEST_WC_ALLOW_REMOTE"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
LOCAL_SUFFIXES = (".local", ".localhost")


def unsafe_reason(url: str, allow_remote: bool = False) -> str | None:
    """Return why `url` must not be written to, or None if it is safe."""
    host = urlparse(url or "").hostname
    if not host:
        return "VSDATA_TEST_WC_URL is not set to a usable URL"
    if allow_remote:
        return None
    if host in LOCAL_HOSTS or host.endswith(LOCAL_SUFFIXES):
        return None
    return f"{host} is not a local host; set {ALLOW_REMOTE_VAR}=1 to run write tests against it"
```

Create `tests/integration/wc/__init__.py` as an empty file.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --extra test pytest tests/unit/test_wc_test_guard.py -v`
Expected: PASS (all cases), then `make test` still passes.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/wc/__init__.py tests/integration/wc/safety.py tests/unit/test_wc_test_guard.py
git commit -m "Add host guard for WooCommerce write tests (#117)"
```

---

### Task 2: Throw-away order fixture and order tests

**Files:**
- Create: `tests/integration/wc/conftest.py`
- Create: `tests/integration/wc/test_order_status.py`

**Interfaces:**
- Consumes: `unsafe_reason`, `ALLOW_REMOTE_VAR` from `tests/integration/wc/safety.py`; top-level fixture `wcapi` from `tests/conftest.py` (client built from `VSDATA_TEST_WC_*`); `wc_orders_update_status(wcapi, orders: list[dict], target_status: str) -> list[dict]` from `vs_data_api.vs_data.orders.status` (each update has `id`, `order_key`, `status`, `date_completed`, `date_completed_gmt`).
- Produces: fixture `staging_order(wcapi) -> int`, the id of a `pending` order that is force-deleted on teardown.

- [ ] **Step 1: Write the fixture and the first (read) test**

```python
# tests/integration/wc/conftest.py
import os

import pytest

from tests.integration.wc.safety import ALLOW_REMOTE_VAR, unsafe_reason
from vs_data_api.config import TestSettings


@pytest.fixture
def staging_order(wcapi):
    """A pending order created for one test and force-deleted afterwards."""
    url = TestSettings().vsdata_wc_url
    reason = unsafe_reason(url, allow_remote=os.environ.get(ALLOW_REMOTE_VAR) == "1")
    if reason:
        pytest.skip(reason)

    response = wcapi.post(
        "orders",
        {"status": "pending", "set_paid": False, "fee_lines": [{"name": "vs-data-api HPOS test", "total": "1.00"}]},
    )
    assert response.status_code == 201, f"could not create order: {response.status_code} {response.text[:200]}"
    order_id = response.json()["id"]
    try:
        yield order_id
    finally:
        wcapi.delete(f"orders/{order_id}", params={"force": True})
```

```python
# tests/integration/wc/test_order_status.py
"""
Order calls the app makes, against a real non-production WooCommerce (LocalWP).

Run with HPOS off, then on (#116):  uv run --extra test pytest tests/integration/wc --wcapi
"""

import pytest

from vs_data_api.vs_data.orders.status import wc_orders_update_status

pytestmark = [pytest.mark.wcapi]


def get_order(wcapi, order_id):
    response = wcapi.get(f"orders/{order_id}")
    assert response.status_code == 200, f"{response.status_code} {response.text[:200]}"
    return response.json()


def test_read_order(wcapi, staging_order):
    order = get_order(wcapi, staging_order)

    assert order["id"] == staging_order
    assert order["status"] == "pending"
    for key in ("order_key", "date_completed", "date_completed_gmt"):
        assert key in order
```

- [ ] **Step 2: Run to verify the read test passes against LocalWP**

Run: `uv run --extra test pytest tests/integration/wc --wcapi -v`
Expected: `test_read_order` PASSED. With `VSDATA_TEST_WC_URL` set to a non-local host and no opt-in: SKIPPED with the guard reason (check this once).

- [ ] **Step 3: Add the remaining tests**

```python
def test_batch_update_to_completed(wcapi, staging_order):
    updates = wc_orders_update_status(wcapi, [{"link_wc_order_id": staging_order}], target_status="completed")

    assert updates, "batch update returned nothing: check the key has write access and permalinks are not Plain"
    (update,) = updates
    assert update["id"] == staging_order
    assert update["status"] == "completed"
    assert update["order_key"]
    assert update["date_completed"]
    assert update["date_completed_gmt"]


def test_update_is_persisted(wcapi, staging_order):
    (update,) = wc_orders_update_status(wcapi, [{"link_wc_order_id": staging_order}], target_status="completed")

    order = get_order(wcapi, staging_order)

    assert order["status"] == "completed"
    assert order["date_completed"] == update["date_completed"]


def test_other_status_round_trips(wcapi, staging_order):
    updates = wc_orders_update_status(wcapi, [{"link_wc_order_id": staging_order}], target_status="processing")

    assert [u["status"] for u in updates] == ["processing"]
    assert get_order(wcapi, staging_order)["status"] == "processing"


def test_list_orders_filtered_by_status(wcapi, staging_order):
    response = wcapi.get("orders", params={"status": "pending", "per_page": 1})

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_report_hpos_state(wcapi, capsys):
    """Informational: records whether HPOS is on, so before/after runs are labelled."""
    response = wcapi.get("system_status")
    assert response.status_code == 200
    settings = response.json().get("settings", {})
    with capsys.disabled():
        print(f"\nHPOS enabled: {settings.get('HPOS_enabled', 'unknown')}")
```

- [ ] **Step 4: Run all and verify**

Run: `uv run --extra test pytest tests/integration/wc --wcapi -v -s`
Expected: 6 PASSED and an `HPOS enabled:` line. Then confirm cleanup: in WooCommerce > Orders (and Trash) no "vs-data-api HPOS test" orders remain.

Failure check (once, then revert): set a wrong `VSDATA_TEST_WC_SECRET` and run. Expected: the fixture fails with `could not create order: 401 …`, not a pass.

- [ ] **Step 5: Verify the default suite is unaffected, then commit**

Run: `make test`
Expected: PASS, the new `wc` tests not collected as run (deselected by `-m "not wcapi …"`).

```bash
git add tests/integration/wc/conftest.py tests/integration/wc/test_order_status.py
git commit -m "Add wcapi order status tests against a local WooCommerce (#117)"
```

---

### Task 3: Make target and docs

**Files:**
- Modify: `Makefile` (new target after `smoke`, add to `.PHONY`)
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- Produces: `make test-wc` runs `tests/integration/wc` with `--wcapi`.

- [ ] **Step 1: Add the Makefile target**

Add `test-wc` to the `.PHONY` line, and below `smoke:`:

```make
test-wc: ## Run the WooCommerce order tests against the local/test site (VSDATA_TEST_WC_*, needs --wcapi)
	uv run --extra test pytest tests/integration/wc --wcapi -v -s
```

- [ ] **Step 2: Document the env aliasing**

In `.env.example`, under the `VSDATA_TEST_WC_*` comments, add:

```
# Using the same LocalWP site for the app and the tests? Alias, with braces
# (python-dotenv does not expand a bare $VAR):
# VSDATA_TEST_WC_URL=${VSDATA_WC_URL}
# VSDATA_TEST_WC_KEY=${VSDATA_WC_KEY}
# VSDATA_TEST_WC_SECRET=${VSDATA_WC_SECRET}
# Write tests only run against localhost / *.local. For any other host set:
# VSDATA_TEST_WC_ALLOW_REMOTE=1
```

- [ ] **Step 3: Add the README note**

Add a short section "WooCommerce tests (LocalWP)" to `README.md` covering: site at `http://vitalseeds.local` with a read/write key and non-Plain permalinks; `make test-wc`; run once with HPOS off and once with it on (WooCommerce > Settings > Advanced > Features); the tests create and delete their own order.

- [ ] **Step 4: Verify**

Run: `make test-wc` then `make test`
Expected: both pass; `make help` lists `test-wc`.

- [ ] **Step 5: Commit**

```bash
git add Makefile .env.example README.md
git commit -m "Document and add make test-wc for WooCommerce order tests (#117)"
```

---

## Self-review

- **Spec coverage:** guard (Task 1); fixture, read, batch complete, persisted, other status, list filter, HPOS report (Task 2); running, env and procedure for #116 (Task 3). Out-of-scope items are untouched.
- **Placeholders:** none; every step carries code or exact commands.
- **Names:** `unsafe_reason`, `ALLOW_REMOTE_VAR`, `staging_order`, `wc_orders_update_status` are used identically across tasks.
- **Assumption to verify in Task 2:** the system status key is `HPOS_enabled`; the test uses `.get(..., 'unknown')`, so a different key shows `unknown` rather than failing.
