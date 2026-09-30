#!/usr/bin/env python3
"""Unit tests for ``tools/api_circuit_breaker.py`` quota accounting."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from tools import api_circuit_breaker


FIXED_NOW = datetime(2026, 8, 13, 12, 0, 0)


class FrozenDatetime(datetime):
    """``datetime`` subclass whose ``now()`` is pinned to ``FIXED_NOW``."""

    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW


class CircuitBreakerFixture:
    """Isolated state file and frozen clock instead of the real home path."""

    today = str(FIXED_NOW.date())

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state_file = Path(self._tmp.name) / "logs" / ".api_state.json"
        for attribute, value in (
            ("STATE_FILE", self.state_file),
            ("datetime", FrozenDatetime),
        ):
            patcher = patch.object(api_circuit_breaker, attribute, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_state(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state))


class LoadStateTests(CircuitBreakerFixture, unittest.TestCase):
    def test_missing_file_yields_empty_today_state(self):
        state = api_circuit_breaker.load_state()
        self.assertEqual(state, {"date": self.today, "calls": {}})
        self.assertFalse(self.state_file.exists())

    def test_same_day_state_is_preserved(self):
        self.write_state({"date": self.today, "calls": {"twelvedata": 3}})
        self.assertEqual(
            api_circuit_breaker.load_state(),
            {"date": self.today, "calls": {"twelvedata": 3}},
        )

    def test_stale_day_state_is_reset(self):
        yesterday = str(FIXED_NOW.date() - timedelta(days=1))
        self.write_state({"date": yesterday, "calls": {"twelvedata": 700}})
        self.assertEqual(
            api_circuit_breaker.load_state(), {"date": self.today, "calls": {}}
        )


class SaveStateTests(CircuitBreakerFixture, unittest.TestCase):
    def test_creates_parent_directory_and_round_trips(self):
        state = {"date": self.today, "calls": {"finnhub": 2}}
        api_circuit_breaker.save_state(state)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(json.loads(self.state_file.read_text()), state)


class RecordCallTests(CircuitBreakerFixture, unittest.TestCase):
    def test_first_call_starts_at_one_and_persists(self):
        self.assertEqual(api_circuit_breaker.record_call("twelvedata"), 1)
        self.assertEqual(
            json.loads(self.state_file.read_text())["calls"]["twelvedata"], 1
        )

    def test_repeated_calls_accumulate(self):
        for expected in (1, 2, 3):
            self.assertEqual(api_circuit_breaker.record_call("twelvedata"), expected)

    def test_default_provider_is_twelvedata(self):
        api_circuit_breaker.record_call()
        self.assertEqual(
            json.loads(self.state_file.read_text())["calls"], {"twelvedata": 1}
        )

    def test_providers_are_counted_independently(self):
        api_circuit_breaker.record_call("twelvedata")
        api_circuit_breaker.record_call("finnhub")
        self.assertEqual(
            json.loads(self.state_file.read_text())["calls"],
            {"twelvedata": 1, "finnhub": 1},
        )

    def test_stale_day_counter_restarts(self):
        yesterday = str(FIXED_NOW.date() - timedelta(days=1))
        self.write_state({"date": yesterday, "calls": {"twelvedata": 500}})
        self.assertEqual(api_circuit_breaker.record_call("twelvedata"), 1)


class CheckQuotaTests(CircuitBreakerFixture, unittest.TestCase):
    def test_unused_provider_reports_full_quota(self):
        report = api_circuit_breaker.check_quota("alphavantage")
        self.assertEqual(report["calls_today"], 0)
        self.assertEqual(report["limit"], api_circuit_breaker.LIMITS["alphavantage"])
        self.assertEqual(report["remaining"], report["limit"])
        self.assertEqual(report["percent_used"], 0.0)
        self.assertTrue(report["ok"])

    def test_unknown_provider_uses_fallback_limit(self):
        report = api_circuit_breaker.check_quota("unknown-provider")
        self.assertEqual(report["limit"], 800)

    def test_stays_ok_just_below_ninety_percent(self):
        limit = api_circuit_breaker.LIMITS["twelvedata"]
        self.write_state(
            {"date": self.today, "calls": {"twelvedata": int(limit * 0.9) - 1}}
        )
        self.assertTrue(api_circuit_breaker.check_quota("twelvedata")["ok"])

    def test_trips_at_ninety_percent(self):
        limit = api_circuit_breaker.LIMITS["twelvedata"]
        self.write_state({"date": self.today, "calls": {"twelvedata": int(limit * 0.9)}})
        report = api_circuit_breaker.check_quota("twelvedata")
        self.assertFalse(report["ok"])
        self.assertEqual(report["percent_used"], 90.0)

    def test_exhausted_quota_reports_negative_remaining(self):
        limit = api_circuit_breaker.LIMITS["alphavantage"]
        self.write_state({"date": self.today, "calls": {"alphavantage": limit + 5}})
        report = api_circuit_breaker.check_quota("alphavantage")
        self.assertEqual(report["remaining"], -5)
        self.assertFalse(report["ok"])


class GetStatusTests(CircuitBreakerFixture, unittest.TestCase):
    def test_covers_every_known_provider(self):
        status = api_circuit_breaker.get_status()
        self.assertEqual(
            {row["provider"] for row in status}, set(api_circuit_breaker.LIMITS)
        )
        for row in status:
            self.assertEqual(row["limit"], api_circuit_breaker.LIMITS[row["provider"]])
            self.assertEqual(row["remaining"], row["limit"] - row["calls"])

    def test_recorded_calls_are_visible(self):
        self.write_state({"date": self.today, "calls": {"twelvedata": 400}})
        rows = [
            r for r in api_circuit_breaker.get_status() if r["provider"] == "twelvedata"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["calls"], 400)
        self.assertEqual(rows[0]["percent"], 50.0)


if __name__ == "__main__":
    unittest.main()
