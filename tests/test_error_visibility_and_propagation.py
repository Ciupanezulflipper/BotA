"""Errors must be visible on stderr and must propagate through exit codes.

These are regression tests for previously silent failure paths: corrupt state
files, provider exhaustion and unwritable history were all indistinguishable
from a normal quiet run.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import ModuleType
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lib_utils = load_module("lib_utils_error_test", TOOLS / "lib_utils.py")


class ReadJsonTests(unittest.TestCase):
    def test_missing_file_is_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = os.path.join(temporary, "absent.json")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                value = lib_utils.read_json(missing, default={"d": 1})
        self.assertEqual(value, {"d": 1})
        self.assertEqual(stderr.getvalue(), "")

    def test_corrupt_file_reports_before_falling_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            corrupt = os.path.join(temporary, "corrupt.json")
            Path(corrupt).write_text("{not json", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                value = lib_utils.read_json(corrupt, default={"d": 1})
        self.assertEqual(value, {"d": 1})
        self.assertIn("corrupt.json", stderr.getvalue())


class SltpMonitorStateTests(unittest.TestCase):
    def _monitor(self, root: Path) -> ModuleType:
        with mock.patch.dict(os.environ, {"BOTA_ROOT": str(root)}, clear=False):
            return load_module("sltp_monitor_error_test", TOOLS / "sltp_monitor.py")

    def test_corrupt_state_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            monitor = self._monitor(root)
            state_file = Path(monitor.STATE_FILE)
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text("}{", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                state = monitor.load_state()
        self.assertEqual(state, {"hit": {}, "daily_summary_sent": ""})
        self.assertIn("duplicate alerts possible", stderr.getvalue())

    def test_missing_state_is_quiet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            monitor = self._monitor(Path(temporary))
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                state = monitor.load_state()
        self.assertEqual(state, {"hit": {}, "daily_summary_sent": ""})
        self.assertEqual(stderr.getvalue(), "")


class ProvidersFailureAggregationTests(unittest.TestCase):
    def test_all_providers_failed_lists_every_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {"HOME": temporary, "PROVIDER_ORDER": "yahoo,alphavantage,twelvedata"},
                clear=False,
            ):
                providers = load_module("providers_error_test", TOOLS / "providers.py")
                with mock.patch.object(
                    providers, "_fetch_yahoo", side_effect=RuntimeError("yahoo down")
                ), mock.patch.object(
                    providers, "_fetch_av", side_effect=RuntimeError("av down")
                ), mock.patch.object(
                    providers, "_fetch_td", side_effect=RuntimeError("td down")
                ):
                    with redirect_stderr(io.StringIO()):
                        with self.assertRaises(RuntimeError) as caught:
                            providers.get_ohlc("EURUSD", "M15", 10)

        message = str(caught.exception)
        for expected in ("yahoo down", "av down", "td down"):
            self.assertIn(expected, message)
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)


class RunSignalOnceExitCodeTests(unittest.TestCase):
    def test_no_usable_provider_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": temporary,
                    "BOTA_ROOT": temporary,
                    "PROVIDER_ORDER": "nonexistent_provider",
                    "DRY_RUN_MODE": "true",
                    "TELEGRAM_ENABLED": "0",
                }
            )
            completed = subprocess.run(
                [sys.executable, str(TOOLS / "run_signal_once.py"), "EURUSD"],
                capture_output=True,
                text=True,
                env=environment,
                timeout=60,
            )

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("decision=WAIT", completed.stdout)
        self.assertIn("no provider returned a price", completed.stderr)


class SignalEngineExitCodeTests(unittest.TestCase):
    def test_no_usable_provider_exits_nonzero(self) -> None:
        environment = os.environ.copy()
        environment["PROVIDER_ORDER"] = "nonexistent_provider"
        completed = subprocess.run(
            [
                sys.executable,
                str(TOOLS / "signal_engine.py"),
                "--symbol",
                "EURUSD",
                "--tf",
                "15",
            ],
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
        )

        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertFalse(payload["ok"])
        self.assertIn("no provider usable", payload["error"])


if __name__ == "__main__":
    unittest.main()
