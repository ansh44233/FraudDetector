"""
Unit tests for engine/rules.py
All DB calls mocked.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.rules import (
    rule_velocity, rule_rapid_repeat,
    rule_high_risk_merchant, rule_shared_device,
    rule_mule_chain, _flag,
)


def make_cur(rows=None):
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    return cur


class TestFlagHelper:
    def test_flag_inserts_row(self):
        cur = MagicMock()
        _flag(cur, 42, "TEST_RULE", 80.0, {"key": "val"})
        assert cur.execute.called
        call_args = cur.execute.call_args[0]
        assert "INSERT INTO fraud_flags" in call_args[0]
        assert 42 in call_args[1]
        assert "TEST_RULE" in call_args[1]
        assert 80.0 in call_args[1]


class TestRuleVelocity:
    def test_no_rows_no_flags(self):
        cur = make_cur([])
        with patch("engine.rules._flag") as mock_flag:
            rule_velocity(cur)
        mock_flag.assert_not_called()

    def test_flags_when_count_exceeds_5(self):
        cur = make_cur([{"txn_id": 1, "txn_count_10m": 7}])
        with patch("engine.rules._flag") as mock_flag:
            rule_velocity(cur)
        mock_flag.assert_called_once()
        args = mock_flag.call_args[0]
        assert args[1] == 1
        assert args[2] == "VELOCITY_10M"
        assert args[3] == 85.0

    def test_no_flag_when_count_exactly_5(self):
        cur = make_cur([{"txn_id": 2, "txn_count_10m": 5}])
        with patch("engine.rules._flag") as mock_flag:
            rule_velocity(cur)
        mock_flag.assert_not_called()

    def test_multiple_rows(self):
        cur = make_cur([
            {"txn_id": 1, "txn_count_10m": 8},
            {"txn_id": 2, "txn_count_10m": 6},
            {"txn_id": 3, "txn_count_10m": 4},  # should not flag
        ])
        with patch("engine.rules._flag") as mock_flag:
            rule_velocity(cur)
        assert mock_flag.call_count == 2


class TestRuleRapidRepeat:
    def test_flags_on_fast_repeat(self):
        cur = make_cur([{"txn_id": 5, "gap_secs": 28.5}])
        with patch("engine.rules._flag") as mock_flag:
            rule_rapid_repeat(cur)
        mock_flag.assert_called_once()
        args = mock_flag.call_args[0]
        assert args[2] == "RAPID_REPEAT"
        assert args[3] == 70.0

    def test_no_rows_no_flags(self):
        cur = make_cur([])
        with patch("engine.rules._flag") as mock_flag:
            rule_rapid_repeat(cur)
        mock_flag.assert_not_called()

    def test_gap_seconds_in_details(self):
        cur = make_cur([{"txn_id": 7, "gap_secs": 45.0}])
        with patch("engine.rules._flag") as mock_flag:
            rule_rapid_repeat(cur)
        details = mock_flag.call_args[0][4]
        assert "gap_seconds" in details
        assert details["gap_seconds"] == 45.0


class TestRuleHighRiskMerchant:
    def test_flags_high_risk_merchant(self):
        cur = make_cur([{"txn_id": 10, "amount": 15000, "risk_tier": 3, "category": "CRYPTO"}])
        with patch("engine.rules._flag") as mock_flag:
            rule_high_risk_merchant(cur)
        mock_flag.assert_called_once()
        args = mock_flag.call_args[0]
        assert args[2] == "HIGH_RISK_MERCHANT"
        assert args[3] == 65.0

    def test_no_rows_no_flags(self):
        cur = make_cur([])
        with patch("engine.rules._flag") as mock_flag:
            rule_high_risk_merchant(cur)
        mock_flag.assert_not_called()


class TestRuleSharedDevice:
    def test_flags_shared_device(self):
        cur = make_cur([{"txn_id": 20, "device_id": "device_mule_1", "sharing_users": 2}])
        with patch("engine.rules._flag") as mock_flag:
            rule_shared_device(cur)
        mock_flag.assert_called_once()
        args = mock_flag.call_args[0]
        assert args[2] == "SHARED_DEVICE"
        assert args[3] == 60.0

    def test_device_id_in_details(self):
        cur = make_cur([{"txn_id": 21, "device_id": "device_x", "sharing_users": 3}])
        with patch("engine.rules._flag") as mock_flag:
            rule_shared_device(cur)
        details = mock_flag.call_args[0][4]
        assert details["device_id"] == "device_x"
        assert details["other_users"] == 3


class TestRuleMuleChain:
    def test_flags_deep_chain(self):
        cur = make_cur([{"txn_id": 30, "depth": 3}, {"txn_id": 31, "depth": 2}])
        with patch("engine.rules._flag") as mock_flag:
            rule_mule_chain(cur)
        assert mock_flag.call_count == 2
        for c in mock_flag.call_args_list:
            assert c[0][2] == "MULE_CHAIN"
            assert c[0][3] == 90.0

    def test_no_chains_no_flags(self):
        cur = make_cur([])
        with patch("engine.rules._flag") as mock_flag:
            rule_mule_chain(cur)
        mock_flag.assert_not_called()

    def test_chain_depth_in_details(self):
        cur = make_cur([{"txn_id": 32, "depth": 4}])
        with patch("engine.rules._flag") as mock_flag:
            rule_mule_chain(cur)
        details = mock_flag.call_args[0][4]
        assert details["chain_depth"] == 4


class TestRunAllRules:
    def test_run_all_returns_new_flag_count(self):
        mock_conn = MagicMock()
        mock_cur  = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        # before=5, after=8 → 3 new flags
        mock_cur.fetchone.side_effect = [{"n": 5}, {"n": 8}]

        with patch("engine.rules.get_conn", return_value=mock_conn):
            from engine.rules import run_all_rules
            result = run_all_rules()

        assert result == 3
