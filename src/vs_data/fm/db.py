"""
Filemaker SQL limitations/requirements

- table names must be enclosed in double quotes
- string values must be enclosed in single quotes
"""

import os

import pypyodbc as pyodbc

from vs_data import log
from vs_data.fm import constants


VSDATA_FM_CONNECTION_STRING = os.environ.get("VSDATA_FM_CONNECTION_STRING", None)
VSDATA_FM_LINK_CONNECTION_STRING = os.environ.get("VSDATA_FM_LINK_CONNECTION_STRING", None)


def construct_dsn_connection_string(
    dsn: str = "", user: str = "", pwd: str = ""
) -> str:
    """
    Format a connection string to connect via a DSN
    """
    # dsn = "vs_stock"
    # user = "stock_update"
    # pwd = ""
    return f"DSN={dsn};UID={user};PWD={pwd}"


def construct_db_connection_string(
    db_name: str, db_user: str, db_password: str, db_host: str = "localhost"
) -> str:
    """
    Format a connection string to connect directly to database.

    Example:
    db_name = "vs_db"
    db_user = "vs_data"
    db_password = ""
    """
    return (
        "Driver={FileMaker ODBC};Server="
        + db_host
        + ";Database="
        + db_name
        + ";UID="
        + db_user
        + ";PWD="
        + db_password
        + ";"
    )


def is_link_db(connection):
    if connection.connectString == VSDATA_FM_LINK_CONNECTION_STRING:
        return True
    return False


def connection(connection_string: str) -> pyodbc.Connection:
    """
    Return a database connection.

    Uses a DSN
    """
    if not connection_string:
        return False

    connection = pyodbc.connect(connection_string)
    return connection


def _select_columns(
    connection: pyodbc.Connection,
    table: str,
    columns: str,
    where: str = None,
) -> dict:
    """
    Construct SQL statement for a select query and return result.

    Returns columns, rows.
    """
    fm_columns = [constants.fname(table, c) for c in columns]
    fm_table = constants.tname(table)
    field_list = ",".join([f'"{f}"' for f in fm_columns])
    where_clause = f"WHERE {where}" if where else ""
    sql = f'SELECT {field_list} FROM "{fm_table}" {where_clause}'
    rows = connection.cursor().execute(sql).fetchall()

    log.debug(sql)
    return columns, rows


def select(
    connection: pyodbc.Connection,
    table: str,
    columns: list,
    where: str = None,
) -> dict:
    """
    Perform SQL select query and return result as list of dicts

    Accepts
    - connection, table, columns, where
    """
    columns, rows = _select_columns(connection, table, columns, where)
    objects = [dict(zip(columns, r)) for r in rows]
    return objects
