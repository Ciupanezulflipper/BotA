#!/usr/bin/env python3
"""Unit tests for ``tools/provider_limits.py`` cooldown bookkeeping."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import provider_limits


class ProviderLimitsFixture:
    """Redirect the registry to a temporary file and freeze time."""

    NOW = 1_700_000_000.0

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = Path(self._tmp.name) / "provider_limits.json"

        db_patch = patch.object(provider_limits, "DB", self.db)
        db_patch.start()
        self.addCleanup(db_patch.stop)

        self.clock = patch.object(provider_limits.time, "time", return_value=self.NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def write_db(self, payload: dict) -> None:
        self.db.write_text(json.dumps(payload))


class LoadTests(ProviderLimitsFixture, unittest.TestCase):
    def test_missing_file_returns_defaults_copy(self):
        loaded = provider_limits._load()
        self.assertEqual(loaded, provider_limits.DEFAULTS)
        loaded["yahoo"]["cooldown"] = 1.0
        self.assertEqual(provider_limits.DEFAULTS["yahoo"]["cooldown"], 90.0)

    def test_corrupt_file_falls_back_to_defaults(self):
        self.db.write_text("{not json")
        self.assertEqual(provider_limits._load(), provider_limits.DEFAULTS)

    def test_existing_file_is_used(self):
        self.write_db({"yahoo": {"last": 5.0, "cooldown": 10.0}})
        self.assertEqual(
            provider_limits._load(), {"yahoo": {"last": 5.0, "cooldown": 10.0}}
        )


class SaveTests(ProviderLimitsFixture, unittest.TestCase):
    def test_save_writes_json_and_removes_temp_file(self):
        provider_limits._save({"finnhub": {"last": 1.0, "cooldown": 2.0}})
        self.assertEqual(
            json.loads(self.db.read_text()), {"finnhub": {"last": 1.0, "cooldown": 2.0}}
        )
        self.assertFalse(self.db.with_suffix(".tmp").exists())


class ReadyTests(ProviderLimitsFixture, unittest.TestCase):
    def test_never_used_provider_is_ready(self):
        self.assertTrue(provider_limits.ready("yahoo"))

    def test_provider_inside_cooldown_is_not_ready(self):
        self.write_db({"yahoo": {"last": self.NOW - 10.0, "cooldown": 90.0}})
        self.assertFalse(provider_limits.ready("yahoo"))

    def test_provider_at_cooldown_boundary_is_ready(self):
        self.write_db({"yahoo": {"last": self.NOW - 90.0, "cooldown": 90.0}})
        self.assertTrue(provider_limits.ready("yahoo"))

    def test_unknown_provider_uses_one_second_cooldown(self):
        self.write_db({"custom": {"last": self.NOW - 0.5, "cooldown": 1.0}})
        self.assertFalse(provider_limits.ready("custom"))

        self.write_db({"other": {"last": self.NOW - 2.0}})
        self.assertTrue(provider_limits.ready("other"))

    def test_provider_absent_from_stored_registry_is_ready(self):
        self.write_db({"finnhub": {"last": self.NOW, "cooldown": 1.2}})
        self.assertTrue(provider_limits.ready("brand-new"))


class StampTests(ProviderLimitsFixture, unittest.TestCase):
    def test_stamp_records_now_and_blocks_immediate_reuse(self):
        provider_limits.stamp("yahoo")
        stored = json.loads(self.db.read_text())
        self.assertEqual(stored["yahoo"]["last"], self.NOW)
        self.assertEqual(stored["yahoo"]["cooldown"], 90.0)
        self.assertFalse(provider_limits.ready("yahoo"))

    def test_stamp_can_override_cooldown(self):
        provider_limits.stamp("yahoo", cooldown=5.0)
        self.assertEqual(json.loads(self.db.read_text())["yahoo"]["cooldown"], 5.0)

    def test_stamp_registers_unknown_provider_with_default_cooldown(self):
        provider_limits.stamp("brand-new")
        self.assertEqual(
            json.loads(self.db.read_text())["brand-new"],
            {"last": self.NOW, "cooldown": 1.0},
        )

    def test_stamp_does_not_mutate_module_defaults(self):
        provider_limits.stamp("yahoo", cooldown=5.0)
        self.assertEqual(
            provider_limits.DEFAULTS["yahoo"], {"last": 0.0, "cooldown": 90.0}
        )

        self.db.unlink()
        provider_limits.stamp("yahoo")
        self.assertEqual(json.loads(self.db.read_text())["yahoo"]["cooldown"], 90.0)

    def test_stamp_preserves_other_providers(self):
        self.write_db({"finnhub": {"last": 1.0, "cooldown": 1.2}})
        provider_limits.stamp("yahoo", cooldown=30.0)
        stored = json.loads(self.db.read_text())
        self.assertEqual(stored["finnhub"], {"last": 1.0, "cooldown": 1.2})
        self.assertEqual(stored["yahoo"], {"last": self.NOW, "cooldown": 30.0})


if __name__ == "__main__":
    unittest.main()
