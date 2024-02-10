from __future__ import annotations

import os
from functools import lru_cache

import pytest
import responses
from fastapi.testclient import TestClient

from vs_data_api.config import TestSettings, get_env_settings
from vs_data_api.main import app, get_settings
from vs_data_api.vs_data.fm import db
from vs_data_api.vs_data.fm.db import pyodbc
from vs_data_api.vs_data.wc import api

# Allow fastapi *dependencies* to use the test settings
# currently replaced with test for pytest env var
# @lru_cache()
# def get_settings_override():
#     return TestSettings()
# app.dependency_overrides[get_settings] = get_settings_override

# Get the same test settings for use with pytest fixtures
test_settings = get_env_settings()

VSDATA_FM_CONNECTION_STRING = test_settings.fm_connection_string
VSDATA_FM_LINK_CONNECTION_STRING = test_settings.fm_link_connection_string

VSDATA_WC_URL = test_settings.vsdata_wc_url
VSDATA_WC_KEY = test_settings.vsdata_wc_key
VSDATA_WC_SECRET = test_settings.vsdata_wc_secret

# import betamax

# with betamax.Betamax.configure() as config:
#     config.cassette_library_dir = "tests/fixtures/cassettes"


def pytest_addoption(parser):
    parser.addoption("--fmdb", action="store_true", dest="fmdb", default=False, help="enable fmdb decorated tests")
    parser.addoption("--wcapi", action="store_true", dest="wcapi", default=False, help="enable wcapi decorated tests")
    parser.addoption(
        "--dbmock", action="store_true", dest="dbmock", default=False, help="enable dbmock decorated tests"
    )
    parser.addoption("--skipslow", action="store_true", dest="skipslow", default=False, help="skip slow running tests")


def pytest_configure(config):
    mark_expression = []
    if not config.option.fmdb:
        mark_expression.append("not fmdb")
    if not config.option.wcapi:
        mark_expression.append("not wcapi")
    if not config.option.dbmock:
        mark_expression.append("not dbmock")
    if config.option.skipslow:
        mark_expression.append("not slow")
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


@pytest.fixture(name="client")
def _client():
    with TestClient(app) as client:
        yield client
