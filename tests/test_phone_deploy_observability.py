from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    path = HERE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"missing loader for {relative}")
    spec.loader.exec_module(module)
    return module


deploy = load_module("phone_deploy_observability", "ops/phone_deploy_observability.py")


class TransactionTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.base = Path(td.name)
        self.root = self.base / "BotA"
        self.stage = self.base / "stage"
        self.backup = self.root / "state" / "deployments" / "test"
        self.root.mkdir(parents=True)
        self.stage.mkdir(parents=True)
        (self.root / "unrelated.txt").write_text("leave-me-alone", encoding="utf-8")
        self.original: dict[str, tuple[bool, bytes | None, int | None]] = {}
        self.expected: dict[str, str] = {}

        for index, relpath in enumerate(deploy.RUNTIME_FILES):
            stage_path = self.stage / relpath
            stage_path.parent.mkdir(parents=True, exist_ok=True)
            new_data = f"new-{index}-{relpath}\n".encode()
            stage_path.write_bytes(new_data)
            self.expected[relpath] = deploy.git_blob_sha(new_data)

            target = self.root / relpath
            if index % 2 == 0:
                target.parent.mkdir(parents=True, exist_ok=True)
                old_data = f"old-{index}-{relpath}\n".encode()
                target.write_bytes(old_data)
                mode = 0o755 if relpath.endswith(".sh") else 0o640
                os.chmod(target, mode)
                self.original[relpath] = (True, old_data, mode)
            else:
                self.original[relpath] = (False, None, None)

        self.entries = deploy.backup_current(self.root, self.backup)

    def assert_original_restored(self):
        for relpath, (existed, data, mode) in self.original.items():
            target = self.root / relpath
            if existed:
                self.assertTrue(target.is_file(), relpath)
                self.assertEqual(target.read_bytes(), data, relpath)
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), mode, relpath)
            else:
                self.assertFalse(target.exists(), relpath)
        self.assertEqual((self.root / "unrelated.txt").read_text(encoding="utf-8"), "leave-me-alone")

    def test_fault_after_every_file_rolls_back_exact_bytes_and_modes(self):
        for fail_after in range(1, len(deploy.RUNTIME_FILES) + 1):
            with self.subTest(fail_after=fail_after):
                with self.assertRaises(deploy.DeployError):
                    deploy.install_files(
                        self.root,
                        self.stage,
                        self.expected,
                        fail_after=fail_after,
                    )
                deploy.rollback_files(self.root, self.backup, self.entries)
                self.assert_original_restored()

    def test_success_installs_exact_git_blob_bytes(self):
        deploy.install_files(self.root, self.stage, self.expected)
        for relpath, blob in self.expected.items():
            self.assertEqual(deploy.git_blob_sha((self.root / relpath).read_bytes()), blob)
        self.assertEqual((self.root / "unrelated.txt").read_text(encoding="utf-8"), "leave-me-alone")

    def test_corrupt_backup_fails_before_changing_any_target(self):
        deploy.install_files(self.root, self.stage, self.expected)
        before = {
            relpath: (self.root / relpath).read_bytes()
            for relpath in deploy.RUNTIME_FILES
        }
        existing = next(entry for entry in self.entries if entry.existed)
        backup_path = self.backup / "files" / existing.path
        backup_path.write_bytes(b"corrupt")
        with self.assertRaises(deploy.DeployError):
            deploy.rollback_files(self.root, self.backup, self.entries)
        after = {
            relpath: (self.root / relpath).read_bytes()
            for relpath in deploy.RUNTIME_FILES
        }
        self.assertEqual(before, after)

    def test_new_file_is_removed_on_rollback(self):
        new_entry = next(entry for entry in self.entries if not entry.existed)
        deploy.install_files(self.root, self.stage, self.expected)
        self.assertTrue((self.root / new_entry.path).exists())
        deploy.rollback_files(self.root, self.backup, self.entries)
        self.assertFalse((self.root / new_entry.path).exists())


class ProcessIdentityTests(unittest.TestCase):
    def proc(self, pid, ppid, start, state, comm, argv=()):
        return deploy.ProcIdentity(pid, ppid, start, state, comm, tuple(argv))

    def test_safe_idle_requires_exactly_one_live_sleep_child(self):
        wrapper = self.proc(100, 50, 1000, "S", "bash", ("bash", "bota-watcher.run"))
        sleep = self.proc(101, 100, 1001, "S", "sleep", ("sleep", "300"))
        table = {100: wrapper, 101: sleep}
        self.assertEqual(deploy.safe_idle_sleep(wrapper, table), sleep)

        python = self.proc(102, 100, 1002, "S", "python3", ("python3", "worker.py"))
        self.assertIsNone(deploy.safe_idle_sleep(wrapper, {**table, 102: python}))

    def test_zombie_sleep_is_inert_not_live_work(self):
        wrapper = self.proc(100, 50, 1000, "T", "bash", ("bash", "bota-watcher.run"))
        sleep = self.proc(101, 100, 1001, "Z", "sleep", ())
        self.assertEqual(deploy.live_descendants({100: wrapper, 101: sleep}, 100), [])

    def test_pid_reuse_or_parent_change_breaks_identity(self):
        expected = self.proc(100, 50, 1000, "S", "bash")
        reused = self.proc(100, 50, 2000, "S", "bash")
        reparented = self.proc(100, 1, 1000, "S", "bash")
        self.assertFalse(deploy.same_process(expected, reused))
        self.assertFalse(deploy.same_process(expected, reparented))
        self.assertTrue(deploy.same_process(expected, expected))


