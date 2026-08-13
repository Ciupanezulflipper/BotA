#!/usr/bin/env python3
"""Unit tests for ``tools/risk_manager.py`` env parsing and reported state."""

from __future__ import annotations

import datetime
import re
import unittest
from unittest.mock import patch

from tools import risk_manager


class EnvFlagTests(unittest.TestCase):
    def test_accepted_truthy_spellings(self):
        for value in ("1", "true", "TRUE", "yes", "YES", " 1 "):
            with patch.dict(risk_manager.os.environ, {"FLAG": value}, clear=True):
                self.assertTrue(risk_manager._env_flag("FLAG"), value)

    def test_other_values_are_false(self):
        for value in ("0", "False", "no", "on", "", "True "):
            with patch.dict(risk_manager.os.environ, {"FLAG": value}, clear=True):
                self.assertFalse(risk_manager._env_flag("FLAG"), value)

    def test_default_is_used_when_unset(self):
        with patch.dict(risk_manager.os.environ, {}, clear=True):
            self.assertTrue(risk_manager._env_flag("FLAG", "1"))
            self.assertFalse(risk_manager._env_flag("FLAG", "0"))


class EnvIntTests(unittest.TestCase):
    def test_parses_integers_with_surrounding_space(self):
        with patch.dict(risk_manager.os.environ, {"N": " 42 "}, clear=True):
            self.assertEqual(risk_manager._env_int("N", 7), 42)

    def test_invalid_values_fall_back_to_default(self):
        for value in ("abc", "", "3.5"):
            with patch.dict(risk_manager.os.environ, {"N": value}, clear=True):
                self.assertEqual(risk_manager._env_int("N", 7), 7, value)

    def test_missing_value_falls_back_to_default(self):
        with patch.dict(risk_manager.os.environ, {}, clear=True):
            self.assertEqual(risk_manager._env_int("N", 7), 7)


class UtcTodayTests(unittest.TestCase):
    def test_returns_utc_iso_date(self):
        stamp = risk_manager.utc_today_str()
        self.assertRegex(stamp, r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(
            stamp,
            datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        )


class PolicyAccessorTests(unittest.TestCase):
    def test_defaults_match_the_documented_policy(self):
        with patch.dict(risk_manager.os.environ, {}, clear=True):
            self.assertEqual(risk_manager.daily_cap(), 30)
            self.assertFalse(risk_manager.send_wait_enabled())
            self.assertTrue(risk_manager.weekend_guard_enabled())
            self.assertTrue(risk_manager.market_block_enabled())
            self.assertFalse(risk_manager.news_blackout_enabled())

    def test_guards_can_be_disabled_explicitly(self):
        env = {
            "DAILY_CAP": "5",
            "SEND_WAIT": "1",
            "WEEKEND_GUARD_ENABLE": "0",
            "MARKET_BLOCK_ENABLE": "0",
            "NEWS_BLACKOUT_ENABLE": "1",
        }
        with patch.dict(risk_manager.os.environ, env, clear=True):
            self.assertEqual(risk_manager.daily_cap(), 5)
            self.assertTrue(risk_manager.send_wait_enabled())
            self.assertFalse(risk_manager.weekend_guard_enabled())
            self.assertFalse(risk_manager.market_block_enabled())
            self.assertTrue(risk_manager.news_blackout_enabled())


class ReportStateTests(unittest.TestCase):
    def test_report_is_json_safe_and_complete(self):
        with patch.dict(risk_manager.os.environ, {}, clear=True):
            state = risk_manager.report_state()

        self.assertEqual(
            set(state),
            {
                "utc_today",
                "send_wait",
                "daily_cap",
                "weekend_guard",
                "market_block",
                "news_blackout",
            },
        )
        self.assertIsInstance(state["daily_cap"], int)
        self.assertIsInstance(state["send_wait"], bool)
        self.assertIsInstance(state["weekend_guard"], bool)
        self.assertIsInstance(state["market_block"], bool)
        self.assertIsInstance(state["news_blackout"], bool)
        self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}", state["utc_today"]))

    def test_report_reflects_environment(self):
        with patch.dict(
            risk_manager.os.environ,
            {"DAILY_CAP": "12", "NEWS_BLACKOUT_ENABLE": "yes"},
            clear=True,
        ):
            state = risk_manager.report_state()

        self.assertEqual(state["daily_cap"], 12)
        self.assertTrue(state["news_blackout"])


if __name__ == "__main__":
    unittest.main()
