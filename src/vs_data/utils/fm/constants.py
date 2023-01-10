"""
Table names etc that are relied on by vs-data.

Some (commented) may need to be created in filemaker.
"""

from vs_data.utils.fm.db import FilemakerTable


class Acquisitions(FilemakerTable):
    wp_product_id = "wp_product_id"


def field_name(table_ref: str, field_ref: str) -> str:
    return getattr(globals()[table_ref], field_ref)


# Shortened alias for field name function
fname = field_name
