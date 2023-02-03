import os

import pytest

from vs_data.fm import db
from vs_data.fm.db import pyodbc
from vs_data.wc import api
import responses
import betamax

with betamax.Betamax.configure() as config:
    config.cassette_library_dir = "tests/fixtures/cassettes"


VSDATA_FM_CONNECTION_STRING = os.environ["VSDATA_TEST_FM_CONNECTION_STRING"]
VSDATA_FM_LINK_CONNECTION_STRING = os.environ["VSDATA_TEST_FM_LINK_CONNECTION_STRING"]

VSDATA_WC_URL = os.environ["VSDATA_TEST_WC_URL"]
VSDATA_WC_KEY = os.environ["VSDATA_TEST_WC_KEY"]
VSDATA_WC_SECRET = os.environ["VSDATA_TEST_WC_SECRET"]


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
