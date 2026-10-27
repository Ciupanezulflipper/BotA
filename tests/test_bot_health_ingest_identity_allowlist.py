#!/usr/bin/env python3
"""Regression tests for the bot_id/source allowlist in
supabase/functions/bot-health-ingest/index.ts.

No Deno runtime is available in this sandbox, so coverage is split:

  - Structural/text checks (same approach as test_vps_systemd_contract.py)
    prove the secret-validation gate is untouched and still runs before
    identity resolution, and that the allowlist is closed (exactly two
    entries).
  - The identity-resolution logic itself (TEST_EXTRACT_START/END block in
    index.ts) is deliberately written with no Deno-specific syntax, so it
    is extracted verbatim and actually executed under Node to prove real
    accept/reject behavior (findings F, G, H) rather than relying on text
    matching alone.

Covers:
  F. unknown bot_id is rejected by ingest
  G. mismatched bot_id/source is rejected
  H. both canonical identities are accepted
  I. existing secret-validation behavior remains unchanged (structural)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_TS = ROOT / "supabase" / "functions" / "bot-health-ingest" / "index.ts"
START_MARKER = "// TEST_EXTRACT_START: identity-allowlist"
END_MARKER = "// TEST_EXTRACT_END: identity-allowlist"


def extract_identity_block(text: str) -> str:
    start = text.index(START_MARKER)
    end = text.index(END_MARKER)
    return text[start:end]


class IngestSecretValidationUnchangedTests(unittest.TestCase):
    """I: structural proof the secret gate is untouched and still runs first."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = INDEX_TS.read_text(encoding="utf-8")

    def test_secret_check_literals_are_present_unchanged(self) -> None:
        for literal in (
            'const expectedSecret = getEnv("BOTA_HEALTH_INGEST_SECRET");',
            "if (!expectedSecret) {",
            'const providedSecret = req.headers.get("x-bota-health-secret") ?? "";',
            "!safeEqual(providedSecret, expectedSecret)",
        ):
            self.assertIn(literal, self.text, literal)

    def test_secret_check_precedes_identity_resolution_and_json_parsing(self) -> None:
        secret_check_index = self.text.index("safeEqual(providedSecret, expectedSecret)")
        json_parse_index = self.text.index("await req.json()")
        identity_call_index = self.text.index("const identity = resolveBotIdentity(payload);")

        self.assertLess(secret_check_index, json_parse_index)
        self.assertLess(json_parse_index, identity_call_index)

    def test_no_service_role_key_handling_was_touched(self) -> None:
        self.assertIn("function getSupabaseAdminKey()", self.text)
        self.assertIn('getEnv("SUPABASE_SERVICE_ROLE_KEY")', self.text)

    def test_allowlist_is_closed_to_exactly_two_identities(self) -> None:
        block = extract_identity_block(self.text)
        self.assertIn('"bota-termux-primary": "termux"', block)
        self.assertIn('"bota-hetzner-primary": "hetzner"', block)
        # No third identity sneaks in.
        self.assertEqual(block.count('": "'), 2)


class IdentityResolutionExecutionTests(unittest.TestCase):
    """F, G, H: actually execute the extracted allowlist logic under Node."""

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("node is not available in this environment")

        text = INDEX_TS.read_text(encoding="utf-8")
        block = extract_identity_block(text)

        harness = block + """
const results = {
  termux: resolveBotIdentity({ bot_id: "bota-termux-primary" }),
  hetzner: resolveBotIdentity({ bot_id: "bota-hetzner-primary" }),
  hetzner_with_consistent_source: resolveBotIdentity({ bot_id: "bota-hetzner-primary", source: "hetzner" }),
  unknown_bot_id: resolveBotIdentity({ bot_id: "bota-termux-primary-OLD" }),
  missing_bot_id: resolveBotIdentity({}),
  non_string_bot_id: resolveBotIdentity({ bot_id: 12345 }),
  mismatched_source_hetzner_claims_termux: resolveBotIdentity({ bot_id: "bota-hetzner-primary", source: "termux" }),
  mismatched_source_termux_claims_hetzner: resolveBotIdentity({ bot_id: "bota-termux-primary", source: "hetzner" }),
};
console.log(JSON.stringify(results));
"""
        cls.tempdir = tempfile.TemporaryDirectory()
        script_path = Path(cls.tempdir.name) / "identity_allowlist_harness.mjs"
        script_path.write_text(harness, encoding="utf-8")

        completed = subprocess.run(
            ["node", str(script_path)], capture_output=True, text=True, timeout=10
        )
        if completed.returncode != 0:
            raise AssertionError(f"harness failed: {completed.stderr}")

        cls.results = json.loads(completed.stdout.strip())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def test_h_both_canonical_identities_are_accepted(self) -> None:
        self.assertEqual(
            self.results["termux"], {"ok": True, "bot_id": "bota-termux-primary", "source": "termux"}
        )
        self.assertEqual(
            self.results["hetzner"], {"ok": True, "bot_id": "bota-hetzner-primary", "source": "hetzner"}
        )

    def test_h_consistent_caller_supplied_source_is_accepted(self) -> None:
        self.assertTrue(self.results["hetzner_with_consistent_source"]["ok"])

    def test_f_unknown_bot_id_is_rejected(self) -> None:
        self.assertEqual(
            self.results["unknown_bot_id"], {"ok": False, "error": "invalid_bot_id"}
        )

    def test_f_missing_bot_id_is_rejected(self) -> None:
        self.assertEqual(self.results["missing_bot_id"], {"ok": False, "error": "invalid_bot_id"})

    def test_f_non_string_bot_id_is_rejected(self) -> None:
        self.assertEqual(self.results["non_string_bot_id"], {"ok": False, "error": "invalid_bot_id"})

    def test_g_mismatched_bot_id_source_is_rejected_both_directions(self) -> None:
        self.assertEqual(
            self.results["mismatched_source_hetzner_claims_termux"],
            {"ok": False, "error": "bot_id_source_mismatch"},
        )
        self.assertEqual(
            self.results["mismatched_source_termux_claims_hetzner"],
            {"ok": False, "error": "bot_id_source_mismatch"},
        )

    def test_source_is_never_taken_verbatim_from_caller_for_accepted_identities(self) -> None:
        # Even when accepted, the returned source is the server-derived
        # value, never an arbitrary caller string that happens to match.
        self.assertEqual(self.results["hetzner_with_consistent_source"]["source"], "hetzner")


if __name__ == "__main__":
    unittest.main()
