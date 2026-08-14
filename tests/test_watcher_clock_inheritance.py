"""Regression coverage for watcher scan_once server-clock inheritance.

The outer tools/watcher_gated_cycle.sh already consults the market gate,
which in turn probes multiple HTTPS Date headers to derive a trusted server
epoch. That epoch is exported to child processes via BOTA_SERVER_EPOCH.

Previously the production watcher core's scan_once unconditionally re-probed
the server clock, turning a successful gate into a fail-closed skip whenever
the second probe was rate-limited, network-flapped, or DNS-throttled. These
tests pin the new contract:

  * a valid inherited BOTA_SERVER_EPOCH is reused verbatim,
  * the direct probe is only invoked when no valid parent epoch exists,
  * missing / invalid inherited epoch combined with a failed probe still
    fails closed (BOTA_SERVER_EPOCH="0" and no pair processing).

The behavior tests drive scan_once by extracting the function body from
signal_watcher_core.sh and stub out compute_server_clock_epoch /
process_pair_tf so we can observe how the trusted epoch was resolved without
doing any live network work or side-effects.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "signal_watcher_core.sh"


HARNESS_TEMPLATE = r"""
#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail

ROOT="__ROOT__"
STATE="${ROOT}/state"
LOGS="${ROOT}/logs"
mkdir -p "${STATE}" "${LOGS}"

: "${PAIRS:=EURUSD}"
: "${TIMEFRAMES:=M15}"

export ROOT STATE LOGS PAIRS TIMEFRAMES

# Extract just the scan_once function body from the production script.
# Extraction start marker matches "scan_once() {".
awk '/^scan_once\(\) \{/{flag=1} flag{print} flag && /^\}/{exit}' \
  "__SCRIPT__" > "${STATE}/scan_once.snippet"

log() {
  printf 'LOG %s %s\n' "$1" "$2" >>"${STATE}/scan.log"
}

compute_server_clock_epoch() {
  __PROBE_BODY__
}

process_pair_tf() {
  printf 'PROCESS pair=%s tf=%s epoch=%s\n' "$1" "$2" "${BOTA_SERVER_EPOCH:-}" \
    >>"${STATE}/scan.log"
}

# shellcheck disable=SC1091
source "${STATE}/scan_once.snippet"

scan_once
printf 'FINAL BOTA_SERVER_EPOCH=%s\n' "${BOTA_SERVER_EPOCH:-}" >>"${STATE}/scan.log"
"""


class ScanOnceInheritsTrustedEpochTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_harness(self, probe_body: str) -> Path:
        text = (
            HARNESS_TEMPLATE
            .replace("__ROOT__", str(self.root))
            .replace("__SCRIPT__", str(SCRIPT))
            .replace("__PROBE_BODY__", probe_body)
        )
        harness = self.root / "harness.sh"
        harness.write_text(text, encoding="utf-8")
        return harness

    def _run(self, env: dict[str, str], probe_body: str) -> str:
        harness = self._write_harness(probe_body)
        merged = os.environ.copy()
        merged.update(env)
        bash = shutil.which("bash")
        if not bash:
            self.fail("bash executable not found on PATH")
        completed = subprocess.run(  # skipcq
            [bash, str(harness)],
            env=merged,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        log = self.root / "state" / "scan.log"
        return log.read_text(encoding="utf-8") if log.exists() else ""

    def test_valid_inherited_epoch_is_reused_without_probing(self) -> None:
        probe_body = 'printf "0\n"; return 0'  # would return unusable epoch
        log = self._run(
            env={"BOTA_SERVER_EPOCH": "1786209193"},
            probe_body=probe_body,
        )
        self.assertIn("server_clock_inherited BOTA_SERVER_EPOCH=1786209193", log)
        self.assertNotIn("server_clock_unavailable", log)
        self.assertIn("PROCESS pair=EURUSD tf=M15 epoch=1786209193", log)
        self.assertIn("FINAL BOTA_SERVER_EPOCH=1786209193", log)

    def test_missing_inherited_epoch_falls_back_to_probe(self) -> None:
        probe_body = 'printf "%s\n" 1786209299; return 0'
        log = self._run(
            env={"BOTA_SERVER_EPOCH": ""},
            probe_body=probe_body,
        )
        self.assertNotIn("server_clock_inherited", log)
        self.assertIn("server_clock_ok BOTA_SERVER_EPOCH=1786209299", log)
        self.assertIn("PROCESS pair=EURUSD tf=M15 epoch=1786209299", log)

    def test_invalid_inherited_epoch_falls_back_to_probe(self) -> None:
        probe_body = 'printf "%s\n" 1786209400; return 0'
        log = self._run(
            env={"BOTA_SERVER_EPOCH": "0"},
            probe_body=probe_body,
        )
        self.assertNotIn("server_clock_inherited", log)
        self.assertIn("server_clock_ok BOTA_SERVER_EPOCH=1786209400", log)

    def test_invalid_inherited_and_failed_probe_fails_closed(self) -> None:
        probe_body = 'printf "0\n"; return 0'
        log = self._run(
            env={"BOTA_SERVER_EPOCH": "not-a-number"},
            probe_body=probe_body,
        )
        self.assertIn("server_clock_unavailable -> SKIP_SCAN fail_closed", log)
        self.assertIn("FINAL BOTA_SERVER_EPOCH=0", log)
        # process_pair_tf must NOT have run in the fail-closed path.
        self.assertNotIn("PROCESS pair=", log)

    def test_source_reuses_inherited_epoch_and_preserves_fail_closed(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("server_clock_inherited", source)
        self.assertIn('_inherited="${BOTA_SERVER_EPOCH:-0}"', source)
        self.assertIn("server_clock_unavailable -> SKIP_SCAN fail_closed", source)
        # scan_once must never trust the phone local clock — the only path
        # that sets a usable epoch flows through the numeric > 1e9 check.
        self.assertIn("_sv_epoch > 1000000000", source)


if __name__ == "__main__":
    unittest.main()
