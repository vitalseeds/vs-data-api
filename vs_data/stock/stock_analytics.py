from vs_data.stock.misc import get_all_products, get_all_wc_products
from vs_data.stock.batch_upload import get_wc_large_variations_by_product
from vs_data.cli.table import display_product_table, display_table
import json
import pandas as pd
import pickle
from os.path import exists
import os
from vs_data.fm.db import convert_pyodbc_cursor_results_to_lists
from vs_data.fm.constants import fname as _f
from vs_data.fm.constants import tname as _t

def get_acq_join_stock(connection):
    acq_sku = _f("acquisitions", "sku")
    acq_columns=[
        acq_sku,
        _f("acquisitions", "crop"),
        _f("acquisitions", "wc_product_id"),
        _f("acquisitions", "wc_variation_lg_id"),
        _f("acquisitions", "wc_variation_regular_id"),
    ]
    stock_sku = _f("stock", "sku")
    stock_columns = [
        stock_sku,
        _f("stock", "stock_large"),
        _f("stock", "stock_regular"),
        # _f("stock", "update"),
        # _f("stock", "update_large"),
    ]

    # TODO: should get sku from join on seed_lot, not packeting_batches
    aliased_columns = [f"A.{a}" for a in acq_columns] + [f"S.{s}" for s in stock_columns]
    aliased_columns = ", ".join(aliased_columns)
    awaiting = _f("packeting_batches", "awaiting_upload")
    # where = f"lower({awaiting})='yes' AND b.pack_date IS NOT NULL"

    sql = (
        f"SELECT {aliased_columns} "
        'FROM "acquisitions" A '
        f'LEFT JOIN "stock" S ON A.{acq_sku} = S.{stock_sku} '
        # "WHERE " + where
    )
    print(sql)
    rows = connection.cursor().execute(sql).fetchall()
    columns = acq_columns + stock_columns
    return columns, rows
    # return [dict(zip(columns, r)) for r in rows]


def compare_wc_fm_stock(fmdb, wcapi, cli: bool=False, csv: bool=False, uncache=False, variations=True):
    """
    Query both fm and wc for stock values.

    Heavily cached using pickles.
    """
    column_pickle = f"tmp/compare_acq_columns.pickle"
    results_pickle = f"tmp/compare_acq_results.pickle"
    products_pickle = f"tmp/compare_wc_products.pickle"
    variations_pickle = f"tmp/compare_wc_variations.pickle"

    if uncache:
        if os.path.exists(column_pickle):
            os.remove(column_pickle)
        if os.path.exists(results_pickle):
            os.remove(results_pickle)
        if os.path.exists(products_pickle):
            os.remove(products_pickle)

    # get all products from vs:acquisitions
    if exists(results_pickle) and exists(column_pickle):
        with open(column_pickle, 'rb') as file:
            columns = pickle.load(file)
        with open(results_pickle, 'rb') as file:
            acquisitions = pickle.load(file)
        print("hello")
    else:
        columns, pyodbc_results = get_acq_join_stock(fmdb)
        acquisitions = convert_pyodbc_cursor_results_to_lists(pyodbc_results)
        with open(column_pickle, 'wb') as file:
            pickle.dump(columns, file)
        with open(results_pickle, 'wb') as file:
            pickle.dump(acquisitions, file)

    # create a pandas dataframe for vs stock
    vs_stock_pd = pd.DataFrame(acquisitions, columns=columns)

    if cli:
        # display_table(acquisitions, headers=columns)
        print(vs_stock_pd)

    # get all products from woocommerce
    if exists(products_pickle):
        with open(products_pickle, 'rb') as file:
            wc_products = pickle.load(file)
    else:
        wc_products = get_all_wc_products(wcapi)
        with open(products_pickle, 'wb') as file:
            pickle.dump(wc_products, file)
    wc_product_stock = pd.DataFrame.from_dict(wc_products)


    # create a pandas dataframe for regular stock
    print(wc_product_stock[["id", "name", "stock_quantity", "variations"]])

    # create a pandas dataframe for large stock
    # Filter for products that have a large product variation
    vs_stock_variations = vs_stock_pd[vs_stock_pd.wc_variation_lg_id.notnull()]
    # Create map dict using pandas index
    # https://cmdlinetips.com/2021/04/convert-two-column-values-from-pandas-dataframe-to-a-dictionary/
    lg_variation_id_map = vs_stock_variations.set_index('wc_product_id').to_dict()['wc_variation_lg_id']

    if exists(variations_pickle):
        with open(variations_pickle, 'rb') as file:
            products_large_variation_stock = pickle.load(file)
    else:
        products_large_variation_stock = get_wc_large_variations_by_product(
            wcapi,
            lg_variation_id_map.keys(),
            lg_variation_id_map,
        )
        with open(variations_pickle, 'wb') as file:
            pickle.dump(products_large_variation_stock, file)

    print(products_large_variation_stock)

    # rename stock column wc_regular_stock

    # get all variations from woocommerce - dataframe
    # rename stock column wc_large_stock

    # join products and variations stock df on product id

    # join vs_stock and wc stock df on sku

    # compare (cli)
    # dataframe to csv