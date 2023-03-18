"""Test cases for the __main__ module."""
import json

import pytest
import requests
import responses
import toml
from objexplore import explore
from responses import _recorder, matchers
from rich import print

from vs_data import log, stock
from vs_data.fm import db

from . import _add_from_file_match_params
from . import flag_batches_for_upload
from inspect import cleandoc as dedent
import pypyodbc as pyodbc

# @pytest.mark.fmdb
# def test_get_batches_awaiting_upload_join_acq(vsdb_connection):
#     flag_batches_for_upload(vsdb_connection, [3515, 3516, 3517])
#     batches = stock.batch_upload.get_batches_awaiting_upload_join_acq(vsdb_connection)
#     assert batches


import sqlite3

from sqlite3 import Error

ACQUISITIONS_SCHEMA = {
    "sku": "TEXT NOT NULL",
    "crop": "TEXT",
    "wc_product_id": "INTEGER",
    "wc_variation_lg_id": "INTEGER",
    "wc_variation_regular_id": "INTEGER",
    "not_selling_in_shop": "TEXT",
}
ACQUISITIONS_COLUMNS = ACQUISITIONS_SCHEMA.keys()

def create_connection(path):
    connection = None
    try:
        connection = sqlite3.connect(path)
        print("Connection to SQLite DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection


def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query executed successfully")
    except Error as e:
        print(f"The error '{e}' occurred")


def execute_read_query(connection, query):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Error as e:
        print(f"The error '{e}' occurred")

def create_acquisitions_table(fmdb_mock):
    # TODO: use schema constant to generate SQL
    create_acq_table = dedent("""
        CREATE TABLE IF NOT EXISTS acquisitions (
            sku TEXT NOT NULL,
            crop TEXT,
            wc_product_id INTEGER,
            wc_variation_lg_id INTEGER,
            wc_variation_regular_id INTEGER,
            not_selling_in_shop TEXT
        );
    """)
    execute_query(fmdb_mock, create_acq_table)


def create_acquisitions_sample(fmdb, fmdb_mock):
    create_acquisitions_table(fmdb_mock)
    _, rows = db._select_columns(fmdb, "acquisitions", columns=ACQUISITIONS_COLUMNS)

    # rows = quote_string_values(rows)
    # print(rows)
    # acq_values = [f"({', '.join(str(r))})" for r in rows]
    # print(acq_values)
    acq_values = [f'("{r[0]}", "{r[1]}", {r[2] or "NULL"}, {r[3] or "NULL"}, {r[4] or "NULL"}, "{r[5]}")' for r in rows]
    create_mock_acquistions = dedent(f"""
        INSERT INTO
        acquisitions ({",".join(ACQUISITIONS_COLUMNS)})
        VALUES
        {', '.join(acq_values)};
    """)
    print(create_mock_acquistions)
    execute_query(fmdb_mock, create_mock_acquistions)


def test_create_sqlite_mock(vsdb_connection):
    """
    Requires an sqlite odbc driver for pyodbc to talk to test db
    Try http://www.ch-werner.de/sqliteodbc installer or `brew install sqliteodbc`
    """
    # TODO: write up pyodbc sqlite solution/dependencies in docs
    # https://realpython.com/python-sql-libraries/#sqlite_1
    fmdb_mock = create_connection("tests/fmdb_mock.sqlite")

    create_acquisitions_sample(vsdb_connection, fmdb_mock)
    # select_acquisition = "SELECT * from acquisitions"
    # acquisitions = execute_read_query(fmdb_mock, select_acquisition)

    for acquisition in acquisitions:
        print(acquisition)


def test_connect_to_sqlite_with_odbc():
    # Create pyodbc connection to mock
    fmdb_mock = db.connection("DRIVER={SQLite3 ODBC Driver};SERVER=localhost;DATABASE=tests/fmdb_mock.sqlite;Trusted_connection=yes")
    assert isinstance(fmdb_mock, pyodbc.Connection)
    # Run an sql query using existing sql builder function (eg
    # db._select_columns)
    results = db._select_columns(
        fmdb_mock,
        "acquisitions",
        ACQUISITIONS_COLUMNS,
    )
    print(results)



@pytest.mark.record
def test_record__generate_batch_table(vsdb_connection):
    # TODO: mark this test 'record'
    # Get a subset of batch records from fmdb and save them into equivalent
    # sqlite database.
    ...