#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

TARGET = Path('tools/native_service_daemon_watchdog.py')
EXPECTED_BLOB = '687a66d9c93ed96c9ce4f325b67d7a87986dc074'


def main() -> int:
    actual = subprocess.check_output(['git', 'hash-object', str(TARGET)], text=True).strip()
    if actual != EXPECTED_BLOB:
        raise SystemExit(f'PACKAGE7_COMPLEXITY_ABORT=BASE_BLOB_MISMATCH:{actual}')
    text = TARGET.read_text(encoding='utf-8')
    start = text.index('def drain_orphan_tree_before_native(')
    end = text.index('\n\ndef handoff(', start)
    replacement = '''def _drain_one_pid1_orphan(root, service, sv, timeout, table_fn, sv_fn):\n    row = topology(table_fn(), root)["services"][service]\n    if row["runsv_count"] != 1 or row["owner"] != "pid1_orphan":\n        raise WatchdogError(f"orphan_drain_precondition_changed:{service}")\n    for command in ("down", "exit"):\n        result = sv_fn(sv, root, service, command, timeout)\n        if result.returncode:\n            detail = (result.stdout or result.stderr).strip()\n            raise WatchdogError(\n                f"sv_{command}_failed:{service}:"\n                f"rc={result.returncode}:{detail}"\n            )\n\n\ndef _orphan_forest_drained(root, table_fn):\n    table = table_fn()\n    return (\n        not managers(table, root)\n        and not any(runsv_rows(table, service) for service in SERVICES)\n    )\n\n\ndef _active_required_runsv(table_fn):\n    table = table_fn()\n    return [service for service in SERVICES if runsv_rows(table, service)]\n\n\ndef drain_orphan_tree_before_native(root, sv, timeout, table_fn=process_table,\n                                    sv_fn=sv_cmd, wait_fn=wait):\n    """Drain a safe PID-1 orphan forest before starting a new manager.\n\n    A previous drain can be interrupted after some supervisors have already\n    exited.  Treat missing supervisors as already drained, but require every\n    remaining active required `runsv` to be exactly one PID-1 orphan.  This\n    makes manager-loss recovery resumable without ever starting a replacement\n    runsvdir against an ambiguous existing supervisor.\n    """\n    state = topology(table_fn(), root)\n    if not _drainable_zero_manager_forest(state):\n        raise WatchdogError(\n            "orphan_forest_not_safe:"\n            f"manager={state['manager_count']};owned={state['owned']};"\n            f"orphaned={state['orphaned']};invalid={state['invalid']};"\n            f"duplicates={state['duplicates']}"\n        )\n\n    orphan_services = [\n        service for service in SERVICES\n        if state["services"][service]["runsv_count"] == 1\n    ]\n    old_pids = [\n        int(state["services"][service]["runsv_pid"])\n        for service in orphan_services\n    ]\n    for service in orphan_services:\n        _drain_one_pid1_orphan(\n            root, service, sv, timeout, table_fn, sv_fn\n        )\n\n    if not wait_fn(lambda: _orphan_forest_drained(root, table_fn), timeout):\n        active = _active_required_runsv(table_fn)\n        raise WatchdogError(\n            "orphan_tree_drain_timeout:"\n            f"active={','.join(active)}"\n        )\n    return old_pids\n'''
    TARGET.write_text(text[:start] + replacement + text[end:], encoding='utf-8')
    print('PACKAGE7_COMPLEXITY_PATCH=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
