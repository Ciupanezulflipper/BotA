#!/usr/bin/env python3
"""Extend the native-manager migration to exact mixed owned/orphan topologies."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__:
    from tools import native_service_daemon_migration as base
    from tools import native_service_daemon_watchdog as watchdog
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import native_service_daemon_migration as base
    from tools import native_service_daemon_watchdog as watchdog

MigrationError = base.MigrationError
_ORIGINAL_PREFLIGHT = base.migration_preflight
_ORIGINAL_EXECUTE_CUTOVER = base.execute_cutover


def _exact_native_partial(state: dict[str, Any]) -> bool:
    """Return true for one exact supervisor per service with at least one orphan."""
    rows = state["services"]
    service_count = len(watchdog.SERVICES)
    return (
        state["manager_count"] == 1
        and state["owned"] + state["orphaned"] == service_count
        and 0 < state["orphaned"] < service_count
        and state["invalid"] == 0
        and state["duplicates"] == 0
        and all(
            rows[service]["runsv_count"] == 1
            and rows[service]["owner"] in {"manager", "pid1_orphan"}
            for service in watchdog.SERVICES
        )
    )


def migration_preflight(
    table: dict[int, dict[str, Any]],
    service_root: Path,
    pidfile_value: int | None,
    watchdog_count: int,
    legacy_guard_count: int,
) -> tuple[str, int | None]:
    """Accept the original source states plus exact native partial-orphan state."""
    state = watchdog.topology(table, service_root)
    if pidfile_value is not None:
        if watchdog_count:
            raise MigrationError(f"preflight_new_watchdog_count:{watchdog_count}")
        if legacy_guard_count:
            raise MigrationError(f"preflight_legacy_guard_count:{legacy_guard_count}")
        if state["manager_count"] > 1:
            raise MigrationError(f"preflight_manager_count:{state['manager_count']}")
        if (
            state["manager_count"] != 1
            or state["manager_pid"] != pidfile_value
        ):
            raise MigrationError(
                "preflight_native_pidfile_manager_mismatch:"
                f"pidfile={pidfile_value};manager={state['manager_pid']};"
                f"count={state['manager_count']}"
            )
        if _exact_native_partial(state):
            return "native_manager_partial_orphans", None
    return _ORIGINAL_PREFLIGHT(
        table,
        service_root,
        pidfile_value,
        watchdog_count,
        legacy_guard_count,
    )


def execute_cutover(**kwargs: Any) -> dict[str, Any]:
    """Reuse the original cutover while skipping native start for partial orphans."""
    preflight_fn = kwargs["preflight_fn"]
    actual_source: list[str] = []

    def compatible_preflight() -> tuple[str, int | None]:
        source_state, manager = preflight_fn()
        actual_source.append(source_state)
        if source_state == "native_manager_partial_orphans":
            return "native_manager_orphans", manager
        return source_state, manager

    kwargs["preflight_fn"] = compatible_preflight
    result = _ORIGINAL_EXECUTE_CUTOVER(**kwargs)
    if actual_source == ["native_manager_partial_orphans"]:
        result["source_state"] = "native_manager_partial_orphans"
    return result


def install() -> None:
    """Install the compatibility hooks into the original migration module."""
    base.migration_preflight = migration_preflight
    base.detached_preflight = migration_preflight
    base.execute_cutover = execute_cutover


def main() -> int:
    """Run the original migration with partial-orphan compatibility enabled."""
    install()
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationError as exc:
        print(f"NATIVE_MANAGER_MIGRATION=FAIL:{exc}", file=sys.stderr)
        raise SystemExit(1)
