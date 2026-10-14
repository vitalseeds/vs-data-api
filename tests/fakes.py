"""
Stand-ins for external systems, for tests that must run without FileMaker.

``FakeConnection`` replaces a pypyodbc connection: it records every SQL
statement and answers SELECTs with canned rows matched by regex.
"""

import re


def normalise_sql(sql: str) -> str:
    """Collapse whitespace so SQL can be compared regardless of formatting."""
    return " ".join(sql.split())


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []
        self.rowcount = 0

    def execute(self, sql, *params):
        self.connection.executed.append(normalise_sql(sql))
        self.rows = []
        for pattern, rows in self.connection.results.items():
            if re.search(pattern, sql, re.IGNORECASE | re.DOTALL):
                self.rows = list(rows)
                break
        self.rowcount = len(self.rows)
        return self

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    """
    Args:
        results: {regex: rows}, the first pattern matching a query gives its rows
    """

    def __init__(self, results: dict = None, connect_string: str = "DSN=fake"):
        self.results = results or {}
        self.connectString = connect_string
        self.executed = []
        self.commits = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def statements(self, pattern: str) -> list:
        """Executed statements matching a regex (case insensitive)."""
        return [sql for sql in self.executed if re.search(pattern, sql, re.IGNORECASE)]
