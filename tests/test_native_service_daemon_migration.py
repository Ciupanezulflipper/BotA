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


def orphan_table() -> dict[int, dict]:
    return {
        200 + index: row("runsv", service, ppid=1)
        for index, service in enumerate(watchdog.SERVICES, start=1)
    }


def native_manager_orphan_table(manager: int = 100) -> dict[int, dict]:
    table = {manager: row("runsvdir", str(ROOT), ppid=1)}
    table.update(orphan_table())
    return table


class PreflightTests(unittest.TestCase):
    def test_accepts_one_detached_manager_with_seven_owned(self) -> None:
        self.assertEqual(
            migration.migration_preflight(detached_table(), ROOT, None, 0, 0),
            ("detached_manager", 100),
        )

    def test_accepts_zero_manager_with_exactly_seven_orphans(self) -> None:
        self.assertEqual(
            migration.migration_preflight(orphan_table(), ROOT, None, 0, 0),
            ("orphan_only", None),
        )

    def test_accepts_native_manager_with_exactly_seven_orphans(self) -> None:
        self.assertEqual(
            migration.migration_preflight(
                native_manager_orphan_table(), ROOT, 100, 0, 0
            ),
            ("native_manager_orphans", None),
        )

    def test_rejects_native_pidfile_manager_mismatch(self) -> None:
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_native_pidfile_manager_mismatch"
        ):
            migration.migration_preflight(
                native_manager_orphan_table(), ROOT, 999, 0, 0
            )

    def test_rejects_native_manager_with_non_exact_orphans(self) -> None:
        table = native_manager_orphan_table()
        table.pop(next(pid for pid in table if pid != 100))
        with self.assertRaisesRegex(
            migration.MigrationError,
            "preflight_topology|preflight_native_manager_topology",
        ):
            migration.migration_preflight(table, ROOT, 100, 0, 0)

    def test_rejects_zero_manager_with_missing_orphan(self) -> None:
        table = orphan_table()
        table.pop(next(iter(table)))
        with self.assertRaisesRegex(
            migration.MigrationError,
            "preflight_topology|preflight_zero_manager_topology",
        ):
            migration.migration_preflight(table, ROOT, None, 0, 0)

    def test_rejects_zero_manager_with_non_pid1_owner(self) -> None:
        table = orphan_table()
        first = next(iter(table))
        table[first]["ppid"] = 999
        with self.assertRaisesRegex(
            migration.MigrationError,
            "preflight_topology|preflight_zero_manager_topology",
        ):
            migration.migration_preflight(table, ROOT, None, 0, 0)

    def test_rejects_non_p_manager(self) -> None:
        table = detached_table()
        table[100] = row("runsvdir", str(ROOT), ppid=1)
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_manager_not_detached_p"
        ):
            migration.migration_preflight(table, ROOT, None, 0, 0)

    def test_rejects_legacy_guard(self) -> None:
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_legacy_guard_count"
        ):
            migration.migration_preflight(detached_table(), ROOT, None, 0, 1)

    def test_rejects_multiple_managers(self) -> None:
        table = detached_table()
        table[101] = row("runsvdir", str(ROOT), ppid=1)
        with self.assertRaisesRegex(
            migration.MigrationError, "preflight_manager_count:2"
        ):
            migration.migration_preflight(table, ROOT, None, 0, 0)


