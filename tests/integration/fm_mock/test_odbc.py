"""Test cases for the __main__ module."""
import sqlite3
from inspect import cleandoc as dedent

import pypyodbc as pyodbc
import pytest
from rich import print

from vs_data_api.vs_data import log
from vs_data_api.vs_data.fm import db

# @pytest.mark.fmdb
# def test_get_batches_awaiting_upload_join_acq(vsdb_connection):
#     flag_batches_for_upload(vsdb_connection, [3515, 3516, 3517])
#     batches = stock.batch_upload.get_batches_awaiting_upload_join_acq(vsdb_connection)
#     assert batches

pytestmark = [pytest.mark.dbmock]


ACQUISITIONS_SCHEMA = {
    "sku": "TEXT NOT NULL",
    "crop": "TEXT",
    "wc_product_id": "INTEGER",
    "wc_variation_lg_id": "INTEGER",
    "wc_variation_regular_id": "INTEGER",
    "not_selling_in_shop": "TEXT",
}
ACQUISITIONS_COLUMNS = ACQUISITIONS_SCHEMA.keys()


@pytest.mark.dbmock
def test_db_connect():
    connection = sqlite3.connect("vs_stock.db")
    assert connection.total_changes == 0


def test_connect_to_sqlite_with_odbc():
    fmdb_mock = db.connection(
        "DRIVER={SQLite3 ODBC Driver};SERVER=localhost;DATABASE=tests/fmdb_mock.sqlite;Trusted_connection=yes"
    )
    assert isinstance(fmdb_mock, pyodbc.Connection)


def create_acquisitions_table(fmdb_mock):
    # TODO: use schema constant to generate SQL
    create_acq_table = dedent(
        """
        CREATE TABLE IF NOT EXISTS acquisitions (
            sku TEXT NOT NULL,
            crop TEXT,
            wc_product_id INTEGER,
            wc_variation_lg_id INTEGER,
            wc_variation_regular_id INTEGER,
            not_selling_in_shop TEXT
        );
    """
    )
    fmdb_mock.cursor().execute(create_acq_table)
    fmdb_mock.commit()
    log.debug("Created acquisitions table")


def create_acquisitions_sample_from_filemaker(fmdb, fmdb_mock):
    create_acquisitions_table(fmdb_mock)
    _, rows = db._select_columns(fmdb, "acquisitions", columns=ACQUISITIONS_COLUMNS)
    acq_values = [f'("{r[0]}", "{r[1]}", {r[2] or "NULL"}, {r[3] or "NULL"}, {r[4] or "NULL"}, "{r[5]}")' for r in rows]
    create_mock_acquistions = dedent(
        f"""
        INSERT INTO
        acquisitions ({",".join(ACQUISITIONS_COLUMNS)})
        VALUES
        {', '.join(acq_values)};
    """
    )
    fmdb_mock.cursor().execute(create_mock_acquistions)
    fmdb_mock.commit()
    log.debug("Added acquisitions from filemaker")


@pytest.mark.fmdb
def test_create_sqlite_mock(vsdb_connection):
    """
    Requires an sqlite odbc driver for pyodbc to talk to test db
    Try http://www.ch-werner.de/sqliteodbc installer or `brew install sqliteodbc`
    """
    fmdb_mock = db.connection(
        "DRIVER={SQLite3 ODBC Driver};SERVER=localhost;DATABASE=tests/fmdb_mock.sqlite;Trusted_connection=yes"
    )

    create_acquisitions_sample_from_filemaker(vsdb_connection, fmdb_mock)
    select_acquisitions = "SELECT * from acquisitions"
    fmdb_mock.cursor().execute(select_acquisitions)

    for acquisition in fmdb_mock.cursor().execute(select_acquisitions).fetchall():
        log.debug(acquisition)


def test_select_columns():
    fmdb_mock = db.connection(
        "DRIVER={SQLite3 ODBC Driver};SERVER=localhost;DATABASE=tests/fmdb_mock.sqlite;Trusted_connection=yes"
    )
    results = db._select_columns(
        fmdb_mock,
        "acquisitions",
        ACQUISITIONS_COLUMNS,
    )
    assert results


# @pytest.mark.fmdb
# def test_record__generate_batch_table(vsdb_connection):
#     # TODO: mark this test 'record'
#     # Get a subset of batch records from fmdb and save them into equivalent
#     # sqlite database.
#     ...
