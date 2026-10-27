#!/usr/bin/env python3
"""Regression tests for the dual-producer (Termux/Hetzner) runtime-health
builder in tools/push_runtime_health_supabase.py.

Covers:
  A. Hetzner payload identity (bot_id=bota-hetzner-primary)
  B. Termux payload identity unchanged (bot_id=bota-termux-primary)
  C. Hetzner HEALTHY only when live, running, and required live jobs are fresh
  D. Stale/incomplete Hetzner health fails conservatively (never false HEALTHY)
  E. useful_progress timestamps map correctly to age fields

Gating-set correction (post pre-commit review):
  G1. failed/stale shadow alone does NOT prevent HEALTHY
  G2. failed/stale profitlab_delivery DOES prevent HEALTHY
  G3. missing profitlab_delivery required structure fails closed (UNKNOWN)
  G4. updater/watcher/closer/profitlab_delivery all healthy -> HEALTHY
  G5. shadow age is still reported independently of gating
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "push_runtime_health_supabase.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "bota_push_runtime_health_supabase", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = load_module()
NOW = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


# Union of the gating jobs plus "shadow" (reported but never gating), so
# fixtures include an entry for every job whose age tests might query
# without implying shadow is part of REQUIRED_LIVE_JOBS.
ALL_FIXTURE_JOBS = tuple(dict.fromkeys(MOD.REQUIRED_LIVE_JOBS + ("shadow",)))


def healthy_orchestrator_health(**overrides) -> dict:
    base = {
        "process_liveness": True,
        "lifecycle": "RUNNING",
        "last_loop_progress_utc": iso(NOW - timedelta(minutes=1)),
        "useful_progress": {
            job: {"status": "PASS", "finished_at_utc": iso(NOW - timedelta(minutes=3))}
            for job in ALL_FIXTURE_JOBS
        },
        "stale_useful_progress": {job: False for job in ALL_FIXTURE_JOBS},
    }
    base.update(overrides)
    return base


class HetznerPayloadIdentityTests(unittest.TestCase):
    def test_a_hetzner_payload_uses_canonical_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "vps_orchestrator_health.json").write_text(
                json.dumps(healthy_orchestrator_health()), encoding="utf-8"
            )

            payload = MOD.build_payload_hetzner(root)

            self.assertEqual(payload["bot_id"], "bota-hetzner-primary")
            self.assertEqual(MOD.HETZNER_BOT_ID, "bota-hetzner-primary")

    def test_detect_source_prefers_hetzner_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "vps_orchestrator_health.json").write_text("{}", encoding="utf-8")

            self.assertEqual(MOD.detect_source(root), "hetzner")

    def test_detect_source_env_override(self, ) -> None:
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = os.environ.get("BOTA_HEALTH_SOURCE")
            os.environ["BOTA_HEALTH_SOURCE"] = "hetzner"
            try:
                self.assertEqual(MOD.detect_source(root), "hetzner")
            finally:
                if previous is None:
                    os.environ.pop("BOTA_HEALTH_SOURCE", None)
                else:
                    os.environ["BOTA_HEALTH_SOURCE"] = previous

    def test_detect_source_fails_closed_when_no_state_file_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError):
                MOD.detect_source(root)


class TermuxPayloadUnchangedTests(unittest.TestCase):
    def test_b_termux_payload_identity_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "runtime_health.json").write_text(
                json.dumps({
                    "bot_mode": "HEALTHY",
                    "last_supervisor_run_utc": iso(NOW),
                    "watcher_log_age_min": 2,
                    "updater_log_age_min": 3,
                    "shadow_log_age_min": 4,
                }),
                encoding="utf-8",
            )

            payload = MOD.build_payload_termux(root)

            self.assertEqual(payload["bot_id"], "bota-termux-primary")
            self.assertEqual(MOD.TERMUX_BOT_ID, "bota-termux-primary")
            self.assertEqual(payload["bot_mode"], "HEALTHY")
            self.assertEqual(payload["watcher_log_age_min"], 2)

    def test_detect_source_falls_back_to_termux_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "runtime_health.json").write_text("{}", encoding="utf-8")

            self.assertEqual(MOD.detect_source(root), "termux")

    def test_build_payload_dispatches_to_termux_when_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "runtime_health.json").write_text(
                json.dumps({"bot_mode": "DEGRADED"}), encoding="utf-8"
            )

            payload = MOD.build_payload(root)

            self.assertEqual(payload["bot_id"], "bota-termux-primary")
            self.assertEqual(payload["bot_mode"], "DEGRADED")


class HetznerBotModeDerivationTests(unittest.TestCase):
    """C + D: fail-closed derivation — HEALTHY only when fully verified."""

    def test_required_live_jobs_is_exactly_the_corrected_gating_set(self) -> None:
        self.assertEqual(
            MOD.REQUIRED_LIVE_JOBS, ("updater", "watcher", "closer", "profitlab_delivery")
        )
        self.assertNotIn("shadow", MOD.REQUIRED_LIVE_JOBS)

    def test_g4_updater_watcher_closer_profitlab_delivery_all_healthy_yields_healthy(self) -> None:
        mode, reasons = MOD.derive_hetzner_bot_mode(healthy_orchestrator_health())
        self.assertEqual(mode, "HEALTHY")
        self.assertEqual(reasons, [])

    def test_c_healthy_when_live_running_and_all_core_jobs_fresh(self) -> None:
        # Retained under its original name for continuity with the Stage 1
        # review; behavior is identical to test_g4 above.
        mode, reasons = MOD.derive_hetzner_bot_mode(healthy_orchestrator_health())
        self.assertEqual(mode, "HEALTHY")
        self.assertEqual(reasons, [])

    def test_d_missing_required_fields_yields_unknown_not_healthy(self) -> None:
        mode, reasons = MOD.derive_hetzner_bot_mode({"lifecycle": "RUNNING"})
        self.assertEqual(mode, "UNKNOWN")
        self.assertIn("missing_required_fields", reasons)

    def test_d_malformed_required_fields_yields_unknown(self) -> None:
        bad = healthy_orchestrator_health(process_liveness="yes")
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "UNKNOWN")
        self.assertIn("malformed_required_fields", reasons)

    def test_d_process_not_live_yields_degraded_not_healthy(self) -> None:
        bad = healthy_orchestrator_health(process_liveness=False)
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "DEGRADED")
        self.assertIn("process_not_live", reasons)

    def test_d_lifecycle_not_running_yields_degraded(self) -> None:
        for lifecycle in ("STARTING", "STOPPING", "STOPPED"):
            with self.subTest(lifecycle=lifecycle):
                bad = healthy_orchestrator_health(lifecycle=lifecycle)
                mode, reasons = MOD.derive_hetzner_bot_mode(bad)
                self.assertEqual(mode, "DEGRADED")
                self.assertIn(f"lifecycle_{lifecycle.lower()}", reasons)

    def test_d_stale_core_job_yields_degraded_not_healthy(self) -> None:
        bad = healthy_orchestrator_health()
        bad["stale_useful_progress"]["watcher"] = True
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "DEGRADED")
        self.assertIn("stale:watcher", reasons)

    def test_d_failed_core_job_status_yields_degraded_not_healthy(self) -> None:
        bad = healthy_orchestrator_health()
        bad["useful_progress"]["closer"] = {
            "status": "FAILED",
            "finished_at_utc": iso(NOW - timedelta(minutes=1)),
        }
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "DEGRADED")
        self.assertIn("status:closer=FAILED", reasons)

    def test_g3_missing_profitlab_delivery_required_structure_fails_closed(self) -> None:
        bad = healthy_orchestrator_health()
        del bad["useful_progress"]["profitlab_delivery"]
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "UNKNOWN")
        self.assertIn("missing_job_progress:profitlab_delivery", reasons)

    def test_g3_profitlab_delivery_missing_from_stale_map_also_fails_closed(self) -> None:
        bad = healthy_orchestrator_health()
        del bad["stale_useful_progress"]["profitlab_delivery"]
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "UNKNOWN")
        self.assertIn("missing_job_progress:profitlab_delivery", reasons)

    def test_d_non_dict_health_yields_unknown(self) -> None:
        mode, _reasons = MOD.derive_hetzner_bot_mode(None)  # type: ignore[arg-type]
        self.assertEqual(mode, "UNKNOWN")

    def test_g1_stale_shadow_alone_does_not_prevent_healthy(self) -> None:
        good = healthy_orchestrator_health()
        good["stale_useful_progress"]["shadow"] = True
        mode, reasons = MOD.derive_hetzner_bot_mode(good)
        self.assertEqual(mode, "HEALTHY")
        self.assertEqual(reasons, [])

    def test_g1_failed_shadow_status_alone_does_not_prevent_healthy(self) -> None:
        good = healthy_orchestrator_health()
        good["useful_progress"]["shadow"] = {
            "status": "FAILED",
            "finished_at_utc": iso(NOW - timedelta(minutes=1)),
        }
        mode, reasons = MOD.derive_hetzner_bot_mode(good)
        self.assertEqual(mode, "HEALTHY")
        self.assertEqual(reasons, [])

    def test_g1_shadow_entirely_absent_does_not_prevent_healthy(self) -> None:
        good = healthy_orchestrator_health()
        del good["useful_progress"]["shadow"]
        del good["stale_useful_progress"]["shadow"]
        mode, reasons = MOD.derive_hetzner_bot_mode(good)
        self.assertEqual(mode, "HEALTHY")
        self.assertEqual(reasons, [])

    def test_g2_stale_profitlab_delivery_prevents_healthy(self) -> None:
        bad = healthy_orchestrator_health()
        bad["stale_useful_progress"]["profitlab_delivery"] = True
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "DEGRADED")
        self.assertIn("stale:profitlab_delivery", reasons)

    def test_g2_failed_profitlab_delivery_status_prevents_healthy(self) -> None:
        for status in ("FAILED", "TIMED_OUT", "LAUNCH_ERROR", "SKIPPED_OVERLAP", "NOT_RUN"):
            with self.subTest(status=status):
                bad = healthy_orchestrator_health()
                bad["useful_progress"]["profitlab_delivery"] = {
                    "status": status,
                    "finished_at_utc": iso(NOW - timedelta(minutes=1)),
                }
                mode, reasons = MOD.derive_hetzner_bot_mode(bad)
                self.assertEqual(mode, "DEGRADED")
                self.assertIn(f"status:profitlab_delivery={status}", reasons)

    def test_g2_malformed_profitlab_delivery_record_prevents_healthy(self) -> None:
        bad = healthy_orchestrator_health()
        bad["useful_progress"]["profitlab_delivery"] = "not-a-dict"
        mode, reasons = MOD.derive_hetzner_bot_mode(bad)
        self.assertEqual(mode, "DEGRADED")
        self.assertIn("status:profitlab_delivery=None", reasons)

    def test_full_hetzner_payload_never_emits_healthy_when_a_required_live_job_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            health = healthy_orchestrator_health()
            health["stale_useful_progress"]["updater"] = True
            (state / "vps_orchestrator_health.json").write_text(
                json.dumps(health), encoding="utf-8"
            )

            payload = MOD.build_payload_hetzner(root)

            self.assertEqual(payload["bot_mode"], "DEGRADED")
            self.assertNotEqual(payload["bot_mode"], "HEALTHY")


class AgeFieldMappingTests(unittest.TestCase):
    """E: useful_progress timestamps map correctly to age fields."""

    def test_age_minutes_from_iso_computes_exact_minutes(self) -> None:
        then = NOW - timedelta(minutes=7)
        self.assertEqual(MOD.age_minutes_from_iso(iso(then), now=NOW), 7)

    def test_age_minutes_from_iso_none_when_missing(self) -> None:
        self.assertIsNone(MOD.age_minutes_from_iso(None, now=NOW))
        self.assertIsNone(MOD.age_minutes_from_iso("", now=NOW))
        self.assertIsNone(MOD.age_minutes_from_iso("not-a-timestamp", now=NOW))

    def test_age_minutes_from_iso_clamps_negative_to_zero(self) -> None:
        future = NOW + timedelta(minutes=5)
        self.assertEqual(MOD.age_minutes_from_iso(iso(future), now=NOW), 0)

    def test_full_hetzner_payload_maps_each_job_age_field_independently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            health = healthy_orchestrator_health()
            ages_minutes = {"updater": 1, "watcher": 2, "shadow": 3, "closer": 4}
            # build_payload_hetzner computes ages against real wall-clock
            # "now" (age_minutes_from_iso's default), not the fixed NOW used
            # elsewhere in this file, so timestamps here are relative to it.
            real_now = datetime.now(timezone.utc)
            for job, minutes in ages_minutes.items():
                health["useful_progress"][job] = {
                    "status": "PASS",
                    "finished_at_utc": iso(real_now - timedelta(minutes=minutes)),
                }
            (state / "vps_orchestrator_health.json").write_text(
                json.dumps(health), encoding="utf-8"
            )

            payload = MOD.build_payload_hetzner(root)

            self.assertEqual(payload["updater_log_age_min"], 1)
            self.assertEqual(payload["watcher_log_age_min"], 2)
            self.assertEqual(payload["shadow_log_age_min"], 3)
            self.assertEqual(payload["closer_log_age_min"], 4)

    def test_full_hetzner_payload_leaves_unsupported_fields_null(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (state / "vps_orchestrator_health.json").write_text(
                json.dumps(healthy_orchestrator_health()), encoding="utf-8"
            )

            payload = MOD.build_payload_hetzner(root)

            for field in MOD.HETZNER_NULL_FIELDS:
                self.assertIsNone(payload[field], field)

    def test_g5_shadow_age_is_reported_even_when_shadow_is_stale_and_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            health = healthy_orchestrator_health()
            real_now = datetime.now(timezone.utc)
            health["stale_useful_progress"]["shadow"] = True
            health["useful_progress"]["shadow"] = {
                "status": "FAILED",
                "finished_at_utc": iso(real_now - timedelta(minutes=42)),
            }
            (state / "vps_orchestrator_health.json").write_text(
                json.dumps(health), encoding="utf-8"
            )

            payload = MOD.build_payload_hetzner(root)

            # Reported regardless of gating status.
            self.assertEqual(payload["shadow_log_age_min"], 42)
            # And gating is entirely unaffected by shadow's bad state.
            self.assertEqual(payload["bot_mode"], "HEALTHY")

    def test_full_hetzner_payload_missing_job_age_is_null_not_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            health = healthy_orchestrator_health()
            del health["useful_progress"]["watcher"]["finished_at_utc"]
            (state / "vps_orchestrator_health.json").write_text(
                json.dumps(health), encoding="utf-8"
            )

            payload = MOD.build_payload_hetzner(root)

            self.assertIsNone(payload["watcher_log_age_min"])


if __name__ == "__main__":
    unittest.main()
