#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

TARGET = Path('tools/native_service_daemon_watchdog.py')
EXPECTED_BLOB = '6bba41b27e4a7d9a37f011e8b81093d510adf653'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'PACKAGE7_PATCH_ABORT={label}:match_count={count}')
    return text.replace(old, new, 1)


def main() -> int:
    actual_blob = subprocess.check_output(
        ['git', 'hash-object', str(TARGET)], text=True
    ).strip()
    if actual_blob != EXPECTED_BLOB:
        raise SystemExit(
            f'PACKAGE7_PATCH_ABORT=BASE_BLOB_MISMATCH:{actual_blob}'
        )

    text = TARGET.read_text(encoding='utf-8')

    anchor = '''def handoff(service, manager, root, sv, timeout, table_fn, sv_fn,\n            running_fn, wait_fn):\n'''
    helper = '''def _exact_pid1_orphan_tree(state):\n    return (\n        state["manager_count"] == 0\n        and state["owned"] == 0\n        and state["orphaned"] == len(SERVICES)\n        and state["invalid"] == 0\n        and state["duplicates"] == 0\n        and all(\n            state["services"][service]["runsv_count"] == 1\n            and state["services"][service]["owner"] == "pid1_orphan"\n            for service in SERVICES\n        )\n    )\n\n\ndef drain_orphan_tree_before_native(root, sv, timeout, table_fn=process_table,\n                                    sv_fn=sv_cmd, wait_fn=wait):\n    """Drain one exact PID-1 orphan tree before starting a new manager.\n\n    Starting a replacement runsvdir while the old orphan supervisors still own\n    their supervise locks creates retry churn and mixed ownership.  Quiesce and\n    exit the exact seven old supervisors first; then the native manager can\n    acquire every service directory cleanly in one convergence.\n    """\n    state = topology(table_fn(), root)\n    if not _exact_pid1_orphan_tree(state):\n        raise WatchdogError(\n            "orphan_tree_not_exact:"\n            f"manager={state['manager_count']};owned={state['owned']};"\n            f"orphaned={state['orphaned']};invalid={state['invalid']};"\n            f"duplicates={state['duplicates']}"\n        )\n\n    old_pids = [\n        int(state["services"][service]["runsv_pid"])\n        for service in SERVICES\n    ]\n    for service in SERVICES:\n        row = topology(table_fn(), root)["services"][service]\n        if row["runsv_count"] != 1 or row["owner"] != "pid1_orphan":\n            raise WatchdogError(\n                f"orphan_drain_precondition_changed:{service}"\n            )\n        for command in ("down", "exit"):\n            result = sv_fn(sv, root, service, command, timeout)\n            if result.returncode:\n                detail = (result.stdout or result.stderr).strip()\n                raise WatchdogError(\n                    f"sv_{command}_failed:{service}:"\n                    f"rc={result.returncode}:{detail}"\n                )\n\n    def drained():\n        table = table_fn()\n        if managers(table, root):\n            return False\n        return not any(\n            runsv_rows(table, service) for service in SERVICES\n        )\n\n    if not wait_fn(drained, timeout):\n        table = table_fn()\n        active = [\n            service for service in SERVICES\n            if runsv_rows(table, service)\n        ]\n        raise WatchdogError(\n            "orphan_tree_drain_timeout:"\n            f"active={','.join(active)}"\n        )\n    return old_pids\n\n\n'''
    text = replace_once(text, anchor, helper + anchor, 'helper_anchor')

    old_reconcile = '''    started, stale = False, None\n    if initial["manager_count"] == 0:\n        manager, stale = start_native(root, daemon, pidfile, settle, timeout,\n                                      table_fn, command_fn, wait_fn)\n        started = True\n    else:\n        manager = require_native(root, pidfile, table_fn)\n\n    if crond_pidfile is None:\n        crond_pidfile = pidfile.parent / "crond.pid"\n    final = reconcile_services(\n        manager, root, pidfile, crond_pidfile, sv, timeout, table_fn,\n        run_sv_fn, service_running_fn, wait_fn, child_pid_fn, terminate_fn)\n    final.update(native_manager_started=started, stale_pidfile_removed=stale)\n    return final\n'''
    new_reconcile = '''    drained_orphan_pids = []\n    started, stale = False, None\n    if initial["manager_count"] == 0:\n        active_runsv = sum(\n            row["runsv_count"] for row in initial["services"].values()\n        )\n        if active_runsv:\n            if not _exact_pid1_orphan_tree(initial):\n                raise WatchdogError(\n                    "zero_manager_ambiguous_supervisor_topology:"\n                    f"active={active_runsv};orphaned={initial['orphaned']};"\n                    f"invalid={initial['invalid']};"\n                    f"duplicates={initial['duplicates']}"\n                )\n            drained_orphan_pids = drain_orphan_tree_before_native(\n                root, sv, timeout, table_fn, run_sv_fn, wait_fn\n            )\n        manager, stale = start_native(root, daemon, pidfile, settle, timeout,\n                                      table_fn, command_fn, wait_fn)\n        started = True\n    else:\n        manager = require_native(root, pidfile, table_fn)\n\n    if crond_pidfile is None:\n        crond_pidfile = pidfile.parent / "crond.pid"\n    final = reconcile_services(\n        manager, root, pidfile, crond_pidfile, sv, timeout, table_fn,\n        run_sv_fn, service_running_fn, wait_fn, child_pid_fn, terminate_fn)\n    final.update(\n        native_manager_started=started,\n        stale_pidfile_removed=stale,\n        drained_orphan_pids=drained_orphan_pids,\n    )\n    return final\n'''
    text = replace_once(text, old_reconcile, new_reconcile, 'reconcile_once')

    old_event = '''                state = (\n                    "healthy", final["manager_pid"],\n                    json.dumps(final.get("singleton_repairs", {}), sort_keys=True),\n                )\n'''
    new_event = '''                if final.get("drained_orphan_pids"):\n                    event(\n                        args.log, "orphan_tree_drained_before_native",\n                        drained_orphan_pids=final["drained_orphan_pids"],\n                        manager_pid=final["manager_pid"],\n                    )\n                state = (\n                    "healthy", final["manager_pid"],\n                    json.dumps(final.get("singleton_repairs", {}), sort_keys=True),\n                )\n'''
    text = replace_once(text, old_event, new_event, 'recovery_event')

    TARGET.write_text(text, encoding='utf-8')
    print('PACKAGE7_PATCH=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
