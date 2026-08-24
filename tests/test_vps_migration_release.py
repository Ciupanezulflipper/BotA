from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "vps_orchestrator.py"
SPEC = importlib.util.spec_from_file_location("vps_orchestrator", MODULE_PATH)
assert SPEC and SPEC.loader
vps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vps)

EXPECTED_POLICY = {
    "PAIRS": "EURUSD GBPUSD USDJPY", "TIMEFRAMES": "M15",
    "POLICY_B_ENABLED": "1", "POLICY_B_SCORE_MIN": "70",
    "POLICY_B_ADX_MAX": "30", "FILTER_SCORE_MIN": "65",
    "FILTER_SCORE_MIN_ALL": "65", "NEWS_ON": "0",
    "TELEGRAM_MIN_SCORE": "70", "TELEGRAM_TIER_YELLOW_MIN": "70",
    "TELEGRAM_TIER_YELLOW_MIN_INT": "70", "TELEGRAM_TIER_GREEN_MIN": "75",
    "TELEGRAM_TIER_GREEN_MIN_INT": "75", "TELEGRAM_COOLDOWN_SECONDS": "1800",
    "CANDLE_MAX_AGE_SECS": "2700",
}


class VPSMigrationReleaseTests(unittest.TestCase):
    def test_frozen_policy_loads_exactly(self) -> None:
        self.assertEqual(vps.load_frozen_policy(ambient={}), EXPECTED_POLICY)

    def test_policy_defeats_conflicting_ambient_environment(self) -> None:
        ambient = {key: "hostile-override" for key in EXPECTED_POLICY}
        self.assertEqual(vps.load_frozen_policy(ambient=ambient), EXPECTED_POLICY)

    def test_effective_config_is_redacted_and_fingerprint_deterministic(self) -> None:
        secrets = {
            "TELEGRAM_BOT_TOKEN": "obvious-token-secret",
            "TELEGRAM_CHAT_ID": "obvious-chat-secret",
            "SUPABASE_SERVICE_KEY": "obvious-supabase-secret",
            "OANDA_API_KEY": "obvious-provider-secret",
            "PASSWORD": "obvious-credential-secret",
        }
        first = vps.effective_config_evidence(ambient=secrets)
        second = vps.effective_config_evidence(ambient=dict(reversed(list(secrets.items()))))
        emitted = json.dumps(first, sort_keys=True)
        self.assertEqual(first, second)
        for value in secrets.values():
            self.assertNotIn(value, emitted)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", emitted)
        self.assertRegex(first["fingerprint_sha256"], r"^[0-9a-f]{64}$")

    def test_missing_required_command_fails_closed(self) -> None:
        self.assertIn("jq", vps.REQUIRED_COMMANDS)
        result = vps.command_preflight(("definitely-not-a-bota-command",), path="")
        self.assertFalse(result["healthy"])
        self.assertEqual(result["missing"], ["definitely-not-a-bota-command"])

    def test_dependency_manifest_is_parsed_by_runtime_contract(self) -> None:
        self.assertEqual(vps.parse_dependency_manifest(), [
            {"name": "matplotlib", "version": "3.11.1"},
            {"name": "numpy", "version": "2.5.1"},
            {"name": "pandas", "version": "3.0.5"},
            {"name": "requests", "version": "2.34.2"},
        ])

    def test_dependency_manifest_rejects_non_exact_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.txt"
            path.write_text("requests>=2\n", encoding="utf-8")
            with self.assertRaises(vps.ContractError):
                vps.parse_dependency_manifest(path)

    def test_runtime_python_satisfies_declared_contract(self) -> None:
        self.assertEqual(vps.declared_python_contract(), ">=3.14,<3.15")
        self.assertEqual(sys.version_info[:2], (3, 14))
        self.assertTrue(vps.runtime_python_result()["healthy"])

    def test_no_legacy_runtime_authority_is_introduced(self) -> None:
        changed_contract = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8").lower()
            for relative in (
                "pyproject.toml", "requirements-runtime.txt",
                "config/production-vps.env", "tools/vps_orchestrator.py",
            )
        )
        for forbidden in ("android", "termux", "runit", "runsv", "cron"):
            self.assertNotIn(forbidden, changed_contract)


if __name__ == "__main__":
    unittest.main()
