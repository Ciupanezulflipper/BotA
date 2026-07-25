from __future__ import annotations

import unittest
from pathlib import Path

from tools import native_service_daemon_watchdog as watchdog
from tools import native_service_daemon_watchdog_finalizer as finalizer

ROOT = Path("/data/data/com.termux/files/usr/var/service")


def row(exe: str, *argv: str, ppid: int) -> dict:
    return {"ppid": ppid, "argv": [exe, *argv]}


def fully_owned_table(manager: int = 100) -> dict[int, dict]:
    table = {manager: row("runsvdir", str(ROOT), ppid=1)}
    for index, service in enumerate(watchdog.SERVICES, start=1):
        table[200 + index] = row("runsv", service, ppid=manager)
    return table


class FinalizerPreflightTests(unittest.TestCase):
    def assert_rejected(
        self,
        pattern: str,
        *,
        table: dict[int, dict] | None = None,
        pidfile: int | None = 100,
        watchdog_count: int = 0,
        legacy_guard_count: int = 0,
        running_services: set[str] | None = None,
    ) -> None:
        with self.assertRaisesRegex(finalizer.MigrationError, pattern):
            finalizer.finalizer_preflight(
                fully_owned_table() if table is None else table,
                ROOT,
                pidfile,
                watchdog_count,
                legacy_guard_count,
                set(watchdog.SERVICES)
                if running_services is None
                else running_services,
            )

    def test_accepts_fully_owned_running_without_watchdog(self) -> None:
        state = finalizer.finalizer_preflight(
            fully_owned_table(), ROOT, 100, 0, 0, set(watchdog.SERVICES)
        )
        self.assertEqual(state["owned"], len(watchdog.SERVICES))
        self.assertEqual(state["orphaned"], 0)

    def test_rejects_pidfile_mismatch(self) -> None:
        self.assert_rejected(
            "preflight_native_pidfile_manager_mismatch", pidfile=999
        )

    def test_rejects_existing_watchdog(self) -> None:
        self.assert_rejected("preflight_new_watchdog_count:1", watchdog_count=1)

    def test_rejects_orphan(self) -> None:
        table = fully_owned_table()
        table[201]["ppid"] = 1
        self.assert_rejected("preflight_native_fully_owned_topology", table=table)

    def test_rejects_duplicate(self) -> None:
        table = fully_owned_table()
        table[999] = row("runsv", watchdog.SERVICES[0], ppid=100)
        self.assert_rejected("preflight_native_fully_owned_topology", table=table)

    def test_rejects_invalid_owner(self) -> None:
        table = fully_owned_table()
        table[201]["ppid"] = 999
        self.assert_rejected("preflight_native_fully_owned_topology", table=table)

    def test_rejects_missing_service(self) -> None:
        table = fully_owned_table()
        table.pop(201)
        self.assert_rejected("preflight_native_fully_owned_topology", table=table)

    def test_rejects_service_not_running(self) -> None:
        running = set(watchdog.SERVICES)
        running.remove(watchdog.SERVICES[0])
        self.assert_rejected("preflight_services_not_running", running_services=running)

    def test_rejects_legacy_guard(self) -> None:
        self.assert_rejected("preflight_legacy_guard_count:1", legacy_guard_count=1)


if __name__ == "__main__":
    unittest.main()
