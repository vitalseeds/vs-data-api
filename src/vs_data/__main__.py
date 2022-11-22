"""Command-line interface."""
import click
from vs_data.utils.fm import db
from rich import print
from vs_data import stock
from vs_data.utils import cli


@click.group()
@click.version_option()
@click.option("--fmdb", envvar="VSDATA_FM_CONNECTION_STRING", default="")
@click.pass_context
def cli(ctx, fmdb):
    ctx.ensure_object(dict)
    ctx.obj["fmdb"] = db.connection(fmdb)


@cli.command()
@click.pass_context
def update_stock(ctx):
    fmdb = ctx.parent.obj["fmdb"]
    stock.update_wc_stock_from_batch(fmdb)


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
