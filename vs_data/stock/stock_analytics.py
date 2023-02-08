from vs_data.stock.misc import get_all_products, get_all_wc_products
from vs_data.cli.table import display_product_table, display_table
import json

def compare_wc_fm_stock(fmdb, wcapi, cli: bool=False, csv: bool=False):
    # get all products from vs:acquisitions
    # columns, results = get_all_products(fmdb, cli=True)
    # display_table(results, headers=columns)
    # create a pandas dataframe for vs stock

    # get all products from woocommerce
    products = get_all_wc_products(wcapi)

    # with open('wc_products.json', 'a',encoding="utf-8") as file:
    #     json.dump(products, file, indent=2)

    # create a pandas dataframe for regular stock
    # rename stock column wc_regular_stock

    # get all variations from woocommerce - dataframe
    # create a pandas dataframe for large stock
    # rename stock column wc_large_stock

    # join products and variations stock df on product id

    # join vs_stock and wc stock df on sku

    # compare (cli)
    # dataframe to csv