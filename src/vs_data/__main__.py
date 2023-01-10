"""
Command-line interface to interact with Vital Seeds database.
"""
import os

import click
from rich import print

from vs_data import stock
from vs_data.utils.cli import display_product_table
from vs_data.utils.fm import constants
from vs_data.utils.fm import db
from vs_data.utils.wc import api


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
def stock_count(ctx):
    wcapi = ctx.parent.obj["wcapi"]
    products = stock.get_products_in_stock(wcapi).json()
    print([p["id"] for p in products])


@cli.command()
@click.pass_context
def products(ctx):
    wcapi = ctx.parent.obj["wcapi"]
    ids = [43121, 10691, 10411, 10350, 10351, 10279, 10272, 10273, 10274, 10275]
    display_product_table(stock.get_products_by_id(wcapi, ids))


@cli.command()
@click.pass_context
def test_fm_call(ctx):
    # Append-adds at last
    if not os.path.exists(os.path.expanduser("~/.vs-data")):
        os.mkdir(os.path.expanduser("~/.vs-data"))
    file_path = os.path.expanduser("~/.vs-data/test_output.txt")
    with open(file_path, "a") as file:
        file.write("FM ran cli command")
        print(f"wrote to {file_path}")
        file.close()


@cli.command()
@click.argument("file", required=False)
@click.pass_context
def runsql(ctx, file):
    fmdb = ctx.parent.obj["fmdb"]
    # wcapi = ctx.parent.obj["wcapi"]
    file = file or "example"
    sql_file_path = f"src/vs_data/utils/fm/queries/{file}.sql"
    with open(sql_file_path, "r") as sqlfile:
        query = sqlfile.read()
        print(fmdb.execute(query).fetchall())


@cli.command()
@click.pass_context
def get_wc_product_ids(ctx):
    wcapi = ctx.parent.obj["wcapi"]
    fmdb = ctx.parent.obj["fmdb"]


@cli.command()
@click.pass_context
def import_wc_product_ids(ctx):
    """
    Query the link db for wc product ids and add to the vs_db acquisitions table (based on sku)
    """
    wcapi = ctx.parent.obj["wcapi"]
    fmdb = ctx.parent.obj["fmdb"]
    fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])

    # Get the WC:product_id for each SKU from the link database
    regular_product_skus = stock.get_product_sku_map_from_linkdb(fmlinkdb)
    print(regular_product_skus[:10])

    # Get acquisitions from vs_db
    # aquisitions = stock.get_acquisitions_sku_map_from_vsdb(fmdb)
    # print(aquisitions[:10])

    # Update acquisitions with wc_product_id
    stock.update_acquisitions_wc_id(fmdb, regular_product_skus)


# @cli.command()
# @click.pass_context
# def get_wc_variation_ids(ctx):
#     """
#     large_batches
#     """
#     wcapi = ctx.parent.obj["wcapi"]
#     fmdb = ctx.parent.obj["fmdb"]
#     fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])


# @cli.command()
# @click.argument("sql", type=click.STRING)
# @click.pass_context
# def debug_sql(ctx, sql):
#     """
#     has issues with escaping the quoted table/field names in SQL string
#     """
#     fmdb = ctx.parent.obj["fmdb"]
#     rows = fmdb.execute(sql).fetchall()
#     cli.display_table([], rows, float_to_int=False)


if __name__ == "__main__":
    cli()
