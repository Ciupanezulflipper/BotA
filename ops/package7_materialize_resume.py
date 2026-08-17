#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

TARGET = Path('tools/native_service_daemon_watchdog.py')
EXPECTED_BLOB = '69f9515a38f4b97f8ad0a2981c5918bab75f0bdb'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'PACKAGE7_RESUME_PATCH_ABORT={label}:match_count={count}')
    return text.replace(old, new, 1)


def main() -> int:
    actual = subprocess.check_output(['git', 'hash-object', str(TARGET)], text=True).strip()
    if actual != EXPECTED_BLOB:
        raise SystemExit(f'PACKAGE7_RESUME_PATCH_ABORT=BASE_BLOB_MISMATCH:{actual}')
    text = TARGET.read_text(encoding='utf-8')

    start = text.index('def _exact_pid1_orphan_tree(state):\n')
    end = text.index('\n\ndef handoff(', start)
    new = '''def _drainable_zero_manager_forest(state):\n    if state["manager_count"] != 0 or state["duplicates"]:\n        return False\n    for service in SERVICES:\n        row = state["services"][service]\n        if row["runsv_count"] == 0:\n            continue\n        if row["runsv_count"] != 1 or row["owner"] != "pid1_orphan":\n            return False\n    return True\n\n\ndef drain_orphan_tree_before_native(root, sv, timeout, table_fn=process_table,\n                                    sv_fn=sv_cmd, wait_fn=wait):\n    """Drain a safe PID-1 orphan forest before starting a new manager.\n\n    A previous drain can be interrupted after some supervisors have already\n    exited.  Treat missing supervisors as already drained, but require every\n    remaining active required `runsv` to be exactly one PID-1 orphan.  This\n    makes manager-loss recovery resumable without ever starting a replacement\n    runsvdir against an ambiguous existing supervisor.\n    """\n    state = topology(table_fn(), root)\n    if not _drainable_zero_manager_forest(state):\n        raise WatchdogError(\n            "orphan_forest_not_safe:"\n            f"manager={state['manager_count']};owned={state['owned']};"\n            f"orphaned={state['orphaned']};invalid={state['invalid']};"\n            f"duplicates={state['duplicates']}"\n        )\n\n    orphan_services = [\n        service for service in SERVICES\n        if state["services"][service]["runsv_count"] == 1\n    ]\n    old_pids = [\n        int(state["services"][service]["runsv_pid"])\n        for service in orphan_services\n    ]\n    for service in orphan_services:\n        row = topology(table_fn(), root)["services"][service]\n        if row["runsv_count"] != 1 or row["owner"] != "pid1_orphan":\n            raise WatchdogError(\n                f"orphan_drain_precondition_changed:{service}"\n            )\n        for command in ("down", "exit"):\n            result = sv_fn(sv, root, service, command, timeout)\n            if result.returncode:\n                detail = (result.stdout or result.stderr).strip()\n                raise WatchdogError(\n                    f"sv_{command}_failed:{service}:"\n                    f"rc={result.returncode}:{detail}"\n                )\n\n    def drained():\n        table = table_fn()\n        if managers(table, root):\n            return False\n        return not any(\n            runsv_rows(table, service) for service in SERVICES\n        )\n\n    if not wait_fn(drained, timeout):\n        table = table_fn()\n        active = [\n            service for service in SERVICES\n            if runsv_rows(table, service)\n        ]\n        raise WatchdogError(\n            "orphan_tree_drain_timeout:"\n            f"active={','.join(active)}"\n        )\n    return old_pids\n'''
    text = text[:start] + new + text[end:]

    old_guard = '''        if active_runsv:\n            if not _exact_pid1_orphan_tree(initial):\n                raise WatchdogError(\n                    "zero_manager_ambiguous_supervisor_topology:"\n                    f"active={active_runsv};orphaned={initial['orphaned']};"\n                    f"invalid={initial['invalid']};"\n                    f"duplicates={initial['duplicates']}"\n                )\n            drained_orphan_pids = drain_orphan_tree_before_native(\n'''
    new_guard = '''        if active_runsv:\n            if not _drainable_zero_manager_forest(initial):\n                raise WatchdogError(\n                    "zero_manager_ambiguous_supervisor_topology:"\n                    f"active={active_runsv};orphaned={initial['orphaned']};"\n                    f"invalid={initial['invalid']};"\n                    f"duplicates={initial['duplicates']}"\n                )\n            drained_orphan_pids = drain_orphan_tree_before_native(\n'''
    text = replace_once(text, old_guard, new_guard, 'reconcile_guard')
    TARGET.write_text(text, encoding='utf-8')
    print('PACKAGE7_RESUME_PATCH=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
