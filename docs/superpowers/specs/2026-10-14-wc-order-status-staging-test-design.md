# WooCommerce order status test against a non-production site — spec for #117

**Date:** 2026-10-14
**Status:** draft, for review
**Issue:** #117 (project 15, WooCommerce HPOS). Parent: #116 (test against WC HPOS). Needs: #113 (test strategy, done enough to build on), #111, #107.

## Goal

A `wcapi`-only test (no FileMaker) that exercises the order calls the data app
makes against a **non-production** WooCommerce REST API: the LocalWP site at
`vitalseeds.local` (already installed, with a copy of the live data), or staging. Run it once with HPOS off and once with it on. A local
install suits this best: HPOS can be toggled freely, nothing can email a real
customer, and no shared site is touched. If both runs pass
the REST contract the app relies on has not changed.

## What the app depends on

Only one order call exists today, in
[orders/status.py](../../../src/vs_data_api/vs_data/orders/status.py)
(`wc_orders_update_status`):

- `POST orders/batch` with `{"update": [{"id", "status"}]}`
- reads `id`, `order_key`, `status`, `date_completed`, `date_completed_gmt`
  from each entry of `update` in the response
- `date_completed` is then written into the link database

HPOS changes where orders are stored, not the REST shape, so these are the
fields most worth checking (HPOS-backed `date_completed` handling is the
likeliest place for drift).

## Design

One test module, `tests/integration/wc/test_order_status.py`, all tests marked
`wcapi` so the default suite still excludes them (CLAUDE.md, #113).

Fixture `staging_order` (function scope):

1. Skip unless `VSDATA_TEST_WC_URL` is set and its host is non-production:
   `localhost`, `127.0.0.1` or `*.local` (LocalWP). Any other host (staging)
   needs `VSDATA_TEST_WC_ALLOW_REMOTE=1`. This guards against hitting
   production, and replaces comparing against `VSDATA_WC_URL`, since in the
   local/VM setup `.env` aliases `VSDATA_TEST_WC_*` to `${VSDATA_WC_*}`, which
   already point at the local site.
2. `POST orders` to create a throw-away order (`status: "pending"`, one fee
   line, no customer, `set_paid: false`) — no reliance on existing site data.
3. yield its id.
4. Teardown: `DELETE orders/{id}?force=true`, even if the test failed.

Tests:

| Test | Asserts |
|---|---|
| `test_read_order` | `GET orders/{id}` is 200; has `id`, `status`, `order_key`, `date_completed` keys |
| `test_batch_update_to_completed` | call `wc_orders_update_status(wcapi, [{"link_wc_order_id": id}], "completed")` (the real function, not a re-implementation); returns one entry with `status == "completed"`, matching `id`, non-empty `date_completed` and `date_completed_gmt` |
| `test_update_is_persisted` | after the batch call, `GET orders/{id}` shows `completed` and the same `date_completed` |
| `test_other_status` | batch update to `processing` (the `target_status` path used by `/orders/…`) round-trips |
| `test_list_filtered_by_status` | `GET orders?status=processing&per_page=1` is 200 and returns a list (list/filter queries are the other thing HPOS touches) |

Informational, not asserted: log whether HPOS is on, from
`GET system_status` (`settings` section; confirm the exact key on the staging
version). Makes a before/after run self-documenting.

## Running

```
uv run pytest tests/integration/wc --wcapi
```

Needs only `VSDATA_TEST_WC_URL`, `_KEY`, `_SECRET` (read/write key), pointing
at the LocalWP site (`http://vitalseeds.local`, or `https://` if its SSL cert
is trusted) or staging. Runs on the Mac,
no VM required. The `woocommerce` client uses OAuth 1.0a over plain `http` (a
local site) and basic auth over `https`; both work with a normal REST key. Note `make test_int`/hatch
`test_int` also passes `--fmdb`; the new tests must work without it.

## Procedure for #116

1. Run against the local install with HPOS **off** (legacy post storage): baseline, must pass.
2. Enable HPOS (WooCommerce > Settings > Advanced > Features; try with and
   without compatibility mode), run again.
3. Failures show up as diffs in the asserted fields; fix or record in #116.

## Out of scope

- FileMaker / link database (covered by `fmdb` tests and unit tests with fakes).
- Stock, product and variation endpoints (not affected by HPOS).
- Running against production.

## Decisions (was: open questions)

1. Target is LocalWP at `vitalseeds.local`, with a read/write REST key and
   non-plain permalinks (confirmed).
2. Use `http://vitalseeds.local`, so `get_api` is unchanged (no `verify_ssl`).
3. Mail plugins are disabled on the local copy.
4. `conftest.wcapi` reads `TestSettings` (`VSDATA_TEST_*`, aliased in `.env`
   to `${VSDATA_WC_*}`). Confirmed in `config.py`.
5. Use a throw-away order, created and force-deleted per test.
