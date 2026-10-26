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
.test{border-top:1px solid #ddd;padding:.5rem 0}.test small{color:#555;display:block;font-weight:400}
"""


def _page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head>"
        f"<body>{body}</body></html>"
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
    when = "no date" if test.date is None else test.date.isoformat()
    result = "in progress" if test.result is None else format_result(test.result)
    details = [f"{escape(test.seed_count)} seeds"] if test.seed_count else []
    if test.notes:
        details.append(escape(test.notes))
    extra = f"<small>{' · '.join(details)}</small>" if details else ""
    return f'<div class="test"><strong>{when}</strong> {escape(result)}{extra}</div>'


def _germ_tests(tests) -> str:
    lines = "".join(_test_line(t) for t in tests) or "<p>No germination tests yet</p>"
    return f"<h2>Germination tests</h2>{lines}"


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
        + '<p><a href="/lot">Look up another lot</a></p>'
    )
    return _page(f"Lot {summary.lot_number}", body)


def render_form() -> str:
    body = (
        "<h1>Find a lot</h1>"
        '<form action="/lot" method="get">'
        '<input name="lot_number" type="number" inputmode="numeric" placeholder="Lot number" autofocus>'
        "<button>Show lot</button></form>"
    )
    return _page("Find a lot", body)


def render_message(title: str, message: str) -> str:
    return _page(title, f"<h1>{escape(title)}</h1><p>{escape(message)}</p>" '<p><a href="/lot">Look up a lot</a></p>')
