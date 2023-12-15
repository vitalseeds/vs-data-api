import sqlite3

from rich import print


def test_db_connect():
    connection = sqlite3.connect("vs_stock.db")
    assert connection.total_changes == 0
