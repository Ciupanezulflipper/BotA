from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, HERE / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


health_push = load_module("push_runtime_health_security_test", "tools/push_runtime_health_supabase.py")


class IngestUrlValidationTests(unittest.TestCase):
    def test_canonical_url_accepted(self):
        url = "https://ozgkeslgjqbqfewojnmr.supabase.co/functions/v1/bot-health-ingest"
        self.assertIsNone(health_push.validate_ingest_url(url))

    def test_plaintext_scheme_rejected(self):
        url = "http://ozgkeslgjqbqfewojnmr.supabase.co/functions/v1/bot-health-ingest"
        self.assertEqual(health_push.validate_ingest_url(url), "scheme_not_https")

    def test_foreign_host_rejected(self):
        self.assertEqual(
            health_push.validate_ingest_url("https://attacker.example/collect"),
            "host_not_allowed",
        )

    def test_lookalike_host_rejected(self):
        self.assertEqual(
            health_push.validate_ingest_url(
                "https://ozgkeslgjqbqfewojnmr.supabase.co.attacker.example/x"
            ),
            "host_not_allowed",
        )

    def test_credentials_in_url_rejected(self):
        self.assertEqual(
            health_push.validate_ingest_url(
                "https://user:pass@ozgkeslgjqbqfewojnmr.supabase.co/functions/v1/bot-health-ingest"
            ),
            "credentials_in_url",
        )


class TelegramPairValidationTests(unittest.TestCase):
    def setUp(self):
        self.controller = load_module("tele_control_security_test", "archive/tele_control.py")

    def test_valid_pairs_are_normalised(self):
        self.assertEqual(self.controller.valid_pairs(["eurusd", " GBPUSD "]), ["EURUSD", "GBPUSD"])

    def test_shell_metacharacters_rejected(self):
        hostile = ["EURUSD; rm -rf ~", "$(id)", "`id`", "EURUSD'&&id&&'", "EU RUSD"]
        self.assertEqual(self.controller.valid_pairs(hostile), [])

    def test_analyze_argv_passes_pairs_via_environment(self):
        argv, env = self.controller.analyze_argv(["EURUSD", "GBPUSD"])
        self.assertTrue(argv[0].endswith("analyze_now.sh"))
        self.assertEqual(len(argv), 1)
        self.assertEqual(env["ANALYZE_PAIRS"], "EURUSD,GBPUSD")


if __name__ == "__main__":
    unittest.main()
