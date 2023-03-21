import pathlib
import pickle
from os.path import exists
from rich import print
from vs_data import log
from inspect import cleandoc as dedent

TABLE_FIELDS_PICKLE = f"tmp/fmdb_schema_table_fields.pickle"


def get_fmdb_tables(fmdb):
    # Returns TableName, FieldName, FieldType, FieldID, FieldClass, FieldReps and ModCount
    sql = "SELECT DISTINCT BaseTableName FROM FileMaker_Tables"
    tables = fmdb.cursor().execute(sql).fetchall()
    return [t[0] for t in tables]


def get_fmdb_fields(fmdb, table):
    # Returns TableName, FieldName, FieldType, FieldID, FieldClass, FieldReps and ModCount
    sql = f"SELECT * FROM FileMaker_Fields WHERE TableName='{table}'"
    print(sql)
    fields = fmdb.cursor().execute(sql).fetchall()
    return fields


def get_fmdb_table_fields(fmdb, cached=False):
    """
    Get field details for all tables in the FileMaker database.

    Returns a dict tablename:field_dict
    eg
    {'stock': [
        {
            'TableName': 'stock',
            'FieldName': 'PrimaryKey',
            'FieldType': 'varchar',
            'FieldID': 1.0,
            'FieldClass': 'Normal',
            'FieldReps': 1.0,
            'ModCount': 0.0
        },
        ...
    }
    """
    if cached and exists(TABLE_FIELDS_PICKLE):
        with open(TABLE_FIELDS_PICKLE, 'rb') as file:
            return pickle.load(file)

    tables = get_fmdb_tables(fmdb)
    field_columns = ("TableName", "FieldName", "FieldType", "FieldID", "FieldClass", "FieldReps", "ModCount")

    table_fields = {}
    for table in tables:
        dict_rows = [dict(zip(field_columns, f)) for f in get_fmdb_fields(fmdb, table)]
        table_fields[table] = dict_rows

    with open(TABLE_FIELDS_PICKLE, 'wb') as file:
        pickle.dump(table_fields, file)

    return table_fields


def test_duplicate_fmdb_schema(vsdb_connection):
    ddr = "/Users/tom/vital_seeds/fm_database/exports/schema/db_design_report/vs_db_fmp12.xml"
    table_fields = get_fmdb_table_fields(vsdb_connection, cached=True)
    print(table_fields)


# https://www.databuzz.com.au/using-executesql-to-query-the-virtual-schemasystem-tables/
def test_query_fmdb_schema(vsdb_connection):
    # Returns TableName, FieldName, FieldType, FieldID, FieldClass, FieldReps and ModCount
    sql = "SELECT DISTINCT BaseTableName FROM FileMaker_Tables"
    tables = vsdb_connection.cursor().execute(sql).fetchall()
    # sql = "SELECT * FROM FileMaker_Fields"
    sql = "SELECT * FROM FileMaker_Fields WHERE TableName='acquisitions'"
    # Returns TableName, FieldName, FieldType, FieldID, FieldClass, FieldReps and ModCount
    fields = vsdb_connection.cursor().execute(sql).fetchall()
    # fmdb.commit()
    log.debug(tables)
    log.debug(fields)