class LiveAcceptanceTests(unittest.TestCase):
    def state(self, terminal="EVALUATED_REJECTED", cycle="cycle-new"):
        decisions = {}
        for key in deploy.REQUIRED_DECISIONS:
            decisions[key] = {
                "cycle_id": cycle,
                "status": "completed",
                "outcome": "filter_rejected",
                "alerts_csv_persisted": True,
                "telegram_result": "not_attempted",
            }
        return {
            "last_terminal_outcome": {
                "cycle_id": cycle,
                "terminal_outcome": terminal,
            },
            "decisions": decisions,
        }

    def test_same_cycle_three_pair_decisions_pass(self):
        status, reasons = deploy.evaluate_live_cycle(self.state(), "cycle-old")
        self.assertEqual(status, "PASS")
        self.assertEqual(reasons, [])

    def test_old_cycle_waits(self):
        status, reasons = deploy.evaluate_live_cycle(self.state(cycle="cycle-old"), "cycle-old")
        self.assertEqual(status, "WAIT")
        self.assertIn("no_new_cycle", reasons)

    def test_cycle_mismatch_fails(self):
        state = self.state()
        state["decisions"]["GBPUSD:M15"]["cycle_id"] = "other"
        status, reasons = deploy.evaluate_live_cycle(state, "cycle-old")
        self.assertEqual(status, "FAILED")
        self.assertIn("decision_cycle_mismatch:GBPUSD:M15", reasons)

    def test_unknown_telegram_fails(self):
        state = self.state(terminal="EVALUATED_ACCEPTED")
        state["decisions"]["GBPUSD:M15"]["outcome"] = "telegram_unknown_outcome"
        state["decisions"]["GBPUSD:M15"]["telegram_result"] = "unknown_outcome"
        status, reasons = deploy.evaluate_live_cycle(state, "cycle-old")
        self.assertEqual(status, "FAILED")
        self.assertTrue(any(reason.startswith("decision_unhealthy:GBPUSD:M15") for reason in reasons))
        self.assertIn("telegram_unknown:GBPUSD:M15", reasons)

    def test_market_closed_is_pending_not_false_pass(self):
        status, reasons = deploy.evaluate_live_cycle(
            self.state(terminal="MARKET_CLOSED"),
            "cycle-old",
        )
        self.assertEqual(status, "PENDING_MARKET_CLOSED")
        self.assertEqual(reasons, [])

    def test_clock_or_data_failure_is_not_strategy_failure(self):
        status, reasons = deploy.evaluate_live_cycle(
            self.state(terminal="CLOCK_GATE_FAILED"),
            "cycle-old",
        )
        self.assertEqual(status, "EXTERNAL_OR_ENV_FAILURE")
        self.assertEqual(reasons, ["CLOCK_GATE_FAILED"])


class SourceSafetyTests(unittest.TestCase):
    def test_no_destructive_git_or_broad_kill_commands(self):
        source = (HERE / "ops" / "phone_deploy_observability.py").read_text(encoding="utf-8")
        forbidden = (
            "git reset",
            "git checkout",
            "git clean",
            "git pull",
            "pkill",
            "killall",
            "os.killpg",
        )
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_manifest_is_observability_only(self):
        self.assertNotIn("tools/scoring_engine.sh", deploy.RUNTIME_FILES)
        self.assertNotIn("tools/m15_h1_fusion.sh", deploy.RUNTIME_FILES)
        self.assertNotIn("tools/signal_watcher_pro.sh", deploy.RUNTIME_FILES)
        self.assertNotIn("config/strategy.env", deploy.RUNTIME_FILES)
        self.assertEqual(deploy.RUNTIME_COMMIT, "73415776bb1acf6c835236fd23e559d07f274e12")

    def test_pinned_runtime_files_exist_and_match_git_blobs(self):
        self.assertTrue(deploy.git_has_commit(HERE, deploy.RUNTIME_COMMIT))
        for relpath in deploy.RUNTIME_FILES:
            with self.subTest(relpath=relpath):
                data = deploy.source_bytes(HERE, deploy.RUNTIME_COMMIT, relpath)
                self.assertEqual(
                    deploy.git_blob_sha(data),
                    deploy.source_blob_sha(HERE, deploy.RUNTIME_COMMIT, relpath),
                )


if __name__ == "__main__":
    unittest.main()
