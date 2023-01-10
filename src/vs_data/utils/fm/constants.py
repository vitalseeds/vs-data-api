"""
Table names etc that are relied on by vs-data.

Some (commented) may need to be created in filemaker.
"""

from vs_data.utils.fm.db import FilemakerTable


class Acquisitions(FilemakerTable):
    wp_product_id = "wp_product_id"

    table_name = "Acquisitions"


# Accessor functions


def get_fm_table_class_name(table_ref: str):
    return table_ref.title()


def get_fm_field_name(table_ref: str, field_ref: str) -> str:
    return getattr(globals()[get_fm_table_class_name(table_ref)], field_ref)


def get_fm_table_name(table_ref: str) -> str:
    return getattr(globals()[get_fm_table_class_name(table_ref)], "table_name")


# Shortened function aliases for brevity

fname = get_fm_field_name
tname = get_fm_table_name
