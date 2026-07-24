from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from tools import native_service_daemon_migration as migration
from tools import native_service_daemon_watchdog as watchdog

ROOT = Path("/data/data/com.termux/files/usr/var/service")


def row(exe: str, *argv: str, ppid: int) -> dict:
    return {"ppid": ppid, "argv": [exe, *argv]}


def detached_table(manager: int = 100) -> dict[int, dict]:
    table = {manager: row("runsvdir", "-P", str(ROOT), ppid=1)}
    for index, service in enumerate(watchdog.SERVICES, start=1):
        table[200 + index] = row("runsv", service, ppid=manager)
    return table


class PreflightTests(unittest.TestCase):
    def test_accepts_one_detached_manager_with_seven_owned(self) -> None:
        self.assertEqual(
            migration.detached_preflight(detached_table(), ROOT, None, 0, 0),
            100,
        )

    def test_rejects_native_pidfile(self) -> None:
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_native_pidfile_present"
        ):
            migration.detached_preflight(detached_table(), ROOT, 100, 0, 0)

    def test_rejects_non_p_manager(self) -> None:
        table = detached_table()
        table[100] = row("runsvdir", str(ROOT), ppid=1)
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_manager_not_detached_p"
        ):
            migration.detached_preflight(table, ROOT, None, 0, 0)

    def test_rejects_legacy_guard(self) -> None:
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_legacy_guard_count"
        ):
            migration.detached_preflight(detached_table(), ROOT, None, 0, 1)

    def test_rejects_multiple_managers(self) -> None:
        table = detached_table()
        table[101] = row("runsvdir", str(ROOT), ppid=1)
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_manager_count:2"
        ):
            migration.detached_preflight(table, ROOT, None, 0, 0)


class CutoverTests(unittest.TestCase):
    @staticmethod
    def immediate(predicate, _timeout):
        return predicate()

    def test_happy_path(self) -> None:
        alive = {100: True}
        events = []

        def terminate(pid):
            events.append(("term", pid))
            alive[pid] = False

        result = migration.execute_cutover(
            preflight_fn=lambda: 100,
            terminate_fn=terminate,
            manager_alive_fn=lambda pid: alive[pid],
            start_native_fn=lambda: events.append(("native", None)),
            reconcile_native_fn=lambda: {"owned": 7},
            verify_native_fn=lambda require: {
                "manager_pid": 300,
                "watchdog": require,
            },
            start_watchdog_fn=lambda: events.append(("watchdog", None)),
            rollback_fn=mock.Mock(),
            wait_fn=self.immediate,
            term_timeout=1,
        )

        self.assertEqual(result["old_manager_pid"], 100)
        self.assertEqual(result["new_manager_pid"], 300)
        self.assertEqual(
            events,
            [("term", 100), ("native", None), ("watchdog", None)],
        )

    def test_term_timeout_does_not_rollback(self) -> None:
        rollback = mock.Mock()
        with self.assertRaisesRegex(
            migration.MigrationError, "detached_manager_term_timeout"
        ):
            migration.execute_cutover(
                preflight_fn=lambda: 100,
                terminate_fn=lambda _pid: None,
                manager_alive_fn=lambda _pid: True,
                start_native_fn=mock.Mock(),
                reconcile_native_fn=mock.Mock(),
                verify_native_fn=mock.Mock(),
                start_watchdog_fn=mock.Mock(),
                rollback_fn=rollback,
                wait_fn=lambda _predicate, _timeout: False,
                term_timeout=1,
            )
        rollback.assert_not_called()

    def test_failure_after_term_invokes_rollback(self) -> None:
        rollback = mock.Mock(return_value={"owned": 7})

        def fail_start():
            raise RuntimeError("boom")

        with self.assertRaisesRegex(migration.MigrationError, "rollback="):
            migration.execute_cutover(
                preflight_fn=lambda: 100,
                terminate_fn=lambda _pid: None,
                manager_alive_fn=lambda _pid: False,
                start_native_fn=fail_start,
                reconcile_native_fn=mock.Mock(),
                verify_native_fn=mock.Mock(),
                start_watchdog_fn=mock.Mock(),
                rollback_fn=rollback,
                wait_fn=self.immediate,
                term_timeout=1,
            )
        rollback.assert_called_once()

    def test_rollback_failure_is_explicit(self) -> None:
        def fail_start():
            raise RuntimeError("boom")

        def fail_rollback():
            raise RuntimeError("rollback boom")

        with self.assertRaisesRegex(migration.MigrationError, "rollback_failed"):
            migration.execute_cutover(
                preflight_fn=lambda: 100,
                terminate_fn=lambda _pid: None,
                manager_alive_fn=lambda _pid: False,
                start_native_fn=fail_start,
                reconcile_native_fn=mock.Mock(),
                verify_native_fn=mock.Mock(),
                start_watchdog_fn=mock.Mock(),
                rollback_fn=fail_rollback,
                wait_fn=self.immediate,
                term_timeout=1,
            )


if __name__ == "__main__":
    unittest.main()
