"""
Command-line interface to interact with Vital Seeds database.
"""
import os

import click
from rich import print

from vs_data import stock
from vs_data.cli.table import display_product_table
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
@click.option("--wc-secret", envvar="VSDATA_WC_SECRET", default="")
@click.option("--wc-key", envvar="VSDATA_WC_KEY", default="")
@click.option("--wc-url", envvar="VSDATA_WC_URL", default="")
@click.option("--fmlinkdb", envvar="VSDATA_FM_LINK_CONNECTION_STRING", default="")
@click.option("--fmdb", envvar="VSDATA_FM_CONNECTION_STRING", default="")
@click.pass_context
def cli(ctx, fmdb, fmlinkdb, wc_url, wc_key, wc_secret):
    """
    Parent to all the commands, sets up FM connection and WC api instance
    """
    ctx.ensure_object(dict)
    ctx.obj["fmdb"] = db.connection(fmdb)
    ctx.obj["wcapi"] = api.get_api(wc_url, wc_key, wc_secret)


@cli.command()
@click.pass_context
def update_stock(ctx):
    fmdb = ctx.parent.obj["fmdb"]
    wcapi = ctx.parent.obj["wcapi"]
    stock.update_wc_stock_for_new_batches(fmdb, wcapi)


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


if __name__ == "__main__":
    cli()
