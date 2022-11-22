import pypyodbc


def construct_connection_string(dsn="", user="", pwd=""):
    # dsn = "vs_stock"
    # user = "stock_update"
    # pwd = ""
    return f"DSN={dsn};UID={user};PWD={pwd}"


def connection(connection_string):
    if not connection_string:
        return False

    connection = pypyodbc.connect(connection_string)
    return connection.cursor()
