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


def row(exe: str, *argv: str, ppid: int) -> dict:
    return {"ppid": ppid, "argv": [exe, *argv]}


def healthy_table(manager: int = 100) -> dict[int, dict]:
    table = {
        manager: row("runsvdir", str(ROOT), ppid=1),
    }
    for index, service in enumerate(watchdog.SERVICES, start=1):
        table[200 + index] = row("runsv", service, ppid=manager)
    return table


class NativeManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.pidfile = Path(self.temp.name) / "service-daemon.pid"

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def immediate(predicate, _timeout):
        return predicate()

    def test_healthy_native_manager_is_noop(self) -> None:
        self.pidfile.write_text("100\n")
        command = mock.Mock()
        run_sv = mock.Mock()

        result = watchdog.reconcile_once(
            ROOT,
            DAEMON,
            self.pidfile,
            SV,
            1,
            2,
            table_fn=lambda: healthy_table(),
            command_fn=command,
            run_sv_fn=run_sv,
            service_running_fn=lambda *_args: True,
            wait_fn=self.immediate,
        )

        self.assertEqual(result["manager_pid"], 100)
        self.assertEqual(result["owned"], 7)
        self.assertFalse(result["native_manager_started"])
        command.assert_not_called()
        run_sv.assert_not_called()

    def test_multiple_managers_fail_closed(self) -> None:
        table = healthy_table()
        table[101] = row("runsvdir", "-P", str(ROOT), ppid=1)
        self.pidfile.write_text("100\n")

        with self.assertRaisesRegex(watchdog.WatchdogError, "multiple_managers:2"):
            watchdog.reconcile_once(
                ROOT,
                DAEMON,
                self.pidfile,
                SV,
                1,
                2,
                table_fn=lambda: table,
                service_running_fn=lambda *_args: True,
                wait_fn=self.immediate,
            )

    def test_existing_manager_without_native_pidfile_fails_closed(self) -> None:
        with self.assertRaisesRegex(watchdog.WatchdogError, "native_pidfile_missing"):
            watchdog.reconcile_once(
                ROOT,
                DAEMON,
                self.pidfile,
                SV,
                1,
                2,
                table_fn=lambda: healthy_table(),
                service_running_fn=lambda *_args: True,
                wait_fn=self.immediate,
            )

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

        result = watchdog.reconcile_once(
            ROOT,
            DAEMON,
            self.pidfile,
            SV,
            1,
            2,
            table_fn=table_fn,
            command_fn=command_fn,
            service_running_fn=lambda *_args: True,
            wait_fn=self.immediate,
        )

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
            watchdog.reconcile_once(
                ROOT,
                DAEMON,
                self.pidfile,
                SV,
                1,
                2,
                table_fn=lambda: table,
                command_fn=command,
                service_running_fn=lambda *_args: True,
                wait_fn=self.immediate,
            )
        command.assert_not_called()

    def test_manager_owned_down_service_is_brought_up(self) -> None:
        self.pidfile.write_text("100\n")
        crond_checks = {"count": 0}

        def running(_sv, _root, service):
            if service != "crond":
                return True
            crond_checks["count"] += 1
            return crond_checks["count"] > 1

        run_sv = mock.Mock(
            return_value=subprocess.CompletedProcess([], 0, "ok", "")
        )

        result = watchdog.reconcile_once(
            ROOT,
            DAEMON,
            self.pidfile,
            SV,
            1,
            2,
            table_fn=lambda: healthy_table(),
            run_sv_fn=run_sv,
            service_running_fn=running,
            wait_fn=self.immediate,
        )

        run_sv.assert_called_once_with(SV, ROOT, "crond", "up", 2)
        self.assertEqual(result["restarted_services"], ["crond"])
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

        result = watchdog.reconcile_once(
            ROOT,
            DAEMON,
            self.pidfile,
            SV,
            1,
            2,
            table_fn=table_fn,
            run_sv_fn=run_sv,
            service_running_fn=lambda *_args: True,
            wait_fn=self.immediate,
        )

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

        result = watchdog.reconcile_once(
            ROOT,
            DAEMON,
            self.pidfile,
            SV,
            1,
            2,
            table_fn=table_fn,
            service_running_fn=lambda *_args: True,
            wait_fn=self.immediate,
        )

        self.assertEqual(result["owned"], 7)
        self.assertGreaterEqual(calls["count"], 4)

    def test_manager_pidfile_mismatch_fails_closed(self) -> None:
        self.pidfile.write_text("101\n")
        with self.assertRaisesRegex(
            watchdog.WatchdogError,
            "native_pidfile_manager_mismatch:pidfile=101:manager=100",
        ):
            watchdog.reconcile_once(
                ROOT,
                DAEMON,
                self.pidfile,
                SV,
                1,
                2,
                table_fn=lambda: healthy_table(),
                service_running_fn=lambda *_args: True,
                wait_fn=self.immediate,
            )


if __name__ == "__main__":
    unittest.main()
