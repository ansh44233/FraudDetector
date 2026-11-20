"""
Unit tests for FraudDetector API.
All DB calls are mocked — no Postgres needed.
Run: pytest tests/test_api.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient


MOCK_FLAGS = [
    {
        "id": 1, "rule_name": "VELOCITY_10M", "risk_score": 85.0,
        "details": {"txn_count_10m": 7}, "resolved": False,
        "created_at": "2026-11-20T10:00:00", "txn_ref": "abc-123",
        "amount": 950.0, "user_name": "Rahul Sharma", "merchant": "WazirX",
    },
    {
        "id": 2, "rule_name": "MULE_CHAIN", "risk_score": 90.0,
        "details": {"chain_depth": 3}, "resolved": False,
        "created_at": "2026-11-20T09:00:00", "txn_ref": "def-456",
        "amount": 15000.0, "user_name": "Anjali Mehta", "merchant": "UnknownShop",
    },
]

MOCK_SUMMARY = [{
    "total_txns": 326, "open_flags": 14, "avg_risk_score": 72.4,
    "active_users_24h": 8, "txns_last_hour": 12, "volume_24h": 482000,
}]


# ── client fixture (inline, avoids conftest import issues) ───

@pytest.fixture(scope="module")
def client():
    import unittest.mock as mock
    with mock.patch("builtins.open", mock.mock_open(read_data="<html></html>")):
        from api.main import app
    with TestClient(app) as c:
        yield c


# ── Flags ────────────────────────────────────────────────────

class TestFlags:
    def test_list_open_flags(self, client):
        with patch("api.main.query", return_value=MOCK_FLAGS):
            resp = client.get("/flags?resolved=false")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_flag_has_required_fields(self, client):
        with patch("api.main.query", return_value=MOCK_FLAGS):
            resp = client.get("/flags")
        item = resp.json()[0]
        for f in ("id", "rule_name", "risk_score", "resolved", "user_name", "merchant"):
            assert f in item, f"Missing: {f}"

    def test_no_open_flags(self, client):
        with patch("api.main.query", return_value=[]):
            resp = client.get("/flags?resolved=false")
        assert resp.json() == []

    def test_resolve_flag(self, client):
        with patch("api.main.query", return_value=[{"id": 1}]), \
             patch("api.main.execute", return_value=None):
            resp = client.patch("/flags/1", json={"resolved": True})
        assert resp.status_code == 200
        assert resp.json()["resolved"] is True

    def test_resolve_flag_not_found(self, client):
        with patch("api.main.query", return_value=[]):
            resp = client.patch("/flags/9999", json={"resolved": True})
        assert resp.status_code == 404


# ── Transactions ──────────────────────────────────────────────

class TestTransactions:
    PAYLOAD = {
        "user_id": 1, "merchant_id": 1, "amount": 500.0,
        "currency": "INR", "channel": "UPI",
        "ip_address": "192.168.1.1", "device_id": "device_1",
    }

    def test_create_transaction(self, client):
        mock_conn = MagicMock()
        mock_cur  = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"id": 42, "txn_ref": "test-ref-001"}
        with patch("api.main.get_conn", return_value=mock_conn), \
             patch("api.main.run_rules_for_txn", return_value=[]):
            resp = client.post("/transactions", json=self.PAYLOAD)
        assert resp.status_code == 201
        assert "txn_id" in resp.json()

    def test_negative_amount_rejected(self, client):
        bad = {**self.PAYLOAD, "amount": -100}
        resp = client.post("/transactions", json=bad)
        assert resp.status_code == 422

    def test_zero_amount_rejected(self, client):
        bad = {**self.PAYLOAD, "amount": 0}
        resp = client.post("/transactions", json=bad)
        assert resp.status_code == 422

    def test_list_transactions(self, client):
        mock_rows = [
            {"id": 1, "txn_ref": "abc", "user_name": "Rahul", "merchant": "Swiggy",
             "amount": 200, "currency": "INR", "channel": "UPI", "status": "completed",
             "device_id": "d1", "ip_address": "1.1.1.1",
             "created_at": "2026-11-20", "flag_count": 0}
        ]
        with patch("api.main.query", return_value=mock_rows):
            resp = client.get("/transactions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# ── Analytics ─────────────────────────────────────────────────

class TestAnalytics:
    def test_summary(self, client):
        with patch("api.main.query", return_value=MOCK_SUMMARY):
            resp = client.get("/analytics/summary")
        assert resp.status_code == 200
        s = resp.json()
        data = s[0] if isinstance(s, list) else s
        assert "total_txns" in data
        assert "open_flags" in data

    def test_velocity(self, client):
        mock_data = [{"id": 1, "name": "Anjali", "txn_count": 7,
                      "total_amount": 6500, "first_txn": "...", "last_txn": "..."}]
        with patch("api.main.query", return_value=mock_data):
            resp = client.get("/analytics/velocity")
        assert resp.status_code == 200
        assert resp.json()[0]["txn_count"] == 7

    def test_mule_chains(self, client):
        mock_chains = [{"from_user_id": 5, "to_user_id": 11,
                        "amount": 15000, "depth": 3, "chain": [5, 11]}]
        with patch("api.main.query", return_value=mock_chains):
            resp = client.get("/analytics/mule-chains")
        assert resp.status_code == 200
        assert resp.json()[0]["depth"] == 3

    def test_device_sharing(self, client):
        mock_devs = [{"device_id": "device_mule_1", "user_count": 3,
                      "users": ["A", "B", "C"], "total_amount": 45000}]
        with patch("api.main.query", return_value=mock_devs):
            resp = client.get("/analytics/device-sharing")
        assert resp.status_code == 200
        assert resp.json()[0]["user_count"] == 3

    def test_user_risk_ranking(self, client):
        mock_rank = [{"id": 1, "name": "Rahul", "flag_count": 5,
                      "risk_percentile": 95.0, "risk_decile": 1, "rank": 1}]
        with patch("api.main.query", return_value=mock_rank):
            resp = client.get("/analytics/user-risk-ranking")
        assert resp.status_code == 200
        assert resp.json()[0]["risk_decile"] == 1

    def test_merchant_fraud_rate(self, client):
        mock_merch = [{"merchant": "WazirX", "category": "CRYPTO",
                       "day": "2026-11-20", "txns": 10, "flags": 3,
                       "flag_rate_pct": 30.0, "rolling_7d_rate": 25.0}]
        with patch("api.main.query", return_value=mock_merch):
            resp = client.get("/analytics/merchant-fraud-rate")
        assert resp.status_code == 200
        assert resp.json()[0]["rolling_7d_rate"] == 25.0

    def test_empty_analytics(self, client):
        with patch("api.main.query", return_value=[]):
            resp = client.get("/analytics/device-sharing")
        assert resp.json() == []


# ── Engine ────────────────────────────────────────────────────

class TestEngine:
    def test_run_engine(self, client):
        with patch("api.main.run_all_rules", return_value=3), \
             patch("api.main.execute", return_value=None):
            resp = client.post("/engine/run")
        assert resp.status_code == 200
        assert resp.json()["new_flags"] == 3

    def test_user_risk_stats(self, client):
        mock_stats = [{"user_id": 1, "name": "Rahul", "email": "r@e.com",
                       "total_txns": 50, "total_flags": 5, "risk_score": 72.0,
                       "total_amount": 48000, "avg_amount": 960,
                       "max_single_txn": 95000, "distinct_merchants": 4,
                       "distinct_devices": 2, "distinct_ips": 3, "last_txn_at": "..."}]
        with patch("api.main.query", return_value=mock_stats):
            resp = client.get("/users/risk-stats")
        assert resp.status_code == 200
        assert resp.json()[0]["total_flags"] == 5
