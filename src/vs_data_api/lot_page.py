"""HTML for the lot summary page. Small and phone-friendly, no templating dependency."""

from html import escape

NOT_RECORDED = "not recorded"

_STYLE = """
body{font-family:system-ui,sans-serif;margin:0;padding:1rem;font-size:1.1rem;line-height:1.4}
h1{font-size:1.5rem;margin:0 0 1rem}
dl{margin:0}dt{color:#555;font-size:.9rem;margin-top:.8rem}dd{margin:0;font-weight:600}
input,button{font-size:1.1rem;padding:.5rem;margin:.3rem .3rem .3rem 0}
.missing{color:#999;font-weight:400}
h2{font-size:1.2rem;margin:1.5rem 0 .5rem}
.germination{background:#eee;border-radius:.5rem;padding:.1rem 1rem .5rem;margin-top:1.5rem}
.germination h2{margin-top:.8rem}
.test{border-top:1px solid #ccc;padding:.5rem 0}.test small{color:#555;display:block;font-weight:400}
"""


# Looks the lot up once typing pauses and swaps in just the result, so the box keeps focus.
# Without JavaScript the form still works: it submits to /lot, which redirects.
_SEARCH_SCRIPT = """
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
        "<button>Show lot</button></form>"
    )


def _page(title: str, body: str, lot_number: str = "") -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head>"
        f'<body>{_search_box(lot_number)}<div id="result">{body}</div>'
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


def _test_line(test) -> str:
    when = "no date" if test.date is None else test.date.strftime("%d/%m/%Y")
    result = "in progress" if test.result is None else format_result(test.result)
    details = [f"{escape(test.seed_count)} seeds"] if test.seed_count else []
    if test.notes:
        details.append(escape(test.notes))
    extra = f"<small>{' · '.join(details)}</small>" if details else ""
    return f'<div class="test"><strong>{when}</strong> {escape(result)}{extra}</div>'


def _germ_tests(tests) -> str:
    lines = "".join(_test_line(t) for t in tests) or "<p>No germination tests yet</p>"
    return f'<div class="germination"><h2>Germination tests</h2>{lines}</div>'


def _row(label: str, value: str | None) -> str:
    shown = f'<span class="missing">{NOT_RECORDED}</span>' if value is None else escape(value)
    return f"<dt>{escape(label)}</dt><dd>{shown}</dd>"


def render_lot(summary) -> str:
    weight = None if summary.final_weight_g is None else format_weight(summary.final_weight_g)
    body = (
        f"<h1>Lot {summary.lot_number}</h1><dl>"
        + _row("SKU", summary.sku)
        + _row("Source", summary.source)
        + _row("Weight", weight)
        + _row("Germination result", None if summary.germ_result is None else format_result(summary.germ_result))
        + "</dl>"
        + _germ_tests(summary.germ_tests)
    )
    return _page(f"Lot {summary.lot_number}", body, str(summary.lot_number))


def render_form() -> str:
    return _page("Find a lot", "")


def render_message(title: str, message: str, lot_number: str = "") -> str:
    body = f"<h1>{escape(title)}</h1><p>{escape(message)}</p>"
    return _page(title, body, lot_number)
