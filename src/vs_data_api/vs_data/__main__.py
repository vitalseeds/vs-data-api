"""
Command-line interface to interact with Vital Seeds database.
"""

import click
from rich import print

from vs_data_api.vs_data import log, orders, products, stock
from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.products import import_wc_product_ids_from_linkdb
from vs_data_api.vs_data.wc import api

# TODO: consider using an orm
# eg sqlalchemy
# https://stackoverflow.com/questions/4493614/sqlalchemy-equivalent-of-pyodbc-connect-string-using-freetds
# https://stackoverflow.com/questions/39955521/sqlalchemy-existing-database-query
# https://docs.sqlalchemy.org/en/14/core/reflection.html


@click.group()
@click.version_option()
@click.option("--isolate", "-i", is_flag=True, envvar="VSDATA_ISOLATE", help="Don't load external services (fm/wc)")
@click.option("--wc-secret", envvar="VSDATA_WC_SECRET", default="")
@click.option("--wc-key", envvar="VSDATA_WC_KEY", default="")
@click.option("--wc-url", envvar="VSDATA_WC_URL", default="")
@click.option("--fmlinkdb", envvar="VSDATA_FM_LINK_CONNECTION_STRING", default="")
@click.option("--fmdb", envvar="VSDATA_FM_CONNECTION_STRING", default="")
@click.pass_context
def cli(ctx, fmdb, fmlinkdb, wc_url, wc_key, wc_secret, isolate):
    """
    Parent to all the commands, sets up FM connection and WC api instance
    """
    ctx.ensure_object(dict)
    if not isolate:
        ctx.obj["fmdb"] = db.connection(fmdb)
        ctx.obj["wcapi"] = api.get_api(wc_url, wc_key, wc_secret, check_status=False)


@cli.command()
@click.argument("product_ids")
@click.pass_context
def get_wc_products(ctx, product_ids):
    """
    Update stock from new batches (regular size packets)
    """
    # fmdb = ctx.parent.obj["fmdb"]
    product_ids = [int(p) for p in product_ids.split(",")]
    wcapi = ctx.parent.obj["wcapi"]
    return stock.get_wc_products_by_id(wcapi, product_ids)


# TODO: import util functions like this from another module and use
# functools.wrap to add to cli group
@cli.command()
@click.option("--large", is_flag=True)
@click.argument("sku")
@click.pass_context
def get_wc_stock(ctx, sku: str, large: bool = False):
    """
    Get WooCommerce stock value
    """
    if large:
        log.debug("large stock count not implemented yet")
    fmdb = ctx.parent.obj["fmdb"]
    wcapi = ctx.parent.obj["wcapi"]
    acquisitions = (
        fmdb.cursor()
        .execute(
            "SELECT wc_product_id, wc_variation_lg_id FROM ACQUISITIONS "
            f"WHERE wc_product_id IS NOT NULL AND sku = '{sku}'"
        )
        .fetchall()
    )
    if not acquisitions:
        log.debug("No acquisitions found")
        return
    product_ids = [p["wc_product_id"] for p in acquisitions]
    wc_products = stock.get_wc_products_by_id(wcapi, product_ids)
    if wc_products:
        wc_product_stock = {p["id"]: p["stock_quantity"] for p in wc_products}
        log.debug(wc_product_stock)
        return
    log.debug("No WC product found")


@cli.command()
@click.pass_context
def update_stock(ctx):
    """
    Update stock from new batches (regular size packets)
    """
    fmdb = ctx.parent.obj["fmdb"]
    wcapi = ctx.parent.obj["wcapi"]
    stock.update_wc_stock_for_new_batches(fmdb, wcapi)


@cli.command()
@click.option("--force", is_flag=True)
@click.pass_context
def update_stock_large_packets(ctx, force):
    """
    Update stock from new 'large packet' batches
    """
    fmdb = ctx.parent.obj["fmdb"]
    wcapi = ctx.parent.obj["wcapi"]

    batches = stock.get_large_batches_awaiting_upload_join_acq(fmdb)
    if not batches:
        log.debug("nothing to upload")
        return
    log.debug(batches)
    confirm = input("Would you like to upload the stock from these batches? (Y/n)")
    if confirm.lower() == "y" or force:
        stock.update_wc_stock_for_new_batches(fmdb, wcapi, product_variation="large")


