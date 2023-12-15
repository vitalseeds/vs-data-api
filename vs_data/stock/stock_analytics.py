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
from vs_data import log
from rich import print
import numpy as np
from datascroller import scroll

REPORT_CSV_FILE_PATH = "tmp/exports/report.csv"


def _debug_data(vs_stock_pd, vs_all_stock, wc_product_stock_pd, wc_variations_stock_pd, wc_all_stock, report):
    """
    Throwaway debug function to display some pandas data in the cli.
    """
    print(wc_product_stock_pd.columns)
    scroll(vs_stock_pd.loc[vs_stock_pd["wc_product_id__vs"] == 1694])
    scroll(wc_product_stock_pd.loc[wc_product_stock_pd["id__wc_prd"] == 1694][["stock_quantity__wc_prd"]])
    print(wc_variations_stock_pd.columns)
    scroll(wc_variations_stock_pd.loc[[1694]])
    scroll(report.loc[report["wc_product_id__vs"] == 1694])
    scroll(
        vs_all_stock[vs_all_stock["id__wc_prd"] == 1694][
            [
                "wc_product_id__vs",
                "variation_id__wc_lg_var",
                "stock_regular__vs",
                "stock_large__vs",
                "stock_quantity__wc_prd",
                "stock_quantity__wc_lg_var",
            ]
        ]
    )
    wc_product_stock_pd.to_csv("tmp/exports/wc_product_stock_pd.csv", index=False)
    wc_variations_stock_pd.to_csv("tmp/exports/wc_variations_stock_pd.csv", index=False)
    wc_all_stock.to_csv("tmp/exports/wc_all_stock.csv", index=False)
    vs_stock_pd.to_csv("tmp/exports/vs_stock_pd.csv", index=False)


def get_acq_join_stock(connection):
    acq_sku = _f("acquisitions", "sku")
    acq_columns = [
        acq_sku,
        _f("acquisitions", "crop"),
        _f("acquisitions", "wc_product_id"),
        _f("acquisitions", "wc_variation_lg_id"),
        _f("acquisitions", "wc_variation_regular_id"),
        _f("acquisitions", "not_selling_in_shop"),
    ]
    stock_sku = _f("stock", "sku")
    stock_columns = [
        stock_sku,
        _f("stock", "stock_large"),
        _f("stock", "stock_regular"),
    ]

    # TODO: should get sku from join on seed_lot, not packeting_batches
    aliased_columns = [f"A.{a}" for a in acq_columns] + [f"S.{s}" for s in stock_columns]
    aliased_columns = ", ".join(aliased_columns)
    not_selling = _f("acquisitions", "not_selling_in_shop")
    # where = f"lower({not_selling})='yes'"
    where = f"{not_selling} IS NULL"

    sql = (
        f"SELECT {aliased_columns} "
        'FROM "acquisitions" A '
        f'LEFT JOIN "stock" S ON A.{acq_sku} = S.{stock_sku} '
        "WHERE " + where
    )
    log.debug(sql)
    rows = connection.cursor().execute(sql).fetchall()
    columns = acq_columns + stock_columns
    return columns, rows
    # return [dict(zip(columns, r)) for r in rows]