class CutoverTests(unittest.TestCase):
    @staticmethod
    def immediate(predicate, _timeout):
        return predicate()

    def test_detached_manager_happy_path(self) -> None:
        alive = {100: True}
        events = []

        def terminate(pid):
            events.append(("term", pid))
            alive[pid] = False

        result = migration.execute_cutover(
            preflight_fn=lambda: ("detached_manager", 100),
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

        self.assertEqual(result["source_state"], "detached_manager")
        self.assertEqual(result["old_manager_pid"], 100)
        self.assertEqual(result["new_manager_pid"], 300)
        self.assertEqual(
            events,
            [("term", 100), ("native", None), ("watchdog", None)],
        )

    def test_orphan_only_happy_path_does_not_signal_old_manager(self) -> None:
        terminate = mock.Mock()
        manager_alive = mock.Mock()
        events = []

        result = migration.execute_cutover(
            preflight_fn=lambda: ("orphan_only", None),
            terminate_fn=terminate,
            manager_alive_fn=manager_alive,
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

        self.assertEqual(result["source_state"], "orphan_only")
        self.assertIsNone(result["old_manager_pid"])
        self.assertEqual(events, [("native", None), ("watchdog", None)])
        terminate.assert_not_called()
        manager_alive.assert_not_called()

    def test_native_manager_orphans_skips_manager_start_and_signal(self) -> None:
        terminate = mock.Mock()
        manager_alive = mock.Mock()
        start_native = mock.Mock()
        events = []

        result = migration.execute_cutover(
            preflight_fn=lambda: ("native_manager_orphans", None),
            terminate_fn=terminate,
            manager_alive_fn=manager_alive,
            start_native_fn=start_native,
            reconcile_native_fn=lambda: events.append(("reconcile", None)) or {"owned": 7},
            verify_native_fn=lambda require: {
                "manager_pid": 100,
                "watchdog": require,
            },
            start_watchdog_fn=lambda: events.append(("watchdog", None)),
            rollback_fn=mock.Mock(),
            wait_fn=self.immediate,
            term_timeout=1,
        )

        self.assertEqual(result["source_state"], "native_manager_orphans")
        self.assertIsNone(result["old_manager_pid"])
        self.assertEqual(result["new_manager_pid"], 100)
        self.assertEqual(events, [("reconcile", None), ("watchdog", None)])
        terminate.assert_not_called()
        manager_alive.assert_not_called()
        start_native.assert_not_called()

    def test_term_timeout_does_not_rollback(self) -> None:
        rollback = mock.Mock()
        with self.assertRaisesRegex(
            migration.MigrationError, "detached_manager_term_timeout"
        ):
            migration.execute_cutover(
                preflight_fn=lambda: ("detached_manager", 100),
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

    def test_detached_failure_passes_old_manager_to_rollback(self) -> None:
        rollback = mock.Mock(return_value={"owned": 7})

        with self.assertRaisesRegex(migration.MigrationError, "rollback="):
            migration.execute_cutover(
                preflight_fn=lambda: ("detached_manager", 100),
                terminate_fn=lambda _pid: None,
                manager_alive_fn=lambda _pid: False,
                start_native_fn=mock.Mock(side_effect=RuntimeError("boom")),
                reconcile_native_fn=mock.Mock(),
                verify_native_fn=mock.Mock(),
                start_watchdog_fn=mock.Mock(),
                rollback_fn=rollback,
                wait_fn=self.immediate,
                term_timeout=1,
            )
        rollback.assert_called_once_with(100)

    def test_orphan_failure_passes_none_to_rollback(self) -> None:
        rollback = mock.Mock(return_value={"orphaned": 7})

        with self.assertRaisesRegex(migration.MigrationError, "rollback="):
            migration.execute_cutover(
                preflight_fn=lambda: ("orphan_only", None),
                terminate_fn=mock.Mock(),
                manager_alive_fn=mock.Mock(),
                start_native_fn=mock.Mock(side_effect=RuntimeError("boom")),
                reconcile_native_fn=mock.Mock(),
                verify_native_fn=mock.Mock(),
                start_watchdog_fn=mock.Mock(),
                rollback_fn=rollback,
                wait_fn=self.immediate,
                term_timeout=1,
            )
        rollback.assert_called_once_with(None)

    def test_native_manager_orphan_failure_passes_none_to_rollback(self) -> None:
        rollback = mock.Mock(return_value={"orphaned": 7})

        with self.assertRaisesRegex(migration.MigrationError, "rollback="):
            migration.execute_cutover(
                preflight_fn=lambda: ("native_manager_orphans", None),
                terminate_fn=mock.Mock(),
                manager_alive_fn=mock.Mock(),
                start_native_fn=mock.Mock(),
                reconcile_native_fn=mock.Mock(side_effect=RuntimeError("boom")),
                verify_native_fn=mock.Mock(),
                start_watchdog_fn=mock.Mock(),
                rollback_fn=rollback,
                wait_fn=self.immediate,
                term_timeout=1,
            )
        rollback.assert_called_once_with(None)

    def test_rollback_failure_is_explicit(self) -> None:
        with self.assertRaisesRegex(migration.MigrationError, "rollback_failed"):
            migration.execute_cutover(
                preflight_fn=lambda: ("orphan_only", None),
                terminate_fn=mock.Mock(),
                manager_alive_fn=mock.Mock(),
                start_native_fn=mock.Mock(side_effect=RuntimeError("boom")),
                reconcile_native_fn=mock.Mock(),
                verify_native_fn=mock.Mock(),
                start_watchdog_fn=mock.Mock(),
                rollback_fn=mock.Mock(side_effect=RuntimeError("rollback boom")),
                wait_fn=self.immediate,
                term_timeout=1,
            )


if __name__ == "__main__":
    unittest.main()
