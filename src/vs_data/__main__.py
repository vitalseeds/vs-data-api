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
from vs_data.utils.cli import display_product_table
import os


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
    stock.update_wc_stock_from_batch(fmdb, wcapi)


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
def push_skus_to_wc(ctx):
    ctx.parent.params["fmlinkdb"]
    print(ctx.parent.params["fmlinkdb"])
    print(type(ctx.parent.params["fmlinkdb"]))
    # print(db.construct_db_connection_string("link_db", "vs_data", "1234"))
    fmlinkdb = db.connection(ctx.parent.params["fmlinkdb"])
    print(type(fmlinkdb))

    from vs_data.woocommerce import (
        get_product_sku_map_from_linkdb,
        get_product_variation_sku_map_from_linkdb,
    )

    product_skus = get_product_sku_map_from_linkdb(fmlinkdb)
    print(len(product_skus))
    variation_skus = get_product_variation_sku_map_from_linkdb(fmlinkdb)
    print(len(variation_skus))

    print(product_skus[0])
    print(variation_skus[0])

    # overlaps = []
    # for p in product_skus:
    #     if match := [v for v in variation_skus if v["SKU"] == p["SKU"]]:
    #         overlaps.append({"product": p, "variation": match})

    # print("[red]OVERLAPS")
    # print(overlaps)
    # print(len(overlaps))

    wcapi = ctx.parent.obj["wcapi"]


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
