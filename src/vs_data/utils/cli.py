from rich.console import Console
from rich.table import Table

COLOURS = (
    "green",
    "magenta",
    "cyan",
    "green",
    "magenta",
    "cyan",
    "green",
    "magenta",
    "cyan",
)
RAINBOW = True


def display_table(headers, rows, title=None, float_to_int=True):
    table = Table(title=title)

    for i, header in enumerate(headers):
        if RAINBOW:
            table.add_column(header, no_wrap=True, style=COLOURS[i])
        else:
            table.add_column(header, no_wrap=True)

    # table.add_column("Released", justify="right", style="cyan", no_wrap=True)
    # table.add_column("Title", style="magenta")
    # table.add_column("Box Office", justify="right", style="green")

    for row in rows:
        if float_to_int:
            row = [int(v) if isinstance(v, float) else v for v in row]

        row = [str(v) for v in row]
        # table.add_row(*rows)
        table.add_row(*row)

    # table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
    # table.add_row("Dec 15, 2017", "Star Wars Ep. V111: The Last Jedi", "$1,332,539,889")
    # table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

    console = Console()
    console.print(table)


def display_product_table(products, fields=["id", "sku", "stock_quantity"]):
    if hasattr(products, "json"):
        products = products.json()

    rows = []
    for product in products:
        rows.append([product[f] for f in fields])

    display_table(fields, rows)
