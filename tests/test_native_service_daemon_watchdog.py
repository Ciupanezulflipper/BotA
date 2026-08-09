from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import native_service_daemon_watchdog as watchdog

ROOT = Path("/data/data/com.termux/files/usr/var/service")
DAEMON = Path("/data/data/com.termux/files/usr/etc/init.d/service-daemon")
SV = Path("/data/data/com.termux/files/usr/bin/sv")
CROND_PID = 300
CROND_RUNSV_PID = 207


def row(exe: str, *argv: str, ppid: int) -> dict:
    return {"ppid": ppid, "argv": [exe, *argv]}


def healthy_table(manager: int = 100) -> dict[int, dict]:
    table = {
        manager: row("runsvdir", str(ROOT), ppid=1),
    }
    for index, service in enumerate(watchdog.SERVICES, start=1):
        table[200 + index] = row("runsv", service, ppid=manager)
    table[CROND_PID] = row("crond", "-n", "-s", ppid=CROND_RUNSV_PID)
    return table


class NativeManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.pidfile = Path(self.temp.name) / "service-daemon.pid"
        self.crond_pidfile = Path(self.temp.name) / "crond.pid"
        self.crond_pidfile.write_text(f"{CROND_PID}\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def immediate(predicate, _timeout):
        return predicate()

    @staticmethod
    def healthy_child(_root, service):
        return CROND_PID if service == "crond" else None

    def reconcile(self, **overrides):
        kwargs = {
            "table_fn": healthy_table,
            "service_running_fn": lambda *_args: True,
            "wait_fn": self.immediate,
            "crond_pidfile": self.crond_pidfile,
            "child_pid_fn": self.healthy_child,
        }
        kwargs.update(overrides)
        return watchdog.reconcile_once(
            ROOT,
            DAEMON,
            self.pidfile,
            SV,
            1,
            2,
            **kwargs,
        )

    def test_healthy_native_manager_is_noop(self) -> None:
        self.pidfile.write_text("100\n")
        command = mock.Mock()
        run_sv = mock.Mock()

        result = self.reconcile(command_fn=command, run_sv_fn=run_sv)

        self.assertEqual(result["manager_pid"], 100)
        self.assertEqual(result["owned"], 7)
        self.assertTrue(result["crond_ownership"]["healthy"])
        self.assertFalse(result["native_manager_started"])
        self.assertEqual(result["singleton_repairs"], {})
        command.assert_not_called()
        run_sv.assert_not_called()

    def test_multiple_managers_fail_closed(self) -> None:
        table = healthy_table()
        table[101] = row("runsvdir", "-P", str(ROOT), ppid=1)
        self.pidfile.write_text("100\n")

        with self.assertRaisesRegex(watchdog.WatchdogError, "multiple_managers:2"):
            self.reconcile(table_fn=lambda: table)

    def test_existing_manager_without_native_pidfile_fails_closed(self) -> None:
        with self.assertRaisesRegex(watchdog.WatchdogError, "native_pidfile_missing"):
            self.reconcile()

    def test_missing_manager_starts_native_daemon_and_removes_stale_pidfile(self) -> None:
        self.pidfile.write_text("999\n")
        state = {"started": False}

        def table_fn():
            return healthy_table() if state["started"] else {}

        def command_fn(argv, _timeout):
            self.assertEqual(argv, [str(DAEMON), "start"])
            state["started"] = True
            self.pidfile.write_text("100\n")
            return subprocess.CompletedProcess(argv, 0, "ok", "")

        result = self.reconcile(table_fn=table_fn, command_fn=command_fn)

        self.assertTrue(result["native_manager_started"])
        self.assertEqual(result["stale_pidfile_removed"], 999)
        self.assertEqual(result["manager_pid"], 100)
        self.assertEqual(self.pidfile.read_text().strip(), "100")

    def test_live_pidfile_process_blocks_native_start(self) -> None:
        self.pidfile.write_text("555\n")
        table = {555: row("python3", "worker.py", ppid=1)}
        command = mock.Mock()

        with self.assertRaisesRegex(
            watchdog.WatchdogError, "native_pidfile_points_live_process:555"
        ):
            self.reconcile(table_fn=lambda: table, command_fn=command)
        command.assert_not_called()

    def test_manager_owned_down_service_is_brought_up(self) -> None:
        self.pidfile.write_text("100\n")
        state = {"shadow_up": False}

        def running(_sv, _root, service):
            return state["shadow_up"] if service == "bota-shadow" else True

        def run_sv(_sv, _root, service, command, _timeout):
            self.assertEqual((service, command), ("bota-shadow", "up"))
            state["shadow_up"] = True
            return subprocess.CompletedProcess([], 0, "ok", "")

        result = self.reconcile(run_sv_fn=run_sv, service_running_fn=running)

        self.assertEqual(result["restarted_services"], ["bota-shadow"])
        self.assertEqual(result["running"], 7)

    def test_pid1_orphan_is_handed_to_native_manager(self) -> None:
        self.pidfile.write_text("100\n")
        state = {"handed": False}

        def table_fn():
            table = healthy_table()
            if not state["handed"]:
                table[202] = row("runsv", "bota-watcher", ppid=1)
            return table

        calls = []

        def run_sv(_sv, _root, service, command, _timeout):
            calls.append((service, command))
            if service == "bota-watcher" and command == "exit":
                state["handed"] = True
            return subprocess.CompletedProcess([], 0, "ok", "")

        result = self.reconcile(table_fn=table_fn, run_sv_fn=run_sv)

        self.assertEqual(
            calls,
            [("bota-watcher", "down"), ("bota-watcher", "exit")],
        )
        self.assertEqual(result["handed_off_services"], ["bota-watcher"])
        self.assertEqual(result["owned"], 7)

    def test_delayed_runsv_rows_are_bounded_before_failure(self) -> None:
        self.pidfile.write_text("100\n")
        calls = {"count": 0}

        def table_fn():
            calls["count"] += 1
            if calls["count"] < 4:
                return {100: row("runsvdir", str(ROOT), ppid=1)}
            return healthy_table()

        result = self.reconcile(table_fn=table_fn)

        self.assertEqual(result["owned"], 7)
        self.assertGreaterEqual(calls["count"], 4)

    def test_manager_pidfile_mismatch_fails_closed(self) -> None:
        self.pidfile.write_text("101\n")
        with self.assertRaisesRegex(
            watchdog.WatchdogError,
            "native_pidfile_manager_mismatch:pidfile=101:manager=100",
        ):
            self.reconcile()

    def test_exact_stale_pid1_crond_is_reconciled_without_blind_pidfile_delete(self) -> None:
        self.pidfile.write_text("100\n")
        state = {"table": healthy_table(), "child": None, "crond_up": False}
        state["table"].pop(CROND_PID)
        state["table"][555] = row("crond", "-n", "-s", ppid=1)
        self.crond_pidfile.write_text("555\n")
        calls = []
        terminated = []

        def table_fn():
            return state["table"]

        def child_pid(_root, service):
            return state["child"] if service == "crond" else None

        def running(_sv, _root, service):
            return state["crond_up"] if service == "crond" else True

        def run_sv(_sv, _root, service, command, _timeout):
            calls.append((service, command))
            if (service, command) == ("crond", "up"):
                state["table"][777] = row(
                    "crond", "-n", "-s", ppid=CROND_RUNSV_PID
                )
                state["child"] = 777
                state["crond_up"] = True
                self.crond_pidfile.write_text("777\n")
            return subprocess.CompletedProcess([], 0, "ok", "")

        def terminate(pid):
            terminated.append(pid)
            state["table"].pop(pid)
            self.crond_pidfile.unlink()

        result = self.reconcile(
            table_fn=table_fn,
            run_sv_fn=run_sv,
            service_running_fn=running,
            child_pid_fn=child_pid,
            terminate_fn=terminate,
        )

        self.assertEqual(calls, [("crond", "down"), ("crond", "up")])
        self.assertEqual(terminated, [555])
        self.assertEqual(result["restarted_services"], ["crond"])
        repair = result["singleton_repairs"]["crond"]
        self.assertEqual(repair["stale_pid"], 555)
        self.assertEqual(repair["replacement_pid"], 777)
        self.assertEqual(repair["replacement_parent"], CROND_RUNSV_PID)
        self.assertTrue(result["crond_ownership"]["healthy"])

    def test_stale_crond_wrong_pidfile_fails_closed_before_signal_or_sv_down(self) -> None:
        self.pidfile.write_text("100\n")
        table = healthy_table()
        table.pop(CROND_PID)
        table[555] = row("crond", "-n", "-s", ppid=1)
        self.crond_pidfile.write_text("999\n")
        run_sv = mock.Mock()
        terminate = mock.Mock()

        with self.assertRaisesRegex(
            watchdog.WatchdogError, "crond_pidfile_not_stale_candidate"
        ):
            self.reconcile(
                table_fn=lambda: table,
                run_sv_fn=run_sv,
                service_running_fn=lambda _sv, _root, service: service != "crond",
                child_pid_fn=lambda *_args: None,
                terminate_fn=terminate,
            )
        run_sv.assert_not_called()
        terminate.assert_not_called()

    def test_stale_crond_non_pid1_parent_fails_closed(self) -> None:
        self.pidfile.write_text("100\n")
        table = healthy_table()
        table.pop(CROND_PID)
        table[555] = row("crond", "-n", "-s", ppid=444)
        self.crond_pidfile.write_text("555\n")
        terminate = mock.Mock()

        with self.assertRaisesRegex(
            watchdog.WatchdogError, "crond_live_process_ambiguous"
        ):
            self.reconcile(
                table_fn=lambda: table,
                service_running_fn=lambda _sv, _root, service: service != "crond",
                child_pid_fn=lambda *_args: None,
                terminate_fn=terminate,
            )
        terminate.assert_not_called()

    def test_multiple_crond_processes_fail_closed(self) -> None:
        self.pidfile.write_text("100\n")
        table = healthy_table()
        table.pop(CROND_PID)
        table[555] = row("crond", "-n", "-s", ppid=1)
        table[556] = row("crond", "-n", "-s", ppid=1)
        self.crond_pidfile.write_text("555\n")
        terminate = mock.Mock()

        with self.assertRaisesRegex(
            watchdog.WatchdogError, "crond_live_process_ambiguous:count=2"
        ):
            self.reconcile(
                table_fn=lambda: table,
                service_running_fn=lambda _sv, _root, service: service != "crond",
                child_pid_fn=lambda *_args: None,
                terminate_fn=terminate,
            )
        terminate.assert_not_called()

    def test_running_crond_with_wrong_parent_fails_closed_without_signal(self) -> None:
        self.pidfile.write_text("100\n")
        table = healthy_table()
        table[CROND_PID]["ppid"] = 1
        terminate = mock.Mock()

        with self.assertRaisesRegex(watchdog.WatchdogError, "crond_ownership_invalid"):
            self.reconcile(table_fn=lambda: table, terminate_fn=terminate)
        terminate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
