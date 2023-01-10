"""
Table names etc that are relied on by vs-data.

Some (commented) may need to be created in filemaker.
"""
from enum import Enum


class FilemakerTable(str, Enum):
    """
    Enum type to hold filemaker table/field name strings as constants
    """

    ...


class Acquisitions(FilemakerTable):
    table_name = "Acquisitions"

    SKU = "SKU"
    crop = "crop"
    wc_product_id = "wc_product_id"


# Accessor functions


def get_fm_table_class_name(table_ref: str):
    return table_ref.title()


def get_fm_field_name(table_ref: str, field_ref: str) -> str:
    table_class = globals()[get_fm_table_class_name(table_ref)]
    return getattr(table_class, field_ref).value


def get_fm_table_name(table_ref: str) -> str:
    return getattr(globals()[get_fm_table_class_name(table_ref)], "table_name").value


# Shortened function aliases for brevity

fname = get_fm_field_name
tname = get_fm_table_name
