"""HTML for the lot summary page. Small and phone-friendly, no templating dependency."""

from html import escape

NOT_RECORDED = "not recorded"

_STYLE = """
body{font-family:system-ui,sans-serif;margin:0;padding:1rem;font-size:1.1rem;line-height:1.4}
form{margin-bottom:1rem}
h1{font-size:clamp(2.5rem,14vw,4rem);line-height:1.1;margin:0 0 1rem}
dl.fields{display:grid;grid-template-columns:1fr 1fr;gap:.2rem 1rem;margin:0}
dt{color:#555;font-size:.9rem;margin-top:.8rem}dd{margin:0;font-weight:600;overflow-wrap:anywhere}
input{font-size:1.1rem;padding:.5rem;margin:.3rem 0;width:100%;box-sizing:border-box}
.missing{color:#999;font-weight:400}
h2{font-size:1.2rem;margin:1.5rem 0 .5rem}
.notes-link{display:inline-block;width:1.5rem;height:1.5rem;line-height:1.5rem;text-align:center;border-radius:50%;background:#fff;color:#333;text-decoration:none;font-weight:600}
dialog{max-width:90vw;border:0;border-radius:.5rem;padding:1rem}dialog::backdrop{background:rgba(0,0,0,.4)}
#notes-text{white-space:pre-wrap;margin:0 0 1rem}
.germination{background:#eee;border-radius:.5rem;padding:.1rem 1rem .5rem;margin-top:1.5rem}
.germination h2{margin-top:.8rem}
table{width:100%;border-collapse:collapse}
th{color:#555;font-size:.9rem;font-weight:400;text-align:left}
th,td{padding:.4rem .5rem .4rem 0;border-top:1px solid #ccc;vertical-align:top}
.num{text-align:right;padding-right:0}td.num{font-weight:600;white-space:nowrap}
td.date{white-space:nowrap}
dd.big{font-size:1.8rem;line-height:1.2}
"""


# Looks the lot up once typing pauses and swaps in just the result, so the box keeps focus.
# Without JavaScript the form still works: it submits to /lot, which redirects.
_SEARCH_SCRIPT = """
const notes = document.getElementById('notes');
document.addEventListener('click', (event) => {
  const link = event.target.closest('[data-notes]');
  if (!link) return;
  event.preventDefault();
  document.getElementById('notes-text').textContent = link.dataset.notes;
  notes.showModal();
});
const box = document.querySelector('[name=lot_number]');
let timer;
box.addEventListener('input', () => {
  clearTimeout(timer);
  const lot = box.value.trim();
  if (!lot) return;
  timer = setTimeout(async () => {
    try {
      const page = new DOMParser().parseFromString(await (await fetch('/lot/' + encodeURIComponent(lot))).text(), 'text/html');
      document.getElementById('result').innerHTML = page.getElementById('result').innerHTML;
      document.title = page.title;
      history.replaceState(null, '', '/lot/' + encodeURIComponent(lot));
    } catch (e) {
      document.getElementById('result').textContent = "Couldn't look that up. Check the connection and try again.";
    }
  }, 500);
});
"""


def _search_box(lot_number: str = "") -> str:
    return (
        '<form action="/lot" method="get">'
        '<input name="lot_number" type="search" inputmode="numeric" placeholder="Lot number" '
        f'value="{escape(lot_number)}" autocomplete="off">'
        "</form>"
    )


def _page(title: str, body: str, lot_number: str = "") -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head>"
        f'<body>{_search_box(lot_number)}<div id="result">{body}</div>'
        '<dialog id="notes"><p id="notes-text"></p><form method="dialog"><input type="submit" value="Close"></form></dialog>'
        f"<script>{_SEARCH_SCRIPT}</script></body></html>"
    )


def format_weight(grams: float | None) -> str:
    if grams is None:
        return NOT_RECORDED
    return f"{grams:g} g"


def format_result(percent: float | None) -> str:
    if percent is None:
        return NOT_RECORDED
    return f"{percent:g}%"


def _notes_link(notes: str | None) -> str:
    if not notes:
        return ""
    return f'<a href="#" class="notes-link" data-notes="{escape(notes)}" aria-label="Show notes" title="Show notes">?</a>'


def _test_row(test) -> str:
    when = "no date" if test.date is None else test.date.strftime("%d / %m / %y")
    result = "in progress" if test.result is None else format_result(test.result)
    return (
        f'<tr><td class="date">{when}</td><td>{escape(test.seed_count or "")}</td>'
        f'<td>{_notes_link(test.notes)}</td><td class="num">{escape(result)}</td></tr>'
    )


def _germ_tests(tests) -> str:
    if not tests:
        table = "<p>No germination tests yet</p>"
    else:
        head = '<tr><th>Date</th><th>Seeds</th><th>Notes</th><th class="num">Result</th></tr>'
        table = f"<table>{head}{''.join(_test_row(t) for t in tests)}</table>"
    return f'<div class="germination"><h2>Germination tests</h2>{table}</div>'


def _row(label: str, value: str | None, big: bool = False) -> str:
    shown = f'<span class="missing">{NOT_RECORDED}</span>' if value is None else escape(value)
    css = ' class="big"' if big else ""
    return f"<div><dt>{escape(label)}</dt><dd{css}>{shown}</dd></div>"


def render_lot(summary) -> str:
    weight = None if summary.final_weight_g is None else format_weight(summary.final_weight_g)
    body = (
        f'<h1>#{summary.lot_number}</h1><dl class="fields">'
        + _row("SKU", summary.sku, big=True)
        + _row("Source", summary.source)
        + _row("Weight", weight)
        + _row("Germination result", None if summary.germ_result is None else format_result(summary.germ_result))
        + "</dl>"
        + _germ_tests(summary.germ_tests)
    )
    return _page(f"#{summary.lot_number}", body, str(summary.lot_number))


def render_form() -> str:
    return _page("Find a lot", "")


def render_message(title: str, message: str, lot_number: str = "") -> str:
    body = f"<h1>{escape(title)}</h1><p>{escape(message)}</p>"
    return _page(title, body, lot_number)
