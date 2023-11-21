"""
Command-line interface to interact with Vital Seeds database.
"""
import os

import click
from rich import print

from vs_data import stock
from vs_data import orders
from vs_data import products
from vs_data.fm import constants
from vs_data.fm import db
from vs_data.wc import api


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
@click.argument('product_ids')
@click.pass_context
def get_wc_products(ctx, product_ids):
    """
    Update stock from new batches (regular size packets)
    """
    fmdb = ctx.parent.obj["fmdb"]
    product_ids = [int(p) for p in product_ids.split(',')]
    wcapi = ctx.parent.obj["wcapi"]
    return stock.get_wc_products_by_id(wcapi, product_ids)

# TODO: import util functions like this from another module and use
# functools.wrap to add to cli group
@cli.command()
@click.option("--large", is_flag=True)
@click.argument('sku')
@click.pass_context
def get_wc_stock(ctx, sku:str, large:bool=False):
    """
    Get WooCommerce stock value
    """
    if large:
        print("large stock count not implemented yet")
    fmdb = ctx.parent.obj["fmdb"]
    wcapi = ctx.parent.obj["wcapi"]
    acquisitions = fmdb.cursor().execute(
        "SELECT wc_product_id, wc_variation_lg_id FROM ACQUISITIONS "
        f"WHERE wc_product_id IS NOT NULL AND sku = '{sku}'"
    ).fetchall()
    if not acquisitions:
        print("No acquisitions found")
        return
    product_ids = [p["wc_product_id"] for p in acquisitions]
    wc_products = stock.get_wc_products_by_id(wcapi, product_ids)
    if wc_products:
        wc_product_stock = {p["id"]:p["stock_quantity"] for p in wc_products}
        print(wc_product_stock)
        return
    print("No WC product found")


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
        print("nothing to upload")
        return
    print(batches)
    confirm = input('Would you like to upload the stock from these batches? (Y/n)')
    if confirm.lower() == 'y' or force:
        stock.update_wc_stock_for_new_batches(fmdb, wcapi, product_variation="large")


@cli.command()
@click.pass_context
def import_wc_product_ids(ctx):
    """
    Query the link db for wc product ids and add to the vs_db acquisitions table (based on sku)
    """
    fmdb = ctx.parent.obj["fmdb"]
    fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])

    # Get the WC:product_id for each SKU from the link database
    regular_product_skus = stock.get_product_sku_map_from_linkdb(fmlinkdb)
    print(regular_product_skus[:10])

    # Update acquisitions with wc_product_id
    stock.update_acquisitions_wc_id(fmdb, regular_product_skus)


    # Get the WC:variation_id for each SKU from the link database
    variations = stock.get_product_variation_map_from_linkdb(fmlinkdb)
    print(variations[:10])

    # Update acquisitions with WC variation ids for large and regular packets
    stock.update_acquisitions_wc_variations(fmdb, variations)


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
@click.argument('sql')
@click.pass_context
def run_sql(ctx, sql:str, commit:bool, fetchall=False):
    """
    Run arbitrary SQL
    """
    fmdb = ctx.parent.obj.get("fmdb")
    # cursor = fmdb.cursor()
    print(sql)

    results = fmdb.cursor().execute(sql)
    # Only relevant for a select query
    if fetchall:
        print(results.fetch_all())
        return
    print(results)
    if commit:
        fmdb.commit()


@cli.command()
@click.pass_context
def test_fm(ctx):
    """
    Test FileMaker connection
    """
    fmdb = ctx.parent.obj["fmdb"]


if __name__ == "__main__":
    cli()
