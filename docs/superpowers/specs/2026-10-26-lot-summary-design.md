# Serve a FileMaker lot summary, spec for #132

**Date:** 2026-10-26
**Status:** draft, for review
**Issue:** #132 (on no project board)

## Goal

Staff often need to see what FileMaker holds for one seed lot, and want to do it
on a phone beside the seed tray. The tray label shows a SKU and/or lot number.
Today that means finding the lot in the portal on the FileMaker home screen.

Staff use the details to decide whether to count out seeds for a germination
test (if none exists) and whether to bag the lot and put it in the store. They
also use them to fill in blanks by hand in Processing flow, the app that manages
processing.

vs-data-api serves a one-page, mobile-friendly summary of a single lot, read
from FileMaker.

## Decisions

| Question | Decision |
|---|---|
| Lookup | By **lot number only** in this first step. A SKU can have several lots, so SKU search (list the lots, pick one) is a later step. |
| Access | Over the LAN from a phone browser. **No login**, same as the rest of the API. |
| Writes | None. Read-only. |
| Shape | HTML page at `GET /lot/{lot_number}`, plus the same data as JSON. |
| First fields | Lot number, SKU, **Source**, **Final weight**. |
| Later fields | Germination tests, germination result (if known), notes, as listed in #132. |

## Behaviour

- `GET /lot/{lot_number}` returns a small HTML page, readable on a phone without
  zooming: the lot number as a heading, then each field as a label and value.
  A field with no value shows "not recorded", not a blank, so a gap is visible.
- `GET /lot/{lot_number}?format=json` (or `Accept: application/json`) returns the
  same fields as JSON. [My guess; the builder may pick the neater way to
  negotiate this.]
- Unknown lot number: a plain "Lot N not found" page with status 404.
- A lot number that is not a whole number: 422 with the same plain style.
- FileMaker unreachable: a plain-English page saying so, status 503. It does
  not dump the raw ODBC error (the existing exception handler returns JSON for
  FileMaker's benefit; this page is for people).
- Errors follow the format asked for: a JSON request gets JSON errors in the
  API's usual shape (`{"message": ...}`), an HTML request gets plain pages.
  [My call.]
- A small form at `GET /lot` takes a lot number and goes to its page, so staff
  can type one in without editing the URL. [My guess.]

## Data

Source and final weight are fields on the `seed_lots` table (confirmed). From
the database design report, the FileMaker field names are:

| Page label | FileMaker field |
|---|---|
| Lot number | `lot_number` |
| SKU | `sku` |
| Source | `Source` |
| Final weight | `Original weight` (confirmed: FileMaker has no field called "final weight") |

The `SeedLots` class in `vs_data/fm/vs_tables.py` maps only `lot_number` and
`sku`, so it needs `Source` and `Original weight` added (the repo's
convention is to rename awkward FileMaker fields in the database over time; the
builder can follow it or map the names as they are). If they are not exposed
through the ODBC connection, exposing them in FileMaker is part of this work.
For later steps, germination tests are in `Germ_tests` (`Lot_numberFK`, `Date`,
`Result`, `Seed count`, `test_number`, `Notes`); `seed_lots` also has `Notes`.

- `lot_number` is unique in `seed_lots` (confirmed), so the lookup returns at
  most one row.
- Final weight is in **grams**; show it with a "g" unit.
- Source is **free text**; show it as stored.
- A final weight of **0 means not recorded**, as does an empty Source; both show
  "not recorded". #132 notes the details are shown in the portal on the home
screen, so they may need adding to the database design report.

Final weight is owned by Processing flow and written into FileMaker by the sync
(see `2026-09-23-processing-flow-sync-client.md`). This page shows what
FileMaker holds, which may lag Processing flow. That is acceptable for now.

## Structure

Follow the repo's habit of small single-purpose modules. Roughly: a lot-summary
query/model beside the other FileMaker code, and a router plus a template for
the page. The exact layout is the builder's call.

## Tests

Default suite only (no FileMaker): the route against a faked lookup, covering
found, not found, bad lot number, missing field, FileMaker down, and JSON vs
HTML. A test marked `fmdb` can check the real field names against FileMaker.

## Non-goals

- SKU search, germination tests, result and notes in this first step.
- Authentication, or access from outside the LAN.
- Editing anything in FileMaker or Processing flow.
- Any change to the vsdata-doctor, unless a change here touches something it
  relies on (see `src/vs_doctor/CLAUDE.md`).

## Left to the builder

HTML templating approach (inline string, Jinja, etc.), URL details beyond
`/lot/{lot_number}`, module names, and how to word the plain-English messages.
