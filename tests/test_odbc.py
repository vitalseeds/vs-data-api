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

from . import _add_from_file_match_params
from . import flag_batches_for_upload

# @pytest.mark.fmdb
# def test_get_batches_awaiting_upload_join_acq(vsdb_connection):
#     flag_batches_for_upload(vsdb_connection, [3515, 3516, 3517])
#     batches = stock.batch_upload.get_batches_awaiting_upload_join_acq(vsdb_connection)
#     assert batches


import sqlite3

from sqlite3 import Error


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


def test_connect_to_sqlite_with_odbc():
    # https://realpython.com/python-sql-libraries/#sqlite_1
    connection = create_connection("tests/fmdb_mock.sqlite")
    create_users_table = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  age INTEGER,
  gender TEXT,
);
"""
    execute_query(connection, create_users_table)
    create_mock_users = """
INSERT INTO
  users (name, age, gender, nationality)
VALUES
  ('James', 25, 'male', 'USA'),
  ('Leila', 32, 'female', 'France'),
  ('Brigitte', 35, 'female', 'England'),
  ('Mike', 40, 'male', 'Denmark'),
  ('Elizabeth', 21, 'female', 'Canada');
"""
    execute_query(connection, create_mock_users)
    select_users = "SELECT * from users"
    users = execute_read_query(connection, select_users)

    for user in users:
        print(user)


@pytest.mark.record
def test_record__generate_batch_table(vsdb_connection):
    # TODO: mark this test 'record'
    # Get a subset of batch records from fmdb and save them into equivalent
    # sqlite database.
    ...