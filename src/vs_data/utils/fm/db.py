"""
Filemaker SQL limitations/requirements

- table names must be enclosed in double quotes
- string values must be enclosed in single quotes
"""

import pypyodbc as pyodbc


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


def connection(connection_string):
    """
    Return a database connection.

    Uses a DSN
    """
    if not connection_string:
        return False

    connection = pyodbc.connect(connection_string)
    return connection
