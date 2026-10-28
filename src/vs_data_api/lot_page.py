"""HTML for the lot summary page. Small and phone-friendly, no templating dependency."""

from html import escape
from urllib.parse import quote

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
table{width:100%;max-width:768px;border-collapse:collapse}
th{color:#555;font-size:.9rem;font-weight:400;text-align:left}
th,td{padding:.4rem .5rem .4rem 0;border-top:1px solid #ccc;vertical-align:top}
.num{text-align:right;padding-right:0}td.num{font-weight:600;white-space:nowrap}
td.date{white-space:nowrap}
.num+.num{padding-left:1rem}
dd.big{font-size:1.8rem;line-height:1.2}
h1+.sub{margin:-.6rem 0 1rem;font-size:1.1rem;font-weight:400;color:#555}
.search{display:flex;align-items:center;gap:1rem;margin-bottom:1rem}
.search form{flex:1;margin:0}
a{text-decoration:none}
dd a{color:inherit}
.switch{white-space:nowrap;color:#333;text-decoration:none}
.switch i{color:#999}
.used td{color:#999;font-style:italic;background:aliceblue}
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
const prefix = '__PREFIX__';
const box = document.querySelector('.search input');
let timer;
box.addEventListener('input', () => {
  clearTimeout(timer);
  const lot = box.value.trim();
  if (!lot) return;
  timer = setTimeout(async () => {
    try {
      const page = new DOMParser().parseFromString(await (await fetch(prefix + '/' + encodeURIComponent(lot))).text(), 'text/html');
      document.getElementById('result').innerHTML = page.getElementById('result').innerHTML;
      document.title = page.title;
      history.replaceState(null, '', prefix + '/' + encodeURIComponent(lot));
    } catch (e) {
      document.getElementById('result').textContent = "Couldn't look that up. Check the connection and try again.";
    }
  }, 500);
});
"""


class _Search:
    """What differs between the lot search and the SKU search: where it goes and what it takes."""

    def __init__(self, route: str, field: str, placeholder: str, inputmode: str, other: str):
        self.route, self.field, self.placeholder, self.inputmode, self.other = route, field, placeholder, inputmode, other

    @property
    def name(self) -> str:
        return self.route.lstrip("/")


LOT = _Search("/lot", "lot_number", "Lot number", "numeric", "/sku")
SKU = _Search("/sku", "sku", "SKU", "text", "/lot")


def _switch(search: _Search) -> str:
    """`lot / sku` link to the other search. The word for the current page is bold, the other grey italic."""
    lot, sku = ("<b>lot</b>", "<i>sku</i>") if search is LOT else ("<i>lot</i>", "<b>sku</b>")
    return f'<a class="switch" href="{search.other}" title="Switch search">{lot} / {sku}</a>'


def _search_box(search: _Search, value: str = "") -> str:
    extra = ' autocapitalize="off" spellcheck="false"' if search is SKU else ""
    return (
        '<div class="search">'
        f'<form action="{search.route}" method="get">'
        f'<input name="{search.field}" type="search" inputmode="{search.inputmode}" placeholder="{search.placeholder}" '
        f'value="{escape(value)}" autocomplete="off"{extra}>'
        "</form>"
        f"{_switch(search)}</div>"
    )


def _page(title: str, body: str, value: str = "", search: _Search = LOT) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head>"
        f'<body>{_search_box(search, value)}<div id="result">{body}</div>'
        '<dialog id="notes"><p id="notes-text"></p><form method="dialog"><input type="submit" value="Close"></form></dialog>'
        f"<script>{_SEARCH_SCRIPT.replace('__PREFIX__', search.route)}</script></body></html>"
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


def _row(label: str, value: str | None, big: bool = False, href: str | None = None) -> str:
    shown = f'<span class="missing">{NOT_RECORDED}</span>' if value is None else escape(value)
    if href and value is not None:
        shown = f'<a href="{escape(href)}">{shown}</a>'
    css = ' class="big"' if big else ""
    return f"<div><dt>{escape(label)}</dt><dd{css}>{shown}</dd></div>"


def render_lot(summary) -> str:
    weight = None if summary.final_weight_g is None else format_weight(summary.final_weight_g)
    sku_href = None if summary.sku is None else "/sku/" + quote(summary.sku, safe="")
    body = (
        f'<h1>#{summary.lot_number}</h1><dl class="fields">'
        + _row("SKU", summary.sku, big=True, href=sku_href)
        + _row("Source", summary.source)
        + _row("Weight", weight)
        + _row("Germination result", None if summary.germ_result is None else format_result(summary.germ_result))
        + "</dl>"
        + _germ_tests(summary.germ_tests)
    )
    return _page(f"#{summary.lot_number}", body, str(summary.lot_number))


def render_form(search: _Search = LOT) -> str:
    return _page("Find a lot" if search is LOT else "Find a SKU", "", search=search)


def render_message(title: str, message: str, value: str = "", search: _Search = LOT) -> str:
    body = f"<h1>{escape(title)}</h1><p>{escape(message)}</p>"
    return _page(title, body, value, search)


def _sku_row(lot) -> str:
    when = "no date" if lot.date_received is None else lot.date_received.strftime("%d / %m / %y")
    current = NOT_RECORDED if lot.current_weight_g is None else format_weight(lot.current_weight_g)
    initial = NOT_RECORDED if lot.initial_weight_g is None else format_weight(lot.initial_weight_g)
    used = ' class="used"' if lot.current_weight_g == 0 else ""  # 0 is used up; unknown is not
    return (
        f'<tr{used}><td><a href="/lot/{lot.lot_number}">#{lot.lot_number}</a></td>'
        f'<td class="date">{when}</td><td class="num">{escape(initial)}</td><td class="num">{escape(current)}</td></tr>'
    )


def render_sku(sku_lots) -> str:
    head = '<tr><th>Lot</th><th>Received</th><th class="num">Initial</th><th class="num">Current</th></tr>'
    what = " · ".join(part for part in (sku_lots.crop, sku_lots.variety) if part)
    sub = f'<h2 class="sub">{escape(what)}</h2>' if what else ""
    body = f"<h1>{escape(sku_lots.sku)}</h1>{sub}<table>{head}{''.join(_sku_row(lot) for lot in sku_lots.lots)}</table>"
    return _page(sku_lots.sku, body, sku_lots.sku, SKU)
