# SPDX-FileCopyrightText: 2023-present tombola <tombola@github>
#
# SPDX-License-Identifier: MIT
"""
Command-line interface to interact with Vital Seeds database.
"""
import os

import click
from rich import print

from vs_data_api import config
from vs_data_api.__about__ import __version__
from vs_data_api.vs_data import orders, products, stock
from vs_data_api.vs_data.fm import constants, db
from vs_data_api.vs_data.wc import api

# Switch pydantic settings class based on environment variable
settings = config.get_env_settings()


VSDATA_FM_CONNECTION_STRING = settings.fm_connection_string
VSDATA_FM_LINK_CONNECTION_STRING = settings.fm_link_connection_string
VSDATA_WC_SECRET = settings.vsdata_wc_secret
VSDATA_WC_KEY = settings.vsdata_wc_key
VSDATA_WC_URL = settings.vsdata_wc_url


@click.group()
@click.version_option(version=__version__, prog_name="vs-data-api")
@click.option("--isolate", "-i", is_flag=True, envvar="VSDATA_ISOLATE", help="Don't load external services (fm/wc)")
@click.option("--wc-secret", default=VSDATA_WC_SECRET)
@click.option("--wc-key", default=VSDATA_WC_KEY)
@click.option("--wc-url", default=VSDATA_WC_URL)
@click.option("--fmlinkdb", default=VSDATA_FM_LINK_CONNECTION_STRING)
@click.option("--fmdb", default=VSDATA_FM_CONNECTION_STRING)
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
        print("large stock count not implemented yet")
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
        print("No acquisitions found")
        return
    product_ids = [p["wc_product_id"] for p in acquisitions]
    wc_products = stock.get_wc_products_by_id(wcapi, product_ids)
    if wc_products:
        wc_product_stock = {p["id"]: p["stock_quantity"] for p in wc_products}
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
    confirm = input("Would you like to upload the stock from these batches? (Y/n)")
    if confirm.lower() == "y" or force:
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
@click.option("--link", is_flag=True, help="Run against WC link database")
@click.option("--fetchall", is_flag=True, help="Commit SQL query results ")
@click.option("--commit", is_flag=True, help="Commit SQL query results ")
@click.argument("sql")
@click.pass_context
def run_sql(ctx, sql: str, commit: bool, fetchall=False, link: bool=False):
    """
    Run arbitrary SQL
    """

    fmdb = db.connection(ctx.parent.params["fmlinkdb"]) if link else ctx.parent.obj.get("fmdb")
    with fmdb:
        print(sql)
        results = fmdb.cursor().execute(sql)
        # Only relevant for a select query
        if fetchall:
            print(results.fetchall())
            return
        print(results)
        if commit:
            fmdb.commit()
    return


@cli.command()
@click.option("--link", is_flag=True, help="Check WC link database")
@click.pass_context
def test_fm(ctx, link: bool):
    """
    Test FileMaker connection
    """
    if link:
        try:
            fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])
            if fmlinkdb:
                print("Link database connection OK")
                return
        except Exception:
            ...
        print("Link database connection failed")
        return

    try:
        fmdb = ctx.parent.obj["fmdb"]
        if fmdb:
            print("FileMaker connection OK")
            return
    except Exception:
        ...
    print("No FileMaker connection")
    return



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
