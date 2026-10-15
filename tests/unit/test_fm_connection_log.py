import logging

import pytest

from vs_data_api.vs_data.fm import db

BASE = "Driver={FileMaker ODBC};Server=127.0.0.1;Database=vs_db;UID=vsdata;"


@pytest.mark.parametrize(
    ("connection_string", "masked"),
    [
        (BASE + "PWD=s3cret;", BASE + "PWD=****;"),
        (BASE + "pwd=s3cret;", BASE + "pwd=****;"),
        (BASE + "Password=s3cret;", BASE + "Password=****;"),
        (BASE + "PWD=s3cret", BASE + "PWD=****"),  # no trailing semicolon
        (BASE + "PWD=a=b#c;Port=2399;", BASE + "PWD=****;Port=2399;"),  # '=' in the password
        (BASE + "PWD={se;cret}};x};Port=2399;", BASE + "PWD=****;Port=2399;"),  # braced, with ';' inside
        (BASE + "PWD=;", BASE + "PWD=****;"),  # empty still masked, so nothing is hinted
        ("DSN=vs_db;UID=u", "DSN=vs_db;UID=u"),  # no password: unchanged
        ("", ""),
    ],
)
def test_mask_password_stars_the_value_and_keeps_the_rest(connection_string, masked):
    assert db.mask_password(connection_string) == masked


def test_failed_connection_logs_the_masked_string(monkeypatch, caplog):
    def refuse(connection_string):
        raise db.pyodbc.Error("08001", "listener refused")

    monkeypatch.setattr(db.pyodbc, "connect", refuse)
    with caplog.at_level(logging.ERROR), pytest.raises(db.pyodbc.Error):
        db.connection(BASE + "PWD=s3cret;")
    assert "s3cret" not in caplog.text
    assert BASE + "PWD=****;" in caplog.text
