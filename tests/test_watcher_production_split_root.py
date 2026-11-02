from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def tree_digest(root: Path) -> dict[str, tuple[int, str]]:
    result = {}
    for path in root.rglob("*"):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = (
                stat.S_IMODE(path.stat().st_mode), hashlib.sha256(path.read_bytes()).hexdigest()
            )
    return result


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class WatcherProductionSplitRootTests(unittest.TestCase):
    def test_gated_cycle_writes_only_mutable_root_with_read_only_code(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); code = base / "code"; mutable = base / "mutable"
            shutil.copytree(TOOLS, code / "tools")
            mutable.mkdir()
            for path in code.rglob("*"):
                path.chmod(0o555 if path.is_dir() else 0o444)
            code.chmod(0o555)
            before = tree_digest(code)
            env = os.environ.copy()
            env.update({
                "BOTA_CODE_ROOT": str(code), "BOTA_ROOT": str(code),
                "BOTA_MUTABLE_ROOT": str(mutable), "WATCHER_GATED_MARKET_HINT": "MARKET_OPEN",
                "WATCHER_GATED_DRY_RUN": "1", "BOTA_CYCLE_ID": "split-root-test",
            })
            completed = subprocess.run(
                ["bash", str(code / "tools/watcher_gated_cycle.sh")], env=env,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(tree_digest(code), before)
            self.assertTrue((mutable / "state/pipeline_progress.json").is_file())
            self.assertTrue((mutable / "logs").is_dir())

    def test_recovery_and_ledger_resolve_split_roots(self):
        recovery = load("split_recovery", TOOLS / "watcher_pending_delivery_recovery.py")
        ledger = load("split_ledger", TOOLS / "watcher_cycle_ledger.py")
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); code=base/"code"; mutable=base/"mutable"
            env={"BOTA_CODE_ROOT":str(code), "BOTA_ROOT":str(code), "BOTA_MUTABLE_ROOT":str(mutable)}
            with mock.patch.dict(os.environ,env,clear=True):
                self.assertEqual(recovery.mutable_root(),mutable.resolve())
                self.assertEqual(ledger.code_root(),code)
                self.assertEqual(ledger.mutable_root(),mutable)

    def test_sender_0644_runs_via_bash_without_metadata_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); code=base/"code"; tools=code/"tools"; mutable=base/"mutable"
            tools.mkdir(parents=True); (mutable/"logs/state").mkdir(parents=True)
            shutil.copy2(TOOLS/"signal_watcher_pro.sh",tools/"signal_watcher_pro.sh")
            (tools/"telegram_send.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
            (tools/"watcher_pending_delivery_recovery.py").write_text("raise SystemExit(0)\n")
            (tools/"signal_watcher_core.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
            for path in tools.iterdir(): path.chmod(0o444)
            before=tree_digest(code)
            env=os.environ.copy(); env.update({
                "BOTA_CODE_ROOT":str(code), "BOTA_ROOT":str(code), "BOTA_MUTABLE_ROOT":str(mutable),
                "BOTA_CYCLE_ID":"x", "BOTA_ALERTS_OFFSET":"0",
                "BOTA_TELEGRAM_RESULT_LOG":str(mutable/"tg"),
                "BOTA_SUPABASE_RESULT_LOG":str(mutable/"sb"),
                "BOTA_DELIVERY_STATE_DIR":str(mutable/"logs/state"),
            })
            completed=subprocess.run(["bash",str(tools/"signal_watcher_pro.sh")],env=env,capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertEqual(tree_digest(code),before)

    def test_canonical_core_has_no_second_telegram_transport(self):
        core=(TOOLS/"signal_watcher_core.sh").read_text()
        sender=(TOOLS/"telegram_send.sh").read_text()
        delivery=(TOOLS/"telegram_delivery.py").read_text()
        self.assertNotIn("sendPhoto",core)
        self.assertNotIn("api.telegram.org",core)
        self.assertIn('bash "${TOOLS}/telegram_send.sh"',core)
        self.assertIn("telegram_delivery_boundary.py",sender)
        self.assertEqual(delivery.count("urllib.request.urlopen"),1)

    def test_standalone_strict_contract_failure_has_no_unbound_variable(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); code=base/"code"; tools=code/"tools"; mutable=base/"mutable"
            tools.mkdir(parents=True); mutable.mkdir()
            for name in ("run_signal_watcher_with_ledger.sh", "watcher_cycle_contract.py"):
                shutil.copy2(TOOLS/name,tools/name)
            (tools/"telegram_send.sh").write_text("exit 0\n")
            (tools/"watcher_evidence_retention.py").write_text("raise SystemExit(0)\n")
            (tools/"signal_watcher_pro.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
            (tools/"watcher_cycle_ledger.py").write_text("raise SystemExit(0)\n")
            (tools/"pipeline_ledger.py").write_text("raise SystemExit(0)\n")
            env=os.environ.copy(); env.pop("BOTA_CYCLE_ID",None); env.update({
                "BOTA_CODE_ROOT":str(code), "BOTA_ROOT":str(code), "BOTA_MUTABLE_ROOT":str(mutable),
                "PAIRS":"EURUSD GBPUSD USDJPY", "TIMEFRAMES":"M15",
            })
            completed=subprocess.run(["bash",str(tools/"run_signal_watcher_with_ledger.sh")],
                                     env=env,text=True,capture_output=True,check=False)
            self.assertNotEqual(completed.returncode,0)
            self.assertNotIn("unbound variable",completed.stderr)
            self.assertIn("retained cycle_log=",completed.stderr)
            self.assertNotIn("persistence_exit_code",completed.stderr)


if __name__ == "__main__":
    unittest.main()
