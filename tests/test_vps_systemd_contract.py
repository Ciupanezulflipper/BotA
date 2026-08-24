from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "ops/systemd/bota.service"
ORCHESTRATOR = ROOT / "tools/vps_orchestrator.py"
SPEC = importlib.util.spec_from_file_location("vps_systemd_contract", ORCHESTRATOR)
assert SPEC and SPEC.loader
vps = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vps
SPEC.loader.exec_module(vps)


def directives(text: str) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "[")):
            continue
        key, value = line.split("=", 1)
        parsed.setdefault(key, []).append(value)
    return parsed


class VPSSystemdContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = UNIT.read_text(encoding="utf-8")
        cls.unit = directives(cls.text)

    def one(self, key: str) -> str:
        self.assertEqual(len(self.unit.get(key, [])), 1, key)
        return self.unit[key][0]

    def test_exactly_one_vps_bota_service_and_no_timer(self) -> None:
        self.assertEqual(list((ROOT / "ops/systemd").glob("*.service")), [UNIT])
        self.assertEqual(list((ROOT / "ops/systemd").glob("*.timer")), [])

    def test_identity_and_simple_process_contract(self) -> None:
        self.assertEqual(self.one("User"), "bota")
        self.assertEqual(self.one("Group"), "bota")
        self.assertEqual(self.one("Type"), "simple")
        self.assertEqual(self.one("WorkingDirectory"), "/opt/bota/current")
        self.assertEqual(
            self.one("ExecStart"),
            "/opt/bota/current/.venv/bin/python /opt/bota/current/tools/vps_orchestrator.py",
        )

    def test_roots_and_required_external_secret_environment(self) -> None:
        self.assertCountEqual(self.unit["Environment"], [
            "BOTA_CODE_ROOT=/opt/bota/current",
            "BOTA_ROOT=/opt/bota/current",
            "BOTA_MUTABLE_ROOT=/var/lib/bota",
        ])
        self.assertEqual(self.one("EnvironmentFile"), "/etc/bota/runtime.env")
        self.assertNotIn("Environment=HOME=", self.text)
        secret_markers = ("token=", "chat_id=", "service_key=", "api_key=", "password=")
        lowered = self.text.lower()
        self.assertFalse(any(marker in lowered for marker in secret_markers))

    def test_restart_cleanup_and_shutdown_budget(self) -> None:
        self.assertEqual(self.one("Restart"), "always")
        self.assertEqual(self.one("KillMode"), "control-group")
        self.assertEqual(self.one("SendSIGKILL"), "yes")
        match = re.fullmatch(r"(\d+)s", self.one("TimeoutStopSec"))
        self.assertIsNotNone(match)
        timeout = int(match.group(1))
        jobs = vps.production_jobs(ROOT)
        term_grace = vps.Orchestrator.__init__.__kwdefaults__["term_grace"]
        sequential_child_shutdown_bound = len(jobs) * term_grace
        self.assertEqual(sequential_child_shutdown_bound, 65)
        self.assertEqual(timeout, 120)
        self.assertGreater(timeout, sequential_child_shutdown_bound)

    def test_required_hardening(self) -> None:
        self.assertEqual(self.one("NoNewPrivileges"), "true")
        self.assertEqual(self.one("PrivateTmp"), "true")
        self.assertEqual(self.one("UMask"), "0077")

    def test_unit_has_no_competing_authority_or_direct_job(self) -> None:
        lowered = self.text.lower()
        forbidden = (
            "cron", "runsv", "runit", "native_watchdog", "supervisor", "watchdogsec",
            "systemctl", "bash -lc", "shell=true", ".timer", "watcher_gated_cycle",
            "indicators_updater", "shadow_manager", "signal_closer", "profitlab",
            "market_pulse", "heartbeat.sh", "runtime_health_push",
        )
        self.assertFalse({word for word in forbidden if word in lowered})
        self.assertEqual(lowered.count("vps_orchestrator.py"), 1)

    def test_orchestrator_remains_complete_sole_job_scheduler(self) -> None:
        self.assertEqual([job.name for job in vps.production_jobs(ROOT)], [
            "updater", "watcher", "shadow", "closer", "heartbeat",
            "profitlab_delivery", "runtime_health_push", "market_pulse",
            "alerts_to_trades", "pause_guard", "autostatus", "signal_accuracy",
            "daily_summary_server_gate",
        ])

    def test_android_legacy_authority_files_remain_for_non_vps_use(self) -> None:
        required = [
            ROOT / "ops/bota_crontab.canonical",
            ROOT / "ops/runit/bota-watcher.run",
            ROOT / "services/bota-shadow/run",
            ROOT / "services/bota-heartbeat/run",
            ROOT / "services/bota-supervisor/run",
        ]
        self.assertTrue(all(path.is_file() for path in required))


if __name__ == "__main__":
    unittest.main()
