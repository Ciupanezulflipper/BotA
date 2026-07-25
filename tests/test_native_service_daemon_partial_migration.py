from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from tools import native_service_daemon_partial_migration as migration
from tools import native_service_daemon_watchdog as watchdog

ROOT = Path("/data/data/com.termux/files/usr/var/service")


def row(exe: str, *argv: str, ppid: int) -> dict:
    return {"ppid": ppid, "argv": [exe, *argv]}


def mixed_table(owned: int, manager: int = 100) -> dict[int, dict]:
    table = {manager: row("runsvdir", str(ROOT), ppid=1)}
    for index, service in enumerate(watchdog.SERVICES, start=1):
        owner = manager if index <= owned else 1
        table[200 + index] = row("runsv", service, ppid=owner)
    return table


class PartialPreflightTests(unittest.TestCase):
    def test_accepts_one_owned_six_orphans(self) -> None:
        self.assertEqual(
            migration.migration_preflight(mixed_table(1), ROOT, 100, 0, 0),
            ("native_manager_partial_orphans", None),
        )

    def test_accepts_other_mixed_distributions(self) -> None:
        for owned in range(2, len(watchdog.SERVICES)):
            with self.subTest(owned=owned):
                self.assertEqual(
                    migration.migration_preflight(
                        mixed_table(owned), ROOT, 100, 0, 0
                    ),
                    ("native_manager_partial_orphans", None),
                )

    def test_all_owned_is_not_classified_as_partial(self) -> None:
        with self.assertRaises(migration.MigrationError):
            migration.migration_preflight(
                mixed_table(len(watchdog.SERVICES)), ROOT, 100, 0, 0
            )

    def test_rejects_missing_service(self) -> None:
        table = mixed_table(1)
        table.pop(201)
        with self.assertRaises(migration.MigrationError):
            migration.migration_preflight(table, ROOT, 100, 0, 0)

    def test_rejects_duplicate_service(self) -> None:
        table = mixed_table(1)
        table[999] = row("runsv", watchdog.SERVICES[0], ppid=1)
        with self.assertRaises(migration.MigrationError):
            migration.migration_preflight(table, ROOT, 100, 0, 0)

    def test_rejects_invalid_owner(self) -> None:
        table = mixed_table(1)
        table[202]["ppid"] = 999
        with self.assertRaises(migration.MigrationError):
            migration.migration_preflight(table, ROOT, 100, 0, 0)

    def test_rejects_pidfile_manager_mismatch(self) -> None:
        with self.assertRaisesRegex(
            migration.MigrationError,
            "preflight_native_pidfile_manager_mismatch",
        ):
            migration.migration_preflight(mixed_table(1), ROOT, 999, 0, 0)


class PartialCutoverTests(unittest.TestCase):
    def test_skips_native_start_and_preserves_source_label(self) -> None:
        start_native = mock.Mock()
        terminate = mock.Mock()
        manager_alive = mock.Mock()
        events: list[str] = []

        result = migration.execute_cutover(
            preflight_fn=lambda: ("native_manager_partial_orphans", None),
            terminate_fn=terminate,
            manager_alive_fn=manager_alive,
            start_native_fn=start_native,
            reconcile_native_fn=lambda: events.append("reconcile") or {"owned": 7},
            verify_native_fn=lambda require: {
                "manager_pid": 100,
                "watchdog": require,
            },
            start_watchdog_fn=lambda: events.append("watchdog"),
            rollback_fn=mock.Mock(),
            wait_fn=lambda predicate, _timeout: predicate(),
            term_timeout=1,
        )

        self.assertEqual(result["source_state"], "native_manager_partial_orphans")
        self.assertEqual(events, ["reconcile", "watchdog"])
        start_native.assert_not_called()
        terminate.assert_not_called()
        manager_alive.assert_not_called()


if __name__ == "__main__":
    unittest.main()