def compare_wc_fm_stock(fmdb, wcapi, cli: bool = False, csv: bool = False, uncache=False, variations=True):
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
        if os.path.exists(variations_pickle):
            os.remove(variations_pickle)

    # get all products from vs:acquisitions
    if exists(results_pickle) and exists(column_pickle):
        with open(column_pickle, "rb") as file:
            columns = pickle.load(file)
        with open(results_pickle, "rb") as file:
            acquisitions = pickle.load(file)
    else:
        columns, pyodbc_results = get_acq_join_stock(fmdb)
        acquisitions = convert_pyodbc_cursor_results_to_lists(pyodbc_results)
        with open(column_pickle, "wb") as file:
            pickle.dump(columns, file)
        with open(results_pickle, "wb") as file:
            pickle.dump(acquisitions, file)

    # create a pandas dataframe for vs stock
    vs_stock_pd: pd.DataFrame = pd.DataFrame(acquisitions, columns=columns)
    vs_stock_pd = vs_stock_pd.astype({"wc_product_id": "Int64", "wc_variation_lg_id": "Int64"})
    vs_stock_pd = vs_stock_pd.add_suffix("__vs")
    log.debug(f"{vs_stock_pd=}")

    # get all products from woocommerce
    if exists(products_pickle):
        with open(products_pickle, "rb") as file:
            wc_products = pickle.load(file)
    else:
        wc_products = get_all_wc_products(wcapi)
        with open(products_pickle, "wb") as file:
            pickle.dump(wc_products, file)

    # create a pandas dataframe for regular stock
    wc_product_stock_pd = pd.DataFrame.from_dict(wc_products)
    wc_product_stock_pd = wc_product_stock_pd.add_suffix("__wc_prd")

    # create a pandas dataframe for large stock
    # filter for products that have a large product variation
    vs_stock_variations = vs_stock_pd[vs_stock_pd.wc_variation_lg_id__vs.notnull()]

    # create variation map dict using the dataframe index
    # https://cmdlinetips.com/2021/04/convert-two-column-values-from-pandas-dataframe-to-a-dictionary/
    lg_variation_id_map = vs_stock_variations.set_index("wc_product_id__vs").to_dict()["wc_variation_lg_id__vs"]

    # Get and cache each of the product variations individually
    if exists(variations_pickle):
        with open(variations_pickle, "rb") as file:
            products_large_variation_stock = pickle.load(file)
    else:
        products_large_variation_stock = get_wc_large_variations_by_product(
            wcapi,
            lg_variation_id_map.keys(),
            lg_variation_id_map,
        )
        with open(variations_pickle, "wb") as file:
            pickle.dump(products_large_variation_stock, file)

    wc_variations_stock_pd = pd.DataFrame.from_dict(products_large_variation_stock, orient="index")
    wc_variations_stock_pd = wc_variations_stock_pd.add_suffix("__wc_lg_var")

    # join wc product and large variations stock on product id
    wc_all_stock = pd.merge(
        wc_product_stock_pd, wc_variations_stock_pd, left_on="id__wc_prd", right_index=True, how="left"
    )

    # Remove products that have null values for wc_product_id (no product on wc)
    vs_stock_pd = vs_stock_pd[vs_stock_pd["wc_product_id__vs"].notna()]
    # join vs_stock and wc stock df on wc product id
    vs_all_stock = pd.merge(vs_stock_pd, wc_all_stock, left_on="wc_product_id__vs", right_on="id__wc_prd", how="left")
    log.debug(f"{vs_all_stock=}")
    log.debug(f"{vs_all_stock.columns=}")
    report: pd.DataFrame = vs_all_stock[
        [
            "sku__vs",
            "wc_product_id__vs",
            "variation_id__wc_lg_var",
            "stock_regular__vs",
            "stock_quantity__wc_prd",
            "stock_large__vs",
            "stock_quantity__wc_lg_var",
        ]
    ]
    # convert floats to int
    report = report.astype(
        {
            "stock_regular__vs": "Int64",
            "stock_large__vs": "Int64",
            "stock_quantity__wc_prd": "Int64",
            "stock_quantity__wc_lg_var": "Int64",
        }
    )

    pd.set_option("display.max_columns", None)  # or 1000
    pd.set_option("display.max_rows", None)  # or 1000
    pd.set_option("display.max_colwidth", None)  # or 199

    # _debug_data(vs_stock_pd, vs_all_stock, wc_product_stock_pd, wc_variations_stock_pd, wc_all_stock, report)

    def get_wc_edit_url(row):
        return f'{os.environ.get("VSDATA_WC_URL")}/wp-admin/post.php?post={row["wc_product_id__vs"]}&action=edit'

    report["wc_edit_url"] = report.apply(lambda row: get_wc_edit_url(row), axis=1)
    if csv:
        report.to_csv(REPORT_CSV_FILE_PATH, index=False)

    if cli:
        scroll(report)

    return REPORT_CSV_FILE_PATH
