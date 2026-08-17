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
    table = {manager: row("runsvdir", str(ROOT), ppid=1)}
    for index, service in enumerate(watchdog.SERVICES, start=1):
        table[200 + index] = row("runsv", service, ppid=manager)
    table[CROND_PID] = row("crond", "-n", "-s", ppid=CROND_RUNSV_PID)
    return table


def orphan_table() -> dict[int, dict]:
    table = {}
    for index, service in enumerate(watchdog.SERVICES, start=1):
        table[200 + index] = row("runsv", service, ppid=1)
    table[CROND_PID] = row("crond", "-n", "-s", ppid=CROND_RUNSV_PID)
    return table


class Package7ManagerLossTests(unittest.TestCase):
    @staticmethod
    def immediate(predicate, _timeout):
        return predicate()

    def test_full_orphan_tree_is_drained_before_native_manager_start(self) -> None:
        state = {"table": orphan_table()}
        events: list[tuple[str, str]] = []
        expected_old = list(range(201, 208))

        def table_fn():
            return state["table"]

        def sv_fn(_sv, _root, service, command, _timeout):
            events.append((command, service))
            if command == "exit":
                old_pid = next(
                    pid
                    for pid, item in list(state["table"].items())
                    if item.get("argv", [])[-1:] == [service]
                    and Path(item.get("argv", [""])[0]).name == "runsv"
                )
                state["table"].pop(old_pid)
            return subprocess.CompletedProcess([], 0, "", "")

        with tempfile.TemporaryDirectory() as temp:
            pidfile = Path(temp) / "service-daemon.pid"
            crond_pidfile = Path(temp) / "crond.pid"
            crond_pidfile.write_text(f"{CROND_PID}\n")

            def command_fn(argv, _timeout):
                events.append(("START", "manager"))
                self.assertFalse(
                    any(
                        watchdog.runsv_rows(state["table"], service)
                        for service in watchdog.SERVICES
                    )
                )
                state["table"] = healthy_table()
                pidfile.write_text("100\n")
                crond_pidfile.write_text(f"{CROND_PID}\n")
                return subprocess.CompletedProcess(argv, 0, "", "")

            result = watchdog.reconcile_once(
                ROOT,
                DAEMON,
                pidfile,
                SV,
                1,
                2,
                table_fn=table_fn,
                command_fn=command_fn,
                run_sv_fn=sv_fn,
                service_running_fn=lambda *_args: True,
                wait_fn=self.immediate,
                crond_pidfile=crond_pidfile,
                child_pid_fn=lambda _root, service: (
                    CROND_PID if service == "crond" else None
                ),
            )

        self.assertEqual(result["drained_orphan_pids"], expected_old)
        start_index = events.index(("START", "manager"))
        self.assertTrue(
            all(
                events.index(("exit", service)) < start_index
                for service in watchdog.SERVICES
            )
        )
        self.assertEqual(result["owned"], 7)
        self.assertEqual(result["orphaned"], 0)

    def test_partial_zero_manager_supervisor_tree_fails_closed(self) -> None:
        table = orphan_table()
        table.pop(201)
        command = mock.Mock()
        run_sv = mock.Mock()

        with tempfile.TemporaryDirectory() as temp:
            pidfile = Path(temp) / "service-daemon.pid"
            crond_pidfile = Path(temp) / "crond.pid"
            crond_pidfile.write_text(f"{CROND_PID}\n")

            with self.assertRaisesRegex(
                watchdog.WatchdogError,
                "zero_manager_ambiguous_supervisor_topology",
            ):
                watchdog.reconcile_once(
                    ROOT,
                    DAEMON,
                    pidfile,
                    SV,
                    1,
                    2,
                    table_fn=lambda: table,
                    command_fn=command,
                    run_sv_fn=run_sv,
                    service_running_fn=lambda *_args: True,
                    wait_fn=self.immediate,
                    crond_pidfile=crond_pidfile,
                    child_pid_fn=lambda *_args: CROND_PID,
                )

        command.assert_not_called()
        run_sv.assert_not_called()


if __name__ == "__main__":
    unittest.main()
