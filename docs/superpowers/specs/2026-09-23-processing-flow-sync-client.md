# Syncing with Processing flow — spec for vs-data-api

**Date:** 2026-09-23
**Status:** draft. The API side (Processing flow) is built, tested and
merged. Everything about how vs-data-api calls it — what triggers a call,
how it schedules retries, how it alerts on failure, how it converts units —
is open and is this project's to decide. This document says what the other
side expects and provides; fill in the rest below.
**Related:** The authoritative design and API reference live in the
`processing_flow` repo:
- `docs/superpowers/specs/2026-09-21-filemaker-sync-design.md` (why it's
  built this way)
- `docs/sync-api.md` (the API reference Processing flow publishes for this
  purpose — this document restates and extends it with exact validation
  rules current as of the branch that shipped it)

If the two ever disagree, `processing_flow`'s own docs are correct — this
copy exists so vs-data-api's implementation work has a spec to build
against in this repo, per the usual planning workflow here.

## Overview: what this is for

Processing flow is the web app Vital Seeds uses to track seed lots through
cleaning, testing and packing. It's replacing an Airtable base. But lots,
SKUs and sales figures still originate in FileMaker — vs-data-api's job is
to keep them in step.

The shape of it:

- **Processing flow never calls out.** It stays on the VPS and has no route
  into the local network. Every call is inbound, authenticated with a
  bearer token, and started by vs-data-api.
- **vs-data-api sends** lot data and sales figures into Processing flow.
- **vs-data-api fetches** each lot's final weight back out, once Processing
  flow (or a staff member) has recorded it, and writes that into FileMaker.
- **FileMaker wins** on the fields it owns — lot number, season, SKU, crop,
  variety, source, grams per pack. A send always overwrites Processing
  flow's copy of those fields, even if a staff member typed something into
  them first. Processing flow makes those fields read-only in its own UI
  once a lot has been matched once (see "Linked lots" below) — that's
  Processing flow's problem to manage, not vs-data-api's.
- **Processing flow wins** on the final weight. vs-data-api never sends a
  weight in as authoritative — it only sends `stock_db_weight` for
  Processing flow to *compare* against its own figure, so Processing flow
  can tick a box confirming the two now match. The actual weight value
  always flows FileMaker ← Processing flow, via the fetch call.

A typical cycle, at whatever cadence vs-data-api decides:

