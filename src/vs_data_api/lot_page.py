"""HTML for the lot summary page. Small and phone-friendly, no templating dependency."""

from html import escape

NOT_RECORDED = "not recorded"

_STYLE = """
body{font-family:system-ui,sans-serif;margin:0;padding:1rem;font-size:1.1rem;line-height:1.4}
h1{font-size:1.5rem;margin:0 0 1rem}
dl{margin:0}dt{color:#555;font-size:.9rem;margin-top:.8rem}dd{margin:0;font-weight:600}
input,button{font-size:1.1rem;padding:.5rem;margin:.3rem .3rem .3rem 0}
.missing{color:#999;font-weight:400}
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
        + '</dl><p><a href="/lot">Look up another lot</a></p>'
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
