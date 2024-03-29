"""
Table names etc that are relied on by vs-data.

Some (commented) may need to be created in filemaker.
"""

from . import link_tables, vs_tables


def strip_prefix(table_ref: str) -> str:
    if ":" not in table_ref:
        return table_ref

    return table_ref.split(":")[1].strip()


def parse_db_table_prefix(table_ref: str):
    if ":" not in table_ref:
        return vs_tables, table_ref

    db, table_ref = table_ref.split(":")
    if db == "link":
        return link_tables, strip_prefix(table_ref)
    return vs_tables, table_ref


def snake_to_camel(snake_str):
    return snake_str.title().replace("_", "")


def get_table_class(table_ref: str):
    """
    Returns a class representing a FM table schema.

    Attribute names are references used by vs-data
    Attribute values are the field names used by Filemaker.
    `table_name` gives the Filemaker name used for the table itself.

    If table_ref starts with `link:` prefix
    then the map for the link database is used rather than the stock database.
    """
    db_table_map, table_ref = parse_db_table_prefix(table_ref)
    table_class = getattr(db_table_map, snake_to_camel(table_ref))
    return table_class


def get_fm_table_column_aliases(table_ref: str) -> dict:
    table_class = get_table_class(table_ref)
    fields = table_class.model_fields
    columns = {f: fields[f].default for f in table_class.model_fields.keys()}
    return columns


# TODO: accept "table:field" form
# TODO: lookup for table shortnames eg 'acq'
def get_fm_field_name(table_ref: str, field_ref: str) -> str:
    # TODO: accept 'table:fieldname' as one argument
    # TODO: allow table name aliases eg acq (pydantic?)
    table_class = get_table_class(table_ref)
    # field_name = getattr(table_class, field_ref)
    # Get the field name from the default value of the field (compatibility detail from previous implementation)
    # TODO: this will needed to be updated to use field alias once using pydantic models for validation
    field_name = table_class.model_fields[field_ref].default
    return field_name


def get_fm_table_name(table_ref: str) -> str:
    table_class = get_table_class(table_ref)
    fm_table_name = table_class.table_name
    return strip_prefix(fm_table_name)


# Shortened function aliases for brevity

fname = get_fm_field_name
tname = get_fm_table_name