1. Send lots (creates new ones, updates existing ones by lot number).
2. Send sales figures (skipped, not rejected, for any SKU Processing flow
   doesn't know yet — so lots first, sales second, is the safe order).
3. Fetch final weights for lots vs-data-api cares about.
4. Write those weights into FileMaker.
5. Optionally, send lots again carrying the weight FileMaker now holds
   (`stock_db_weight`) — this lets Processing flow tick "weight added to
   stock database" immediately, rather than waiting for the next scheduled
   send to notice the match.

Nothing above requires steps 1–5 to run together. A FileMaker button could
run all five in one go for a single split lot; a back-stop timer could run
lots and weights hourly and sales daily. That choice, along with retry
behaviour, failure alerting, and how weight units get converted between
FileMaker's and Processing flow's conventions, is left to vs-data-api.

## The contract: what Processing flow requires and provides

Everything in this section is Processing flow's behaviour, not a
suggestion — it's what a client must satisfy to get a 200, and what it can
rely on getting back.

### Authentication

- Every call under `/api/sync/` requires `Authorization: Bearer <token>`,
  where `<token>` is the shared secret Tom configures as `SYNC_TOKEN` on
  the Processing flow server.
- **404** means the server has no token configured yet (sync is turned
  off) — not a routing problem on vs-data-api's end.
- **401** means the token is missing, empty, or doesn't match.
- The token must be treated as a secret on both ends: at least 40
  characters, transmitted over HTTPS, never logged, never put in a URL
  query string.
- These are the only Processing flow endpoints that work this way — every
  other page requires a signed-in Google account. There's nothing else on
  the app for vs-data-api to authenticate against.

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/sync/lots/` | Create or update lots |
| `GET` | `/api/sync/lots/` | Fetch lot numbers, seasons and final weights |
| `POST` | `/api/sync/sales/` | Create or update sales figures, one row per SKU |

All request and response bodies are JSON. There is no XML, no form
encoding, and no pagination — a send is capped at 1,000 rows (see below),
and a fetch with no filter returns every lot that has a lot number, in one
response.

### Send lots — `POST /api/sync/lots/`

```json
{
  "lots": [
    {
      "lot_number": "3538",
      "season": 2026,
      "sku": "XFMCJ",
      "crop": "Courgette",
      "variety": "Defender",
      "source": "Field 3",
      "g_per_pack": "2.50",
      "stock_db_weight": "125.5"
    }
  ]
}
```

**Fields:**

| Field | Required | Type | Constraint | Notes |
| --- | --- | --- | --- | --- |
| `lot_number` | yes | string | max 100 characters | Matched after trimming leading/trailing spaces. Sending `null` or leaving it out entirely is treated as missing, not as the literal text "None" — same for every other field below. |
| `season` | yes | integer (year) | must already exist in Processing flow | Tom creates a new season before the first send of it. An unknown year is a validation problem, not a silent skip. |
| `sku` | no | string | max 100 characters | |
| `crop` | no | string | max 200 characters | |
| `variety` | no | string | max 200 characters | |
| `source` | no | string | max 200 characters | |
| `g_per_pack` | no | decimal string | up to 6 total digits, 2 after the decimal point (e.g. `"2.50"`, not `"2.500"` or a 5-digit whole part) | |
| `stock_db_weight` | no | decimal string | same unit as Processing flow's own weight | **Never saved as a field.** See "The weight check" below. |

- A field **left out of the row entirely** is left untouched on the stored
  lot.
- A field **sent as `""` or `null`** clears the stored value (except
  `lot_number` and `sku`/id-like fields where `null` is treated as "not
  provided" for validation purposes, per the row above).
- Any value that would not fit the target field (too many digits, too many
  decimal places, too long a string) is rejected as a validation problem —
  it is never truncated or silently accepted. This matters: earlier in
  development, sending an out-of-range decimal returned success and then
  permanently broke every later read of that row. That's fixed; treat a
  422 with a size/format complaint as "value doesn't fit," not as a bug to
  route around by only sending pre-truncated data.
- Up to 1,000 lot rows per call.
- Repeating the same `lot_number` twice within one call is a validation
  problem, not an automatic dedupe.
- A field vs-data-api doesn't recognise, or a field Processing flow itself
  owns (like `status`, `checked_in`, `final_weight`, `weight_in_stock_db`,
  and everything else not listed in the table above), is refused with a
  problem naming it — not silently ignored.

**A good send answers `200`:**

```json
{"created": 3, "updated": 10, "unchanged": 400, "skipped": []}
```

`skipped` is always `[]` for the lots endpoint — it's part of the response
shape because sales' responses share the same structure, but lots has
nothing that can be legitimately skipped the way an orphan sales row can.

**A send with any problem answers `422` and saves nothing at all** — not
even the rows that were individually fine:

```json
{
  "problems": [
    {"row": 4, "lot_number": "3610", "problem": "season 2027 does not exist"},
    {"row": 9, "lot_number": "3611", "problem": "field 'status' belongs to the app"}
  ]
}
```

Every problem in the batch is listed in one response — vs-data-api doesn't
need to fix one row, resend, and discover the next problem. `row` is the
1-based position in the `lots` array as sent. Sending the same payload
again after fixing the reported problems is always safe.

### The weight check

`stock_db_weight` is how vs-data-api tells Processing flow "this is what
FileMaker currently has recorded for this lot's weight" — in the same unit
Processing flow uses for `final_weight`. Converting units, if FileMaker's
internal unit differs, is vs-data-api's job; Processing flow does no
conversion.

- It is compared against the lot's own `final_weight`, to one decimal
  place, and then discarded. It never becomes a stored field value.
- If the two match and are not zero, Processing flow ticks its own "weight
  added to stock database" flag. This flag is what tells Processing flow
  staff the FileMaker side is in sync.
- The tick never gets removed by a later send, even if a later
  `stock_db_weight` doesn't match. Once confirmed, it stays confirmed.
- If either figure is missing, blank, or zero, nothing happens — no tick,
  no error.
- The comparison runs on every send, even one that changes nothing else
  about the lot. A tick that changes from unset to set on its own counts
  as `updated` in the response.
- Sending `final_weight` or `weight_in_stock_db` directly, rather than
  `stock_db_weight`, is refused — those are fields Processing flow owns.

### Send sales — `POST /api/sync/sales/`

```json
{
  "sales": [
    {
      "sku": "XFMCJ",
      "packets_last_year": 420,
      "seeds_per_packet": 25,
      "weight_per_50_seeds": "0.34",
      "grams_per_packet": "2.50",
      "grams_on_shelf": "310.0",
      "days_of_stock_left": 95
    }
  ]
}
```

**Fields:**

| Field | Required | Type | Constraint |
| --- | --- | --- | --- |
| `sku` | yes | string | The key. Matched against any lot's SKU — see below. |
| `packets_last_year` | no | non-negative integer | |
| `seeds_per_packet` | no | non-negative integer | |
| `weight_per_50_seeds` | no | decimal string | up to 6 total digits, 2 after the decimal point |
| `grams_per_packet` | no | decimal string | up to 6 total digits, 2 after the decimal point |
| `grams_on_shelf` | no | decimal string | up to 8 total digits, 1 after the decimal point |
| `days_of_stock_left` | no | non-negative integer | |

- **No financial data travels over this call, ever.** Sales figures are
  packet counts and stock-cover numbers only — there is no field for
  price, revenue, or cost, and sending one is refused as unrecognised.
  Don't add one on the FileMaker side and expect it through; it has to
  stay off this wire entirely.
- A negative number for any of the integer fields is rejected as a
  validation problem, same as an out-of-range decimal.
- A SKU can legitimately belong to lots in more than one season (SKUs
  aren't unique to a single season in Processing flow) — that's not an
  error condition for this call. A sales row just needs *some* lot with a
  matching SKU to exist.
- A row whose SKU matches **no** lot at all is **skipped**, not rejected —
  it comes back named in the `skipped` list of the response, with a
  reason, and the rest of the send still succeeds. Sending lots before
  sales (or at least ahead of the sales figures for brand-new SKUs) avoids
  this; a skipped row is picked up cleanly on the next send once its lot
  exists.
- Each send fully replaces the stored row for that SKU — it's not a
  partial merge with what's already stored. Sending the exact same values
  twice in a row is reported as `unchanged`, not `updated`.
- Repeating the same `sku` twice within one call is a validation problem.
- Up to 1,000 rows per call.

**Response shape matches the lots endpoint**, with `skipped` genuinely
populated here when relevant:

```json
{"created": 3, "updated": 10, "unchanged": 400, "skipped": [{"sku": "ZZZZ", "reason": "no lot has this SKU"}]}
```

A validation problem still answers `422` with every problem listed, and
saves nothing — same all-or-nothing rule as lots.

### Fetch lots — `GET /api/sync/lots/`

```
GET /api/sync/lots/
GET /api/sync/lots/?lot_number=3538&lot_number=3540
```

```json
{"lots": [{"lot_number": "3538", "season": 2026, "final_weight": "125.5"}]}
```

- With no `lot_number` query parameter, returns every lot that has a
  non-blank lot number (lots with no number — legacy or in-progress
  records — are left out, since there's nothing for FileMaker to match
  them to).
- Repeat `?lot_number=` as many times as needed to filter to specific
  lots.
- `final_weight` is a decimal-as-string (e.g. `"125.5"`), or `null` if
  Processing flow hasn't recorded one yet.
- Only these three fields come back today. If vs-data-api needs more
  fields fetched later (e.g. to reconcile something else), that's a
  request to make of Processing flow — the fetch shape isn't something
  vs-data-api can extend unilaterally.
- This call changes nothing on the Processing flow side. It's safe to call
  as often as useful; there's no rate limit enforced by the app itself
  (see "Left for vs-data-api" below).

### All-or-nothing, always

Both `POST` endpoints validate every row in the request before writing
anything. If any row has any problem, the entire call is rejected with a
`422` and the database is untouched — not even the valid rows in the same
batch are saved. This means:

- A partial failure never leaves Processing flow in a half-updated state
  for one call.
- vs-data-api can safely retry a fixed payload without worrying about
  double-applying the rows that "already went through" — because none of
  them did.
- There's no need to chunk a send defensively to limit blast radius,
  except to stay under the 1,000-row cap.

### Linked lots — why some fields become read-only

The first time a send's `lot_number` matches an existing lot (whether it
was created by a staff member in Processing flow, imported from the old
Airtable base, or created by an earlier vs-data-api send), Processing flow
marks that lot as "linked to FileMaker." From that point on, that lot's
FileMaker-owned fields (`lot_number`, `season`, `sku`, `crop`, `variety`,
`source`, `g_per_pack`) become read-only inside Processing flow's own UI —
staff can see them but not edit them there.

This has one practical consequence for vs-data-api: **a send always wins**
on those fields, whether or not the lot pre-existed and whether or not a
staff member had typed something different into it. There's no merge
logic and no conflict to resolve — vs-data-api's value is authoritative
the moment it arrives.

A lot created directly in Processing flow (not yet linked) must have a
lot number for a human to save it — the app enforces this specifically so
a later FileMaker send has something to match against.

## What's deliberately left open for vs-data-api

The processing_flow side is finished and will not change without a heads
up. Everything below is genuinely vs-data-api's design space:

- **When to call.** A FileMaker button firing all three calls at once, a
  scheduled poll, or both — Processing flow has no opinion, as long as
  calls stay under the 1,000-row cap.
- **Retry and backoff policy** on a failed call (`4xx`/`5xx`/network
  error).
- **Failure alerting** — Processing flow does not push notifications of
  any kind; if a send silently stops working, nobody on the Processing
  flow side will notice until someone asks why the data looks stale.
  vs-data-api owns detecting and surfacing that.
- **Unit conversion** for weights, if FileMaker's internal unit for a
  lot's weight differs from Processing flow's. `stock_db_weight` and the
  fetched `final_weight` are compared/returned in whatever unit Processing
  flow itself stores (currently the same unit staff type into the lot
  form) — get the conversion right before comparing or writing back.
- **How vs-data-api reads FileMaker** (ODBC queries, which fields map to
  which, how it decides a lot is "ready to send") — entirely internal to
  vs-data-api / the `vs-data` package, and out of scope for this document.
- **Rate limiting or an IP allow-list** on the Processing flow side, if
  ever wanted, is a Caddy/infrastructure concern (`tombolatron` repo), not
  something this API enforces itself today.

## Open questions

- What unit does FileMaker's weight field actually use, and does it match
  what staff type into Processing flow's lot form? (Processing flow stores
  whatever is sent, unconverted, so this needs to be right on the
  vs-data-api side before the weight check can be trusted.)
- Confirm real production lot numbers have no duplicates before the first
  live send — Processing flow's database now enforces uniqueness on
  non-blank lot numbers, and a send that would create a duplicate is
  refused, not merged.
