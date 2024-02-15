import datetime


# TODO: Move this to a method on a cursor class to overload pypypyodbc cursor
# TODO: Use pydantic models types to format the values
def param_types_from_var(sql_string: str, values: tuple):
    """
    FileMaker ODBC does not tell us what types the fields are, so quote them etc
    using argument type instead.

    (see pypyodbc for 'self.connection.support_SQLDescribeParam')
    """
    quoted_values = []
    for value in values:
        if isinstance(value, str):
            quoted_values.append(f"'{value}'")
            continue
        # TODO: test for formatting dates
        elif isinstance(value, datetime.datetime):
            quoted_values.append(f"TIMESTAMP '{value.strftime('%Y-%m-%d %H:%M:%S')}'")
        elif isinstance(value, datetime.date):
            quoted_values.append(f"DATE '{value.strftime('%Y/%m/%d')}'")
        quoted_values.append(value)

    # We used the ? placeholder for compatibility with pyodbc, so replace with {} for .format
    return sql_string.replace("?", "{}").format(*quoted_values)
