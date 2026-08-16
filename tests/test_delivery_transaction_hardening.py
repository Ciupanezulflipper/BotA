#!/usr/bin/env python3
"""Regressions for the watcher Telegram->Supabase transaction boundary."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


recovery = load_module("watcher_pending_delivery_recovery_test", TOOLS / "watcher_pending_delivery_recovery.py")
contract = load_module("watcher_cycle_contract_transaction_test", TOOLS / "watcher_cycle_contract.py")
supabase = load_module("supabase_publish_transaction_test", TOOLS / "supabase_publish.py")


IDENTITY = {
    "pair": "EURUSD",
    "timeframe": "M15",
    "direction": "BUY",
    "score": "84.90",
    "entry": "1.35379",
    "sl": "1.35222",
    "tp": "1.35692",
}


def legacy_hash(identity: dict[str, str]) -> str:
    raw = "|".join(identity[k] for k in ("pair", "timeframe", "direction", "score", "entry", "sl", "tp"))
    return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()


def core_functions(start: str, end: str) -> str:
    source = (TOOLS / "signal_watcher_core.sh").read_text(encoding="utf-8")
    return source[source.index(f"{start}() {{"):source.index(f"{end}() {{")]


class WatcherHashFallbackTests(unittest.TestCase):
    def run_hash(self, *, md5sum_body: str | None, python_body: str | None = None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td)
            if md5sum_body is not None:
                md5sum = bin_dir / "md5sum"
                md5sum.write_text(f"#!/bin/sh\n{md5sum_body}\n", encoding="utf-8")
                md5sum.chmod(0o755)
            python3 = bin_dir / "python3"
            if python_body is None:
                python3.symlink_to(sys.executable)
            else:
                python3.write_text(f"#!/bin/sh\n{python_body}\n", encoding="utf-8")
                python3.chmod(0o755)
            script = core_functions("signal_delivery_hash", "raw_cache_path") + "\n" + (
                'signal_delivery_hash EURUSD M15 BUY 84.90 1.35379 1.35222 1.35692\n'
            )
            env = os.environ.copy()
            env["PATH"] = str(bin_dir)
            return subprocess.run(
                ["/bin/bash", "-c", script], env=env, capture_output=True, text=True, check=False
            )

    def test_python_fallback_matches_recovery_md5_when_md5sum_unavailable(self) -> None:
        completed = self.run_hash(md5sum_body=None)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, legacy_hash(IDENTITY))
        self.assertRegex(completed.stdout, r"^[0-9a-f]{32}$")
        self.assertEqual(completed.stdout, completed.stdout.lower())

    def test_python_fallback_is_used_when_md5sum_fails(self) -> None:
        completed = self.run_hash(md5sum_body="exit 1")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, legacy_hash(IDENTITY))

    def test_hash_generation_failure_fails_closed(self) -> None:
        completed = self.run_hash(md5sum_body="exit 1", python_body="exit 1")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")


class WatcherAtomicDeliveryMarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.bin_dir = self.root / "bin"
        self.state.mkdir()
        self.bin_dir.mkdir()
        self.hash_file = self.state / "last_hash_EURUSD_M15.txt"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def install_command(self, name: str, body: str) -> None:
        command = self.bin_dir / name
        command.write_text(f"#!/bin/bash\n{body}\n", encoding="utf-8")
        command.chmod(0o755)

    def run_mark(self) -> subprocess.CompletedProcess[str]:
        script = core_functions("signal_delivery_hash", "complete_delivery_transaction") + "\n" + (
            "signal_delivery_mark EURUSD M15 BUY 84.90 1.35379 1.35222 1.35692\n"
        )
        env = os.environ.copy()
        env["STATE"] = str(self.state)
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        return subprocess.run(
            ["/bin/bash", "-c", script], env=env, capture_output=True, text=True, check=False
        )

    def temporary_files(self) -> list[Path]:
        return list(self.state.glob("last_hash_EURUSD_M15.txt.tmp.*"))

    def test_successful_mark_writes_complete_expected_hash(self) -> None:
        completed = self.run_mark()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.hash_file.read_text(encoding="utf-8"), legacy_hash(IDENTITY))

    def test_write_failure_preserves_committed_hash_and_returns_nonzero(self) -> None:
        self.hash_file.write_text("previous-valid-hash", encoding="utf-8")
        self.install_command(
            "mktemp",
            'temp="$(/usr/bin/mktemp "$1")" || exit 1\nchmod 400 "${temp}"\nprintf \'%s\\n\' "${temp}"',
        )

        completed = self.run_mark()

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.hash_file.read_text(encoding="utf-8"), "previous-valid-hash")
        self.assertEqual(self.temporary_files(), [])

    def test_rename_failure_preserves_committed_hash_and_returns_nonzero(self) -> None:
        self.hash_file.write_text("previous-valid-hash", encoding="utf-8")
        self.install_command("mv", "exit 1")

        completed = self.run_mark()

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(self.hash_file.read_text(encoding="utf-8"), "previous-valid-hash")
        self.assertEqual(self.temporary_files(), [])

    def test_successful_replacement_leaves_no_temporary_residue(self) -> None:
        self.hash_file.write_text("previous-valid-hash", encoding="utf-8")

        completed = self.run_mark()

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(self.hash_file.read_text(encoding="utf-8"), legacy_hash(IDENTITY))
        self.assertEqual(self.temporary_files(), [])


class GreenDeliveryPrerequisiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tools = self.root / "tools"
        self.state = self.root / "state"
        self.tools.mkdir()
        self.state.mkdir()
        self.result_log = self.state / "watcher_supabase.test.jsonl"
        self.result_log.touch(mode=0o600)
        self.marker = self.root / "delivery-marked"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_transaction(
        self, *, install_publisher: bool, key: str = "", publisher_source: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        publisher = self.tools / "supabase_publish.py"
        if publisher_source is not None:
            publisher.write_text(publisher_source, encoding="utf-8")
        elif install_publisher:
            shutil.copy2(TOOLS / "supabase_publish.py", publisher)
        elif publisher.exists():
            publisher.unlink()
        script = core_functions("complete_delivery_transaction", "raw_cache_path") + "\n" + (
            'log() { printf "%s\\n" "$*" >&2; }\n'
            'signal_delivery_mark() { : > "${MARKER}"; }\n'
            'complete_delivery_transaction GREEN EURUSD M15 BUY 84.90 84 1.35379 1.35222 1.35692\n'
        )
        env = os.environ.copy()
        env.update({
            "TOOLS": str(self.tools), "ERRLOG": str(self.root / "error.log"),
            "MARKER": str(self.marker), "BOTA_ROOT": str(self.root),
            "BOTA_CYCLE_ID": "cycle-1", "BOTA_SUPABASE_RESULT_LOG": str(self.result_log),
            "SUPABASE_SERVICE_KEY": key,
        })
        return subprocess.run(
            ["bash", "-c", script], env=env, capture_output=True, text=True, check=False
        )

    def test_missing_service_key_fails_without_committing_delivery(self) -> None:
        completed = self.run_transaction(install_publisher=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(self.marker.exists())
        evidence = json.loads(self.result_log.read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"], "failed_missing_service_key")
        self.assertEqual(evidence["cycle_id"], "cycle-1")

    def test_missing_publisher_fails_without_committing_delivery(self) -> None:
        completed = self.run_transaction(install_publisher=False, key="configured")
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(self.marker.exists())
        self.assertIn("publisher missing", completed.stderr)
        self.assertEqual(self.result_log.read_text(encoding="utf-8"), "")

        retry = self.run_transaction(
            install_publisher=True, key="configured", publisher_source="raise SystemExit(0)\n"
        )
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertTrue(self.marker.exists())

    def test_publisher_failure_fails_without_committing_delivery(self) -> None:
        completed = self.run_transaction(
            install_publisher=True, key="configured", publisher_source="raise SystemExit(1)\n"
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(self.marker.exists())
        self.assertIn("publish failed", completed.stderr)


class PendingDeliveryRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "logs" / "state").mkdir(parents=True)
        (self.root / "state" / "telegram_delivery").mkdir(parents=True)
        self.env = mock.patch.dict(
            os.environ,
            {
                "BOTA_ROOT": str(self.root),
                "BOTA_DELIVERY_STATE_DIR": str(self.root / "logs" / "state"),
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def write_sent_state(self, name: str, *, monotonic_ns: int, identity: dict[str, str] | None = None) -> None:
        payload = {
            "status": "sent",
            "identity": dict(identity or IDENTITY),
            "server_epoch": 1_786_000_000,
            "monotonic_ns": monotonic_ns,
        }
        (self.root / "state" / "telegram_delivery" / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_pending_confirmed_send_clears_only_cooldown(self) -> None:
        self.write_sent_state("pending.json", monotonic_ns=200)
        state = self.root / "logs" / "state"
        cooldown = state / "last_sent_EURUSD_M15.txt"
        cooldown.write_text("boot 123\n", encoding="utf-8")
        old_hash = state / "last_hash_EURUSD_M15.txt"
        old_hash.write_text("different-prior-signal", encoding="utf-8")

        self.assertEqual(recovery.main(), 0)
        self.assertFalse(cooldown.exists())
        self.assertEqual(old_hash.read_text(encoding="utf-8"), "different-prior-signal")

    def test_fully_committed_latest_send_preserves_cooldown(self) -> None:
        self.write_sent_state("older.json", monotonic_ns=100, identity={**IDENTITY, "score": "80.00"})
        self.write_sent_state("latest.json", monotonic_ns=200)
        state = self.root / "logs" / "state"
        cooldown = state / "last_sent_EURUSD_M15.txt"
        cooldown.write_text("boot 123\n", encoding="utf-8")
        (state / "last_hash_EURUSD_M15.txt").write_text(legacy_hash(IDENTITY), encoding="utf-8")

        self.assertEqual(recovery.main(), 0)
        self.assertTrue(cooldown.exists())


class DeferredTelegramCommitTests(unittest.TestCase):
    def test_boundary_finalizer_emits_evidence_without_legacy_markers(self) -> None:
        # Import under the canonical module name expected by the adapter.
        delivery = load_module("telegram_delivery", TOOLS / "telegram_delivery.py")
        adapter = load_module("telegram_delivery_boundary_test", TOOLS / "telegram_delivery_boundary.py")
        with mock.patch.object(delivery, "emit_cycle_result", return_value=True) as emit, \
             mock.patch.object(delivery, "prepare_legacy_cooldown") as cooldown, \
             mock.patch.object(delivery, "commit_legacy_delivery_hash") as commit_hash:
            self.assertTrue(adapter._finalize_after_telegram_only(IDENTITY, {}, "sent", {"message_id": 1}))
        emit.assert_called_once()
        cooldown.assert_not_called()
        commit_hash.assert_not_called()


class CanonicalChartSuppressionTests(unittest.TestCase):
    def test_canonical_boundary_does_not_create_chart_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "logs" / "tmp" / "chart_EURUSD_M15_1.png"
            out.parent.mkdir(parents=True)
            env = os.environ.copy()
            env.update({"BOTA_ROOT": str(root), "BOTA_CANONICAL_WATCHER_BOUNDARY": "1"})
            proc = subprocess.run(
                [
                    sys.executable,
                    str(TOOLS / "chart_generator.py"),
                    "--pair", "EURUSD", "--tf", "M15", "--direction", "BUY",
                    "--entry", "1.1", "--sl", "1.0", "--tp", "1.2",
                    "--score", "80", "--confidence", "80", "--out", str(out),
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(out.exists())
            self.assertIn("SKIP untracked photo delivery", proc.stderr)


class SupabaseEvidenceWriteTests(unittest.TestCase):
    def test_zero_byte_write_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = root / "state"
            state.mkdir()
            result = state / "watcher_supabase.zero.jsonl"
            result.write_text("", encoding="utf-8")
            result.chmod(0o600)
            with mock.patch.dict(
                os.environ,
                {
                    "BOTA_ROOT": str(root),
                    "BOTA_SUPABASE_RESULT_LOG": str(result),
                    "BOTA_CYCLE_ID": "cycle-1",
                },
                clear=False,
            ), mock.patch.object(supabase.os, "write", return_value=0):
                self.assertFalse(
                    supabase.emit_cycle_result(
                        pair="EURUSD", direction="BUY", entry="1.1", tf="M15", tier="GREEN", status="published"
                    )
                )


class SupabaseContractHardeningTests(unittest.TestCase):
    def row(self, *, tier: str = "GREEN") -> dict[str, str]:
        return {
            "pair": "EURUSD", "timeframe": "M15", "direction": "BUY",
            "score": "84.90", "entry": "1.35379", "sl": "1.35222", "tp": "1.35692",
            "rejected": "false", "tier": tier,
        }

    def test_unexpected_scope_is_rejected(self) -> None:
        rows = {("EURUSD", "M15"): self.row()}
        record = {
            "cycle_id": "cycle-1", "pair": "GBPUSD", "timeframe": "M15",
            "direction": "BUY", "entry": "1.2", "tier": "GREEN", "status": "published",
        }
        with self.assertRaisesRegex(ValueError, "supabase_scope_unexpected"):
            contract.validate_supabase(rows, [record], "cycle-1", set())

    def test_green_cannot_be_skipped_non_green(self) -> None:
        rows = {("EURUSD", "M15"): self.row()}
        record = {
            "cycle_id": "cycle-1", "pair": "EURUSD", "timeframe": "M15",
            "direction": "BUY", "entry": "1.35379", "tier": "GREEN", "status": "skipped_non_green",
        }
        with self.assertRaisesRegex(ValueError, "supabase_green_status_invalid"):
            contract.validate_supabase(rows, [record], "cycle-1", {("EURUSD", "M15")})

    def test_green_sent_requires_supabase_evidence_even_without_service_key(self) -> None:
        rows = {("EURUSD", "M15"): self.row()}
        with mock.patch.dict(os.environ, {"SUPABASE_SERVICE_KEY": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "supabase_evidence_missing_after_telegram_send"):
                contract.validate_supabase(rows, [], "cycle-1", {("EURUSD", "M15")})


if __name__ == "__main__":
    unittest.main()
