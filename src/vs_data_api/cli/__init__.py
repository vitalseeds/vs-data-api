# SPDX-FileCopyrightText: 2023-present tombola <tombola@github>
#
# SPDX-License-Identifier: MIT
"""
Command-line interface to interact with Vital Seeds database.
"""
import os
from functools import lru_cache

import click
from rich import print

from vs_data_api.__about__ import __version__
from vs_data_api.config import Settings, TestSettings
from vs_data_api.vs_data import log, orders, stock
from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.products import import_wc_product_ids_from_linkdb, price
from vs_data_api.vs_data.wc import api

@lru_cache()
def get_settings():
    """
    Loaded only when a command needs a connection, so --help works without settings.
    """
    # Switch pydantic settings class based on environment variable
    if os.environ.get("TESTING", None) or os.environ.get("HATCH_ENV_ACTIVE", "") == "test":
        return TestSettings()
    return Settings()


class Connections(dict):
    """
    FileMaker connections ("fmdb", "fmlinkdb") and WooCommerce API ("wcapi"), opened on first use.

    Command line options win over settings.
    """

    def __init__(self, options: dict):
        super().__init__()
        self.options = options

    def _option_or_setting(self, option, setting):
        return self.options[option] or getattr(get_settings(), setting)

    def __missing__(self, key):
        if key == "fmdb":
            self[key] = db.connection(self._option_or_setting("fmdb", "fm_connection_string"))
        elif key == "fmlinkdb":
            self[key] = db.connection(self._option_or_setting("fmlinkdb", "fm_link_connection_string"))
        elif key == "wcapi":
            self[key] = api.get_api(
                self._option_or_setting("wc_url", "vsdata_wc_url"),
                self._option_or_setting("wc_key", "vsdata_wc_key"),
                self._option_or_setting("wc_secret", "vsdata_wc_secret"),
                check_status=False,
                verify_ssl=get_settings().vsdata_wc_verify_ssl,
            )
        else:
            raise KeyError(key)
        return self[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


@click.group()
@click.version_option(version=__version__, prog_name="vs-data-api")
@click.option("--isolate", "-i", is_flag=True, envvar="VSDATA_ISOLATE", help="Don't load external services (fm/wc)")
@click.option("--wc-secret", help="Default: VSDATA_WC_SECRET")
@click.option("--wc-key", help="Default: VSDATA_WC_KEY")
@click.option("--wc-url", help="Default: VSDATA_WC_URL")
@click.option("--fmlinkdb", help="Link database connection string. Default: VSDATA_FM_LINK_CONNECTION_STRING")
@click.option("--fmdb", help="Connection string. Default: VSDATA_FM_CONNECTION_STRING")
@click.pass_context
def cli(ctx, fmdb, fmlinkdb, wc_url, wc_key, wc_secret, isolate):
    """
    Parent to all the commands, provides FM connections and WC api instance (opened on first use)
    """
    ctx.ensure_object(dict)
    if not isolate:
        ctx.obj = Connections(ctx.params)


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
    import_wc_product_ids_from_linkdb(ctx.parent.obj["fmdb"], ctx.parent.obj["fmlinkdb"], cli=True)


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
    fmlinkdb = ctx.parent.obj["fmlinkdb"]
    wcapi = ctx.parent.obj.get("wcapi") or exit(1)

    try:
        orders.update_packed_orders_status(fmlinkdb, wcapi, cli=True, target_status=status)
    except orders.OrderUpdateFailed as e:
        raise click.ClickException(str(e))


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
    # fmlinkdb = ctx.parent.obj["fmlinkdb"]
    wcapi = ctx.parent.obj.get("wcapi")

    price.push_variation_prices_to_wc(wcapi, fmdb, cli=True)


@cli.command()
@click.option("--link", is_flag=True, help="Run against WC link database")
@click.option("--fetchall", is_flag=True, help="Commit SQL query results ")
@click.option("--csv", "csv_file", help="Filename to save SQL query results as CSV")
@click.option("--commit", is_flag=True, help="Commit SQL query results ")
@click.argument("sql")
@click.pass_context
def run_sql(ctx, sql: str, commit: bool, csv_file: str, fetchall=False, link: bool = False):
    """
    Run arbitrary SQL
    """

    fmdb = ctx.parent.obj["fmlinkdb"] if link else ctx.parent.obj.get("fmdb")
    with fmdb:
        log.debug(sql)
        results = fmdb.cursor().execute(sql)
        # Only relevant for a select query
        if fetchall:
            rows = results.fetchall()
            log.debug(rows)
            if csv_file:
                import csv
                with open(csv_file, "w") as f:
                    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, escapechar="\\")
                    writer.writerows(rows)
            return
        log.debug(results)
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
            fmlinkdb = ctx.parent.obj["fmlinkdb"]
            if fmlinkdb:
                log.debug("Link database connection OK")
                return
        except Exception:
            ...
        log.debug("Link database connection failed")
        return

    try:
        fmdb = ctx.parent.obj["fmdb"]
        if fmdb:
            log.debug("FileMaker connection OK")
            return
    except Exception:
        ...
    log.debug("No FileMaker connection")
    return


@cli.command()
@click.option("--order-id", type=int, help="Order id to export")
@click.pass_context
def export_wholesale_orders(ctx, order_id: int):
    """
    Export wholesale orders as CSV for import into Xero
    """

    fmlinkdb = ctx.parent.obj["fmlinkdb"]
    orders.wholesale.export_wholesale_orders(fmlinkdb, order_id, cli=True)


if __name__ == "__main__":
    cli()