@cli.command()
@click.pass_context
def import_wc_product_ids(ctx):
    """
    Query the link db for wc product ids and add to the vs_db acquisitions table (based on sku)
    """
    vsdb = ctx.parent.obj["fmdb"]
    linkdb = db.connection(ctx.parent.params["fmlinkdb"])

    import_wc_product_ids_from_linkdb(vsdb, linkdb, cli=True)


@cli.command()
@click.option("--uncache", is_flag=True, help="Delete pickled results from previous run")
@click.pass_context
def stock_csv(ctx, uncache):
    """
    Generate a CSV of stock values from filemaker and woocommerce.

    By default this will run once and cache the expensive wcapi request data and
    fm query results.

    To clear cache and run afresh call with '--uncache' flag.
    """
    fmdb = ctx.parent.obj.get("fmdb")
    wcapi = ctx.parent.obj.get("wcapi") or exit(1)

    stock.compare_wc_fm_stock(fmdb, wcapi, cli=True, uncache=uncache)


@cli.command()
@click.option("--status", default="completed", help="Status to set on WooCommerce order")
@click.pass_context
def update_order_status(ctx, status):
    """
    Mark packed order as completed in woocommerce
    """
    # fmdb = ctx.parent.obj.get("fmdb")
    fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])
    wcapi = ctx.parent.obj.get("wcapi") or exit(1)

    orders.update_packed_orders_status(fmlinkdb, wcapi, cli=True, status=status)


@cli.command()
@click.pass_context
def apply_stock_corrections(ctx):
    """
    Get stock corrections from filemaker, push to WooCommerce.

    Fetch new stock value and update Filemaker stock table.
    """
    fmdb = ctx.parent.obj.get("fmdb")
    wcapi = ctx.parent.obj.get("wcapi") or exit(1)
    with fmdb:
        stock.apply_corrections_to_wc_stock(fmdb, wcapi, cli=True)


@cli.command()
# @click.option(
#     "--status",
#     default="completed",
#     help="Use sku from regular product variations to replace lg var skus that have been lowercased",
# )
@click.pass_context
def push_variation_prices(ctx):
    """
    Push prices for product variations from local database to WC (overwrite)
    """
    fmdb = ctx.parent.obj.get("fmdb")
    # fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])
    wcapi = ctx.parent.obj.get("wcapi")

    products.push_variation_prices_to_wc(wcapi, fmdb, cli=True)


@cli.command()
@click.option("--fetchall", is_flag=True, help="Commit SQL query results ")
@click.option("--commit", is_flag=True, help="Commit SQL query results ")
@click.option("--csv", is_flag=True, help="Commit SQL query results ")
@click.argument("sql")
@click.pass_context
def run_sql(ctx, sql: str, commit: bool, fetchall=False):
    """
    Run arbitrary SQL
    """
    fmdb = ctx.parent.obj.get("fmdb")

    with fmdb:
        log.debug(sql)
        results = fmdb.cursor().execute(sql)
        # Only relevant for a select query
        if fetchall:
            log.debug(results.fetchall())

            return
        log.debug(results)
        if commit:
            fmdb.commit()


@cli.command()
@click.pass_context
def test_fm(ctx):
    """
    Test FileMaker connection
    """
    log.debug("Testing FileMaker connection")
    # fmdb = ctx.parent.obj["fmdb"]


@cli.command()
@click.option("--order-id", type=int, help="Order id to export")
@click.pass_context
def export_wholesale_orders(ctx, order_id: int):
    """
    Export wholesale orders as CSV for import into Xero
    """

    fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])
    orders.wholesale.export_wholesale_orders(fmlinkdb, order_id, cli=True)


if __name__ == "__main__":
    cli()
