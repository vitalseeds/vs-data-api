"""Tests for simple 200 response from all fast api endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vs_data_api.main import app, get_settings, lifespan

# from vs_data_api.main2 import app, get_settings, lifespan

# def test_fastapi_client(client: TestClient):
#     response = client.get("/")
#     assert response.status_code == 200


def test_status(client: TestClient):
    response = client.get("/")

    assert response
    # assert response.json() == {
    #     "message": "VS Data API running",
    # }


def test_awaiting_upload(client: TestClient):
    response = client.get("/batch/awaiting_upload")
    assert response
    # assert response.status_code == 200
    # assert response.json() == {
    #     "message": "VS Data API running",
    # }
