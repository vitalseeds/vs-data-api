"""
Table names etc that are relied on by vs-data.

Some (commented) may need to be created in filemaker.
"""

from . import vs_tables
from . import link_tables


def get_table_class(table_ref: str, link_db=False):
    db_table_map = link_tables if link_db else vs_tables
    return getattr(db_table_map, table_ref.title())


def get_fm_field_name(table_ref: str, field_ref: str, linkdb=False) -> str:
    table_class = get_table_class(table_ref)
    return getattr(table_class, field_ref)


def get_fm_table_name(table_ref: str, linkdb=False) -> str:
    table_class = get_table_class(table_ref)
    return getattr(table_class, "table_name")


# Shortened function aliases for brevity

fname = get_fm_field_name
tname = get_fm_table_name
