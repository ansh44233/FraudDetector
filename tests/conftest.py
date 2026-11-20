"""
Shared fixtures for FraudDetector tests.
Unit tests mock the DB — no live Postgres needed.
Integration tests need TEST_DATABASE_URL set.
"""

import os
import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest.mock as mock

@pytest.fixture(scope="session", autouse=True)
def patch_static():
    with mock.patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None):
        yield

@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    # patch open() for dashboard html
    with mock.patch("builtins.open", mock.mock_open(read_data="<html></html>")):
        from api.main import app
    with TestClient(app) as c:
        yield c
