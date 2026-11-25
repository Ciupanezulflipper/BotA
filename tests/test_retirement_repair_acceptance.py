"""Offline red acceptance tests for the two approved retirement repairs.

The D1 tests exercise the deployed inline scorer decision block in isolation.
The exposure tests exercise real publisher logic against an in-memory REST fake.
Neither test reaches the network or loads live credentials.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "retirement_publisher", ROOT / "tools/supabase_publish.py"
)
assert SPEC is not None and SPEC.loader is not None
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class D1RetirementTests(unittest.TestCase):
    def decision(self, mutable_trend, release_trend=None):
        source = (ROOT / "tools/scoring_engine.sh").read_text(encoding="utf-8")
        start = source.index("# D1 trend filter")
        end = source.index("# Store pullback status", start)
        block = compile(source[start:end], "scoring_engine_d1_block", "exec")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            release, mutable = base / "release", base / "mutable"
            for directory, trend in ((release, release_trend), (mutable, mutable_trend)):
                (directory / "cache").mkdir(parents=True)
                if trend is not None:
                    (directory / "cache/d1_trend_EURUSD.json").write_text(
                        json.dumps({"trend": trend}), encoding="utf-8"
                    )
            namespace = {"os": os, "pair": "EURUSD", "direction": "BUY"}
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, {
                "ROOT": str(release), "BOTA_ROOT": str(release),
                "BOTA_MUTABLE_ROOT": str(mutable),
            }, clear=True), contextlib.redirect_stderr(stderr):
                exec(block, namespace)
            return namespace, stderr.getvalue()

    def test_mutable_d1_overrides_conflicting_release_cache(self):
        result, _ = self.decision("SELL", "BUY")
        self.assertEqual(result["d1_trend"], "SELL")
        self.assertEqual(result["direction"], "HOLD")

    def test_missing_mutable_cache_blocks_signal_even_if_release_cache_exists(self):
        result, _ = self.decision(None, "BUY")
        self.assertEqual(result["direction"], "HOLD")
        self.assertNotEqual(result["d1_trend"], "ANY")

    def test_invalid_mutable_trend_blocks_signal(self):
        result, _ = self.decision("INVALID", None)
        self.assertEqual(result["direction"], "HOLD")
        self.assertNotEqual(result["d1_trend"], "ANY")


class Response:
    def __init__(self, status, body):
        self.status, self.body = status, body

    def read(self):
        return self.body


class MemoryREST:
    def __init__(self, rows):
        self.rows = list(rows)
        self.requests = []
        self.response = None

    def request(self, method, path, body=None, headers=None):
        self.requests.append(method)
        if method == "GET":
            filters = parse_qs(urlsplit(path).query)
            def matches(row):
                for field, values in filters.items():
                    if field in ("select", "limit", "order"):
                        continue
                    for value in values:
                        if not value.startswith("eq."):
                            raise AssertionError("Unsupported REST filter: " + field)
                        actual = row.get(field)
                        target = value[3:]
                        if field in ("entry_price", "stop_loss", "take_profit"):
                            if float(actual) != float(target):
                                return False
                        elif str(actual) != target:
                            return False
                return True
            self.response = Response(200, json.dumps(
                [{"id": row["id"]} for row in self.rows if matches(row)]
            ).encode())
        elif method == "POST":
            row = json.loads(body)
            self.rows.append({"id": str(len(self.rows) + 1), **row})
            self.response = Response(201, b"")
        else:
            raise AssertionError("Unexpected HTTP method")

    def getresponse(self):
        return self.response

    def close(self):
        pass


class ActiveExposureRetirementTests(unittest.TestCase):
    def publish(self, existing_status, existing_direction="SELL"):
        existing = {
            "id": "first", "pair": "USDJPY", "direction": existing_direction,
            "timeframe": "M15", "entry_price": 158.01,
            "stop_loss": 158.5, "take_profit": 156.8,
            "status": existing_status,
        }
        rest = MemoryREST([existing])
        with mock.patch.object(publisher, "publication_lock",
                               return_value=contextlib.nullcontext()), \
             mock.patch.object(publisher.http.client, "HTTPSConnection",
                               return_value=rest), \
             mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": "offline-test-key"},
                             clear=True):
            publisher.publish_with_status(
                "USDJPY", "SELL", "157.99", "158.5", "156.8", "80", "M15", "GREEN"
            )
        return rest

    def test_second_distinct_same_pair_direction_active_is_blocked(self):
        rest = self.publish("ACTIVE")
        self.assertNotIn("POST", rest.requests)
        self.assertEqual(len(rest.rows), 1)

    def test_opposite_direction_remains_eligible(self):
        rest = self.publish("ACTIVE", "BUY")
        self.assertEqual(rest.requests.count("POST"), 1)

    def test_previous_closed_signal_allows_new_entry(self):
        rest = self.publish("CLOSED")
        self.assertEqual(rest.requests.count("POST"), 1)


if __name__ == "__main__":
    unittest.main()
