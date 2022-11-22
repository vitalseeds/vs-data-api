"""
Command-line interface to interact with Vital Seeds database.
"""
# TODO: consider using an orm
# eg sqlalchemy
# https://stackoverflow.com/questions/4493614/sqlalchemy-equivalent-of-pyodbc-connect-string-using-freetds
# https://stackoverflow.com/questions/39955521/sqlalchemy-existing-database-query
# https://docs.sqlalchemy.org/en/14/core/reflection.html
import click
from vs_data.utils.fm import db
from vs_data.utils.wc import api
from rich import print
from vs_data import stock
from vs_data.utils import cli


@click.group()
@click.version_option()
@click.option("--wc-secret", envvar="VSDATA_WC_SECRET", default="")
@click.option("--wc-key", envvar="VSDATA_WC_KEY", default="")
@click.option("--wc-url", envvar="VSDATA_WC_URL", default="")
@click.option("--fmdb", envvar="VSDATA_FM_CONNECTION_STRING", default="")
@click.pass_context
def cli(ctx, fmdb, wc_url, wc_key, wc_secret):
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
    stock.update_wc_stock_from_batch(fmdb, wcapi)


@cli.command()
@click.pass_context
def stock_count(ctx):
    wcapi = ctx.parent.obj["wcapi"]
    stock.get_wp_product_by_sku(wcapi)


# @cli.command()
# @click.argument("sql", type=click.STRING)
# @click.pass_context
# def sql(ctx, sql):
#     """
#     has issues with escaping the quoted table/field names in SQL string
#     """
#     fmdb = ctx.parent.obj["fmdb"]
#     rows = fmdb.execute(sql).fetchall()
#     cli.display_table([], rows, float_to_int=False)


if __name__ == "__main__":
    cli()
