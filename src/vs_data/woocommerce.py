"""
Vital Seeds FM schema specific stock management

These will be run (via shell commands) from FM scripts
"""

from rich import print
from vs_data.utils.cli import display_table
from vs_data.utils.fm.db import select as fm_select

WC_MAX_API_RESULT_COUNT = 10


def get_product_sku_map_from_linkdb(fmlinkdb):
    table = "Products"
    columns = ["_kf_WooCommerceID", "SKU", "Name"]
    products = fm_select(fmlinkdb, table, columns)
    return products


def get_product_variation_sku_map_from_linkdb(fmlinkdb):
    table = "ProductVariations"
    columns = ["_kf_WooCommerceID", "SKU"]
    variations = fm_select(fmlinkdb, table, columns)
    return variations
