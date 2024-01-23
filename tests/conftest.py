import os

import pytest
import responses

from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.fm.db import pyodbc
from vs_data_api.vs_data.wc import api

# import betamax

# with betamax.Betamax.configure() as config:
#     config.cassette_library_dir = "tests/fixtures/cassettes"


VSDATA_FM_CONNECTION_STRING = os.environ["VSDATA_TEST_FM_CONNECTION_STRING"]
VSDATA_FM_LINK_CONNECTION_STRING = os.environ["VSDATA_TEST_FM_LINK_CONNECTION_STRING"]

VSDATA_WC_URL = os.environ["VSDATA_TEST_WC_URL"]
VSDATA_WC_KEY = os.environ["VSDATA_TEST_WC_KEY"]
VSDATA_WC_SECRET = os.environ["VSDATA_TEST_WC_SECRET"]


def pytest_addoption(parser):
    parser.addoption("--fmdb", action="store_true", dest="fmdb", default=False, help="enable fmdb decorated tests")
    parser.addoption("--wcapi", action="store_true", dest="wcapi", default=False, help="enable wcapi decorated tests")
    parser.addoption(
        "--dbmock", action="store_true", dest="dbmock", default=False, help="enable dbmock decorated tests"
    )


def pytest_configure(config):
    mark_expression = []
    if not config.option.fmdb:
        mark_expression.append("not fmdb")
    if not config.option.wcapi:
        mark_expression.append("not wcapi")
    if not config.option.dbmock:
        mark_expression.append("not dbmock")
    combined_markexp = " and ".join(mark_expression)
    if combined_markexp:
        print(f"-m '{combined_markexp}'")
    config.option.markexpr = combined_markexp


@pytest.fixture
def vsdb_connection() -> pyodbc.Connection:
    """Fixture to provide integration with a REAL filemaker database"""
    return db.connection(VSDATA_FM_CONNECTION_STRING)


@pytest.fixture
def linkdb_connection() -> pyodbc.Connection:
    """Fixture to provide integration with a REAL filemaker database"""

    return db.connection(VSDATA_FM_LINK_CONNECTION_STRING)


@pytest.fixture
def wcapi() -> pyodbc.Connection:
    return api.get_api(VSDATA_WC_URL, VSDATA_WC_KEY, VSDATA_WC_SECRET)


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps
