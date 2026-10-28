# Serve a SKU lot list, spec for #134

**Date:** 2026-10-27
**Status:** draft, for review
**Issue:** #134 (on no project board)

## Goal

#132 lets staff look up one lot by lot number on a phone. The tray label often
shows only a SKU, and a SKU can have several lots. Add the SKU step that spec
left for later: type a SKU, see its lots, tap one to open it in the lot page.

Same model as the lot page: search box at the top, the page refreshes itself as
typing pauses, read-only, no login, LAN only.

## Behaviour (from the issue)

- `GET /sku/{sku}` lists the lots in FileMaker with that SKU. The match is case
  insensitive (`onwl` finds `OnWl`).
- Sorted by **Date received**, newest first. A lot with no date goes last.
- Each row shows:
  - lot number, as a link to `/lot/{lot_number}` (the lot page pre-filled);
  - **Date received**;
  - **current weight / initial weight**, e.g. `120 g / 500 g`.
- A lot whose current weight is **0** is shown grey italic. An *unknown* current
  weight (blank) is not grey italic and shows "not recorded" in place of the
  number.
- JSON via `?format=json` or `Accept: application/json`, as for the lot page.

## Decisions (my calls, marked as such)

| Question | Decision |
|---|---|
| One search box or two | **Each page has its own box** (confirmed). `/lot/{lot}` takes lot numbers only, with the numeric keyboard; `/sku/{sku}` takes SKUs only, with a text keyboard. Neither guesses what was typed. Beside each box is one toggle link reading `lot / sku` that goes to the other search page. The word for the page you are on is bold, the other is grey italic: on `/lot` it reads **lot** *sku*, on `/sku` it reads *lot* **sku**. [Originally strikethrough; changed to grey italic on request.] |
| Unknown SKU | 404 "No lots found for SKU X" (same style as "Lot N not found"). A SKU with no lots in FileMaker is indistinguishable from a mistyped one, so one message covers both. |
| No JavaScript | Each box submits to its own form route: the existing `GET /lot?lot_number=N` redirects to `/lot/N`, and the new `GET /sku?sku=X` redirects to `/sku/X`. An empty box shows the plain form. |
| Errors | Reuse the lot page's: 503 plain-English when FileMaker is down, 500 "can't be read" for a bad value, JSON `{"message": ...}` when JSON was asked for. |
| Very long lists | No paging. A SKU is unlikely to have more than a few dozen lots. [My guess; check against `seed_lots`, 2319 rows.] |
| Lot page link back | The lot page's SKU also becomes a link to `/sku/{sku}`, on top of the toggle. [My guess; drop if unwanted.] |

## Data

All fields are on `seed_lots` (from the database design report):

| Page label | FileMaker field | Type |
|---|---|---|
| Lot number | `lot_number` | Number |
| SKU | `sku` | Text |
| Date received | `Date received` | Date (auto-enters today's date) |
| Initial weight | `Original weight` | Number, grams |
| Current weight | `Current weight` | **Calculated** number |

`SeedLots` in `vs_data/fm/vs_tables.py` needs `date_received` and
`current_weight` added.

### Risk: `Current weight` may not come back as a number

Its calculation is:

```
If ( Packed = "yes"; "0";
     (Original weight - Sum(packeting_batches::Total weight)
                      - Sum(Bulk_Batch_Management::Weight)
                      - Sum(large_batches::Total weight) & "g") )
```

The `& "g"` binds to the whole subtraction, so the result is *text* such as
`"350g"` (or `"0"` when the lot is marked packed), even though the field is
declared Number. Two things follow:

1. Nobody knows yet what ODBC returns for it (a number, `350`, `"350g"`, or an
   error). The builder **must check against the real database first** (an
   `fmdb` test or a one-off query), before choosing the parsing.
2. If it is unusable over ODBC or its stored/unstored setting makes it slow in a
   `WHERE`-less select, the fallback is to compute it in Python:
   `Original weight` minus the three child tables (`packeting_batches`,
   `Bulk_Batch_Management`, `large_batches`), with `Packed = "yes"` meaning 0.
   That duplicates FileMaker logic, so prefer reading the field if it works.
   Also decide how to read a blank result (zero is a real value, blank is not).

Whichever route, the display rule is: **0 is grey italic, blank is not.**
Packed lots are the expected source of the zeros.

### Case-insensitive lookup

SKU is text. Compare in FileMaker with `UPPER(sku) = 'ONWL'` if the ODBC driver
allows `UPPER`, otherwise fetch the lots and filter in Python. FileMaker's own
text comparison may already be case-insensitive; the builder should check.
`db.select` takes a raw `where` string, so the SKU must be escaped (double any
single quote) before it goes in; there is no parameter binding. The lot number
path avoided this by requiring an int.

The SKU shown is the one stored in FileMaker (`OnWl`), not what was typed.

## Structure

Follow #132: a query/model in `vs_data/lots/` (e.g. `sku_lots.py`), a route
module beside `lot_routes.py`, and renderers in `lot_page.py` (or a sibling
`sku_page.py` if `lot_page.py` gets unwieldy; it is already 143 lines and the
search script will be shared). The search box and its script currently
hard-code `/lot/`, the field name and a numeric keyboard; parameterise them
(route prefix, field name, placeholder, `inputmode`, and the `lot / sku` toggle) so both pages share one implementation. Exact layout is the builder's call.

## Tests

Default suite, no FileMaker: route against a faked lookup covering found,
case-insensitive match, none found, sort order (including undated last),
zero weight grey italic vs blank weight not, FileMaker down, bad value, JSON
vs HTML, escaping of a SKU containing a quote. An `fmdb` test checks the real
field names and what `Current weight` returns.

## Non-goals

- Editing anything; auth; access from outside the LAN.
- Paging, filtering by status, or showing germination data in the list.
- Searching by crop or partial SKU. (Prefix search would be a natural later
  step; not requested.)
- Any vsdata-doctor change, unless something it relies on moves
  (`src/vs_doctor/CLAUDE.md`).

## Open questions for the owner

1. What should "current weight" mean for a packed lot with a stale
   `Original weight`? I assume 0, as FileMaker's calculation says.
2. (Resolved) #134 is on project 12 "Workflow improvements", Backlog.
