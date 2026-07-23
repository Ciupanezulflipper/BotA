#!/usr/bin/env python3
"""Require every guarded runit service to be manager-owned and running."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

try:
    from . import runsvdir_guard as base
except ImportError:  # Direct execution from the tools directory.
    import runsvdir_guard as base


ORIGINAL_RECONCILE_ONCE = base.reconcile_once


def _require_manager_owned(
    service_root: Path,
    table_fn: Callable[[], dict[int, dict[str, Any]]],
) -> tuple[int, dict[str, Any]]:
    """Return the sole manager after exact ownership validation."""
    current = base.topology(table_fn(), service_root)
    if current["manager_count"] != 1:
        raise base.GuardError(
            f"manager_count_during_running_recovery:{current['manager_count']}"
        )
    manager = current["manager_pid"]
    if manager is None:
        raise base.GuardError("manager_missing_during_running_recovery")

    for service in base.SERVICES:
        row = current["services"][service]
        if row["runsv_count"] != 1:
            raise base.GuardError(
                f"runsv_count_during_running_recovery:{service}:"
                f"{row['runsv_count']}"
            )
        if row["owner"] != "manager":
            raise base.GuardError(
                f"ownership_changed_during_running_recovery:{service}:"
                f"{row['owner']}"
            )
    return manager, current


def reconcile_once(
    service_root: Path,
    sv_binary: Path,
    runsvdir_binary: Path,
    manager_log: Path,
    settle_seconds: float,
    command_timeout: int,
    table_fn: Callable[[], dict[int, dict[str, Any]]] = base.process_table,
) -> dict[str, Any]:
    """Reconcile ownership, recover down services, and require 7/7 running."""
    ownership = ORIGINAL_RECONCILE_ONCE(
        service_root,
        sv_binary,
        runsvdir_binary,
        manager_log,
        settle_seconds,
        command_timeout,
        table_fn=table_fn,
    )
    expected_manager = ownership["manager_pid"]
    restarted: list[str] = []

    for service in base.SERVICES:
        manager, _current = _require_manager_owned(service_root, table_fn)
        if manager != expected_manager:
            raise base.GuardError(
                "manager_changed_during_running_recovery:"
                f"expected={expected_manager}:actual={manager}"
            )

        if base.service_running(sv_binary, service_root, service):
            continue

        result = base.run_sv(
            sv_binary,
            service_root,
            service,
            "up",
            command_timeout,
        )
        if result.returncode != 0:
            detail = (result.stdout or result.stderr).strip()
            raise base.GuardError(
                f"sv_up_failed:{service}:rc={result.returncode}:{detail}"
            )

        if not base.wait_for(
            lambda service=service: base.service_running(
                sv_binary,
                service_root,
                service,
            ),
            command_timeout,
        ):
            raise base.GuardError(f"service_up_timeout:{service}")
        restarted.append(service)

    manager, final = _require_manager_owned(service_root, table_fn)
    if manager != expected_manager:
        raise base.GuardError(
            "manager_changed_after_running_recovery:"
            f"expected={expected_manager}:actual={manager}"
        )

    down = [
        service
        for service in base.SERVICES
        if not base.service_running(sv_binary, service_root, service)
    ]
    if down:
        raise base.GuardError("services_not_running:" + ",".join(down))

    final["running"] = len(base.SERVICES)
    final["restarted_services"] = restarted
    return final


def main() -> int:
    """Run the base guard with strict 7/7 running-state enforcement."""
    base.reconcile_once = reconcile_once
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
