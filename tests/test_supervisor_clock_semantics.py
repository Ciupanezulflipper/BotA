#!/usr/bin/env python3
"""Regression tests for BotA supervisor clock-health semantics."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import supervisor_clock_status


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = REPOSITORY_ROOT / "tools" / "bota_supervisor.sh"
MARKET_GATE = REPOSITORY_ROOT / "tools" / "market_open.sh"


def write_executable(path: Path, content: str) -> None:
    """Write an executable test helper."""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def prepare_runtime(base: Path) -> Path:
    """Create an isolated BotA tree containing the production supervisor."""
    root = base / "BotA"
    tools = root / "tools"
    for directory in (
        tools,
        root / "logs" / "state",
        root / "state",
        root / "config",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    (tools / "bota_supervisor.sh").write_text(
        SUPERVISOR.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tools / "bota_supervisor.sh").chmod(0o755)
    (tools / "supervisor_clock_status.py").write_text(
        (REPOSITORY_ROOT / "tools" / "supervisor_clock_status.py").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    return root


def write_control_plane(root: Path, *, healthy: bool) -> None:
    """Write a deterministic control-plane reporter."""
    failures = [] if healthy else ["owned_mismatch"]
    code = 0 if healthy else 1
    payload = {
        "owned": 7 if healthy else 0,
        "required": 7,
        "running": 7,
        "orphaned": 0 if healthy else 7,
        "failure_reasons": failures,
    }
    write_executable(
        root / "tools" / "control_plane_status.py",
        "#!/usr/bin/env python3\n"
        "import json\n"
        f"print(json.dumps({payload!r}))\n"
        f"raise SystemExit({code})\n",
    )


def write_pipeline(root: Path, *, healthy: bool) -> None:
    """Write a pipeline reporter that records the selected market mode."""
    failures = [] if healthy else ["watcher_progress_stale"]
    code = 0 if healthy else 1
    payload = {"healthy": healthy, "failure_reasons": failures}
    write_executable(
        root / "tools" / "pipeline_health.py",
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"root = Path({str(root)!r})\n"
        "(root / 'state' / 'pipeline_args.txt').write_text("
        "' '.join(sys.argv[1:]), encoding='utf-8')\n"
        f"print(json.dumps({payload!r}))\n"
        f"raise SystemExit({code})\n",
    )


def write_market_gate(root: Path, *, state: str) -> None:
    """Write a market gate with the production stdout/exit/debug contract."""
    if state == "open":
        output, code, detail = "Open", 0, "within session -> Open"
    elif state == "clock_unavailable":
        output, code, detail = (
            "Closed",
            1,
            "server_clock_unavailable count=0 spread=NA -> Closed fail_closed",
        )
    else:
        output, code, detail = "Closed", 1, "Saturday UTC -> Closed"
    write_executable(
        root / "tools" / "market_open.sh",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' {output!r}\n"
        f"printf '%s\\n' {detail!r} >&2\n"
        f"exit {code}\n",
    )


def write_clock_status(
    root: Path,
    *,
    status: str,
    server_clock_ok: bool | None,
    local_clock_unsafe: bool | None,
) -> None:
    """Write a deterministic clock-observability document."""
    payload = {
        "status": status,
        "server_clock_ok": server_clock_ok,
        "local_clock_unsafe": local_clock_unsafe,
        "drift_seconds": 3600 if local_clock_unsafe else 0,
        "server_reason": (
            "server_clock_ok" if server_clock_ok else "server_clock_unavailable"
        ),
        "generated_utc": "2026-08-02T21:00:00Z",
    }
    (root / "logs" / "clock_drift_status.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def run_supervisor(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the production supervisor against the isolated BotA tree."""
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(root.parent),
            "BOTA_ROOT": str(root),
            "PATH": os.environ["PATH"],
        }
    )
    return subprocess.run(
        ["bash", str(root / "tools" / "bota_supervisor.sh")],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def load_health(root: Path) -> dict:
    """Load the generated runtime-health object."""
    return json.loads(
        (root / "state" / "runtime_health.json").read_text(encoding="utf-8")
    )


class TradingClockSafetyTests(unittest.TestCase):
    """Protect the unchanged fail-closed trading gate."""

    def test_market_gate_remains_fail_closed_without_server_clock(self) -> None:
        source = MARKET_GATE.read_text(encoding="utf-8")
        self.assertIn("server_clock_unavailable", source)
        self.assertIn('echo "Closed"', source)
        self.assertRegex(
            source,
            r"server_clock_unavailable.*Closed fail_closed",
        )


class ClockNormalizerTests(unittest.TestCase):
    """Exercise market-gate classification and non-fatal clock reporting."""

    def test_clock_unavailable_is_separate_from_runtime_failure(self) -> None:
        gate = supervisor_clock_status.classify_market_gate(
            1,
            "Closed\n",
            "server_clock_unavailable -> Closed fail_closed\n",
        )
        with tempfile.TemporaryDirectory() as temporary:
            clock_file = Path(temporary) / "clock.json"
            clock_file.write_text(
                json.dumps(
                    {
                        "status": "SERVER_CLOCK_UNAVAILABLE",
                        "server_clock_ok": False,
                        "local_clock_unsafe": None,
                    }
                ),
                encoding="utf-8",
            )
            clock = supervisor_clock_status.normalize_clock_observability(
                clock_file,
                gate,
            )

        self.assertEqual(gate["state"], "clock_unavailable")
        self.assertFalse(gate["trusted_server_clock_available"])
        self.assertEqual(clock["status"], "UNAVAILABLE")
        self.assertEqual(clock["snapshot_status"], "SERVER_CLOCK_UNAVAILABLE")
        self.assertFalse(clock["trading_clock_available"])
        self.assertFalse(clock["runtime_failure"])

    def test_drift_warning_is_informational_when_server_clock_works(self) -> None:
        gate = supervisor_clock_status.classify_market_gate(
            1,
            "Closed\n",
            "Saturday UTC -> Closed\n",
        )
        with tempfile.TemporaryDirectory() as temporary:
            clock_file = Path(temporary) / "clock.json"
            clock_file.write_text(
                json.dumps(
                    {
                        "status": "DRIFT_WARN",
                        "server_clock_ok": True,
                        "local_clock_unsafe": True,
                        "drift_seconds": 3600,
                    }
                ),
                encoding="utf-8",
            )
            clock = supervisor_clock_status.normalize_clock_observability(
                clock_file,
                gate,
            )

        self.assertEqual(gate["state"], "closed")
        self.assertTrue(gate["trusted_server_clock_available"])
        self.assertEqual(clock["status"], "AVAILABLE")
        self.assertEqual(clock["snapshot_status"], "DRIFT_WARN")
        self.assertTrue(clock["trading_clock_available"])
        self.assertTrue(clock["local_clock_warning"])
        self.assertFalse(clock["runtime_failure"])

    def test_live_gate_overrides_stale_unavailable_snapshot(self) -> None:
        gate = supervisor_clock_status.classify_market_gate(
            1,
            "Closed\n",
            "Friday after 20:00 UTC -> Closed\n",
        )
        with tempfile.TemporaryDirectory() as temporary:
            clock_file = Path(temporary) / "clock.json"
            clock_file.write_text(
                json.dumps(
                    {
                        "status": "SERVER_CLOCK_UNAVAILABLE",
                        "server_clock_ok": False,
                        "local_clock_unsafe": None,
                    }
                ),
                encoding="utf-8",
            )
            clock = supervisor_clock_status.normalize_clock_observability(
                clock_file,
                gate,
            )

        self.assertTrue(gate["trusted_server_clock_available"])
        self.assertEqual(clock["status"], "AVAILABLE")
        self.assertEqual(clock["snapshot_status"], "SERVER_CLOCK_UNAVAILABLE")
        self.assertTrue(clock["live_gate_overrode_snapshot"])


class SupervisorBehaviorTests(unittest.TestCase):
    """Verify bot mode is driven only by process and pipeline evidence."""

    @staticmethod
    def configure(
        root: Path,
        *,
        control_healthy: bool = True,
        pipeline_healthy: bool = True,
        market_state: str = "closed",
        clock_status: str = "OK",
        server_clock_ok: bool | None = True,
        local_clock_unsafe: bool | None = False,
    ) -> None:
        """Write all deterministic supervisor dependencies."""
        write_control_plane(root, healthy=control_healthy)
        write_pipeline(root, healthy=pipeline_healthy)
        write_market_gate(root, state=market_state)
        write_clock_status(
            root,
            status=clock_status,
            server_clock_ok=server_clock_ok,
            local_clock_unsafe=local_clock_unsafe,
        )

    def test_clock_outage_does_not_degrade_healthy_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            self.configure(
                root,
                market_state="clock_unavailable",
                clock_status="SERVER_CLOCK_UNAVAILABLE",
                server_clock_ok=False,
                local_clock_unsafe=None,
            )
            result = run_supervisor(root)
            health = load_health(root)
            pipeline_args = (
                root / "state" / "pipeline_args.txt"
            ).read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(health["bot_mode"], "HEALTHY")
        self.assertEqual(health["failure_reasons"], [])
        self.assertEqual(health["market_state"], "clock_unavailable")
        self.assertFalse(
            health["market_gate"]["trusted_server_clock_available"]
        )
        self.assertEqual(health["clock_observability"]["status"], "UNAVAILABLE")
        self.assertFalse(health["clock_observability"]["runtime_failure"])
        self.assertEqual(pipeline_args, "--market-closed")
        self.assertNotIn("server_clock_unavailable", health["failure_reasons"])

    def test_real_control_failure_remains_degraded_without_clock_pollution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            self.configure(
                root,
                control_healthy=False,
                market_state="clock_unavailable",
                clock_status="SERVER_CLOCK_UNAVAILABLE",
                server_clock_ok=False,
                local_clock_unsafe=None,
            )
            result = run_supervisor(root)
            health = load_health(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(health["bot_mode"], "DEGRADED")
        self.assertEqual(
            health["failure_reasons"],
            ["control_plane:owned_mismatch"],
        )
        self.assertNotIn(
            "server_clock_unavailable",
            "|".join(health["failure_reasons"]),
        )
        self.assertEqual(health["market_state"], "clock_unavailable")

    def test_open_market_selects_open_pipeline_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            self.configure(root, market_state="open")
            result = run_supervisor(root)
            health = load_health(root)
            pipeline_args = (
                root / "state" / "pipeline_args.txt"
            ).read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(health["market_state"], "open")
        self.assertEqual(health["clock_observability"]["status"], "AVAILABLE")
        self.assertEqual(pipeline_args, "--market-open")

    def test_closed_market_with_drift_warning_remains_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            self.configure(
                root,
                market_state="closed",
                clock_status="DRIFT_WARN",
                server_clock_ok=True,
                local_clock_unsafe=True,
            )
            result = run_supervisor(root)
            health = load_health(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(health["bot_mode"], "HEALTHY")
        self.assertEqual(health["market_state"], "closed")
        self.assertEqual(health["clock_observability"]["status"], "AVAILABLE")
        self.assertEqual(
            health["clock_observability"]["snapshot_status"],
            "DRIFT_WARN",
        )
        self.assertTrue(
            health["clock_observability"]["local_clock_warning"]
        )
        self.assertTrue(
            health["clock_observability"]["trading_clock_available"]
        )

    def test_missing_clock_file_is_explicit_but_live_gate_stays_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = prepare_runtime(Path(temporary))
            write_control_plane(root, healthy=True)
            write_pipeline(root, healthy=True)
            write_market_gate(root, state="closed")
            result = run_supervisor(root)
            health = load_health(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(health["bot_mode"], "HEALTHY")
        self.assertEqual(health["clock_observability"]["status"], "AVAILABLE")
        self.assertEqual(
            health["clock_observability"]["snapshot_status"],
            "MISSING",
        )
        self.assertFalse(
            health["clock_observability"]["source_file_present"]
        )
        self.assertFalse(health["clock_observability"]["runtime_failure"])


if __name__ == "__main__":
    unittest.main()
