#!/usr/bin/env python3
"""Transactional BotA observability hardening deployment for Android/Termux.

This installer deploys only the reviewed runtime files from the pinned source
commit. It never resets/cleans/checks out the phone working tree, never uses
broad process matching, and never stops an in-flight watcher cycle.

Deployment barrier:
1. stage exact bytes from the pinned Git commit and validate them;
2. prove several consecutive healthy control-plane samples using the staged
   checker;
3. wait for bota-watcher's supervised wrapper to be in its sleep-only idle
   phase;
4. SIGSTOP the exact wrapper after PID/start-time/parent corroboration;
5. terminate only the corroborated sleep child and prove no descendants remain;
6. atomically replace the reviewed files with rollback armed before file #1;
7. verify hashes/syntax while the old wrapper remains frozen;
8. SIGTERM + SIGCONT the exact frozen wrapper so runit starts a fresh wrapper;
9. prove several consecutive healthy post-deployment topology samples;
10. when possible, validate one new natural watcher cycle separately.

Automatic rollback is performed for failures before a replacement wrapper is
confirmed live. After a replacement wrapper is live, post-deployment market or
provider validation never performs an unsafe mid-cycle rollback; the exact
rollback artifact is retained for a later bounded rollback operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

RUNTIME_COMMIT = "73415776bb1acf6c835236fd23e559d07f274e12"
RUNTIME_FILES = (
    "tools/control_plane_status.py",
    "tools/run_signal_watcher_with_ledger.sh",
    "tools/supabase_publish.py",
    "tools/telegram_delivery.py",
    "tools/telegram_send.sh",
    "tools/watcher_cycle_ledger.py",
    "tools/watcher_persistence_gate.py",
)
REQUIRED_DECISIONS = ("EURUSD:M15", "GBPUSD:M15", "USDJPY:M15")
UNHEALTHY_DECISION_OUTCOMES = {
    "no_terminal_outcome",
    "parse_error",
    "telegram_unknown_outcome",
    "telegram_sent_local_reconcile_failed",
}
LIVE_TERMINAL_OK = {
    "EVALUATED_REJECTED",
    "EVALUATED_ACCEPTED",
    "DEDUP_SUPPRESSED_DELIVERY",
    "DELIVERY_ATTEMPTED",
}
EXTERNAL_OR_ENV_TERMINALS = {
    "MARKET_CLOSED",
    "CLOCK_GATE_FAILED",
    "DATA_FETCH_FAILED",
    "DATA_STALE",
}


class DeployError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcIdentity:
    pid: int
    ppid: int
    starttime: int
    state: str
    comm: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class BackupEntry:
    path: str
    existed: bool
    mode: int | None
    sha256: str | None


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    text: bool = True,
    timeout: float | None = 30,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=text,
        capture_output=capture,
        check=False,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() if text and result.stderr else ""
        raise DeployError(f"command_failed:{Path(args[0]).name}:rc={result.returncode}:{stderr[:300]}")
    return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.deploy-", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        fsync_dir(path.parent)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def git_has_commit(root: Path, commit: str) -> bool:
    result = run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root, check=False)
    return result.returncode == 0


def ensure_source_commit(root: Path, commit: str) -> None:
    if git_has_commit(root, commit):
        return
    run(["git", "fetch", "--no-tags", "origin", commit], cwd=root, timeout=90)
    if not git_has_commit(root, commit):
        raise DeployError("source_commit_not_fetched")


def source_blob_sha(root: Path, commit: str, relpath: str) -> str:
    result = run(["git", "rev-parse", f"{commit}:{relpath}"], cwd=root)
    value = result.stdout.strip()
    if len(value) != 40:
        raise DeployError(f"invalid_source_blob:{relpath}")
    return value


def source_bytes(root: Path, commit: str, relpath: str) -> bytes:
    result = run(
        ["git", "show", f"{commit}:{relpath}"],
        cwd=root,
        text=False,
        timeout=30,
    )
    data = result.stdout
    if git_blob_sha(data) != source_blob_sha(root, commit, relpath):
        raise DeployError(f"source_blob_mismatch:{relpath}")
    return data


def stage_sources(root: Path, commit: str, stage: Path) -> dict[str, str]:
    stage.mkdir(parents=True, exist_ok=True)
    expected: dict[str, str] = {}
    for relpath in RUNTIME_FILES:
        data = source_bytes(root, commit, relpath)
        target = stage / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        expected[relpath] = git_blob_sha(data)
    return expected


def validate_staged_sources(stage: Path) -> None:
    python_files = [str(stage / p) for p in RUNTIME_FILES if p.endswith(".py")]
    shell_files = [str(stage / p) for p in RUNTIME_FILES if p.endswith(".sh")]
    if python_files:
        run([sys.executable, "-m", "py_compile", *python_files], timeout=30)
    for path in shell_files:
        run(["bash", "-n", path], timeout=15)


def parse_proc_stat(raw: str, pid: int, argv: tuple[str, ...]) -> ProcIdentity:
    left = raw.find("(")
    right = raw.rfind(")")
    if left < 0 or right <= left:
        raise ValueError("stat_parse")
    comm = raw[left + 1 : right]
    fields = raw[right + 2 :].split()
    if len(fields) <= 19:
        raise ValueError("stat_fields")
    return ProcIdentity(
        pid=pid,
        ppid=int(fields[1]),
        starttime=int(fields[19]),
        state=fields[0],
        comm=comm,
        argv=argv,
    )


def proc_table(proc_root: Path = Path("/proc")) -> dict[int, ProcIdentity]:
    table: dict[int, ProcIdentity] = {}
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            raw = (entry / "stat").read_text(encoding="utf-8", errors="replace")
            argv = tuple(
                part.decode("utf-8", "replace")
                for part in (entry / "cmdline").read_bytes().split(b"\0")
                if part
            )
            table[pid] = parse_proc_stat(raw, pid, argv)
        except (OSError, ValueError):
            continue
    return table


def proc_basename(proc: ProcIdentity) -> str:
    return Path(proc.argv[0]).name if proc.argv else Path(proc.comm).name


def same_process(expected: ProcIdentity, actual: ProcIdentity | None) -> bool:
    return bool(
        actual
        and actual.pid == expected.pid
        and actual.starttime == expected.starttime
        and actual.ppid == expected.ppid
        and actual.comm == expected.comm
    )


def descendants(table: dict[int, ProcIdentity], root_pid: int) -> list[ProcIdentity]:
    children: dict[int, list[int]] = {}
    for pid, proc in table.items():
        children.setdefault(proc.ppid, []).append(pid)
    found: list[ProcIdentity] = []
    pending = list(children.get(root_pid, []))
    while pending:
        pid = pending.pop()
        proc = table.get(pid)
        if proc is None:
            continue
        found.append(proc)
        pending.extend(children.get(pid, []))
    return found


def safe_idle_sleep(wrapper: ProcIdentity, table: dict[int, ProcIdentity]) -> ProcIdentity | None:
    owned = descendants(table, wrapper.pid)
    if len(owned) != 1:
        return None
    child = owned[0]
    if child.ppid != wrapper.pid:
        return None
    if child.state == "Z" or proc_basename(child) != "sleep":
        return None
    return child


def wait_for(predicate, timeout: float, interval: float = 0.2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return None


def read_pid(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        pid = int(raw)
    except (OSError, ValueError) as exc:
        raise DeployError(f"pidfile_unreadable:{path}:{type(exc).__name__}") from exc
    if pid <= 0:
        raise DeployError(f"pidfile_invalid:{path}")
    return pid


def control_snapshot(checker: Path, prefix: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PREFIX"] = str(prefix)
    result = subprocess.run(
        [sys.executable, str(checker)],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
        env=env,
    )
    try:
        value = json.loads(result.stdout)
    except ValueError as exc:
        raise DeployError(f"control_snapshot_invalid_json:rc={result.returncode}") from exc
    if not isinstance(value, dict):
        raise DeployError("control_snapshot_not_object")
    return value


def require_healthy_snapshot(snapshot: dict[str, Any]) -> None:
    required = {
        "healthy": True,
        "manager_count": 1,
        "owned": 7,
        "required": 7,
        "running": 7,
        "orphaned": 0,
        "duplicate_service_rows": 0,
    }
    for key, expected in required.items():
        if snapshot.get(key) != expected:
            raise DeployError(f"control_plane_not_healthy:{key}={snapshot.get(key)!r}")
    if snapshot.get("zombie_runsv"):
        raise DeployError("control_plane_zombie_runsv")
    if len(snapshot.get("live_crond") or []) != 1:
        raise DeployError("control_plane_live_crond_not_one")


def require_stable_control_plane(checker: Path, prefix: Path, samples: int = 3) -> list[dict[str, Any]]:
    results = []
    manager_pid = None
    watcher_runsv_pid = None
    for index in range(samples):
        snap = control_snapshot(checker, prefix)
        require_healthy_snapshot(snap)
        current_manager = snap.get("manager_pid")
        current_runsv = ((snap.get("services") or {}).get("bota-watcher") or {}).get("runsv_pid")
        if not isinstance(current_manager, int) or not isinstance(current_runsv, int):
            raise DeployError("control_plane_missing_manager_or_watcher_runsv")
        if manager_pid is None:
            manager_pid = current_manager
            watcher_runsv_pid = current_runsv
        elif current_manager != manager_pid or current_runsv != watcher_runsv_pid:
            raise DeployError("control_plane_identity_changed_between_samples")
        results.append(snap)
        if index + 1 < samples:
            time.sleep(1)
    return results


def wait_for_idle_wrapper(service_root: Path, watcher_runsv_pid: int, timeout: float) -> tuple[ProcIdentity, ProcIdentity]:
    pidfile = service_root / "bota-watcher" / "supervise" / "pid"

    def sample():
        try:
            wrapper_pid = read_pid(pidfile)
        except DeployError:
            return None
        table = proc_table()
        wrapper = table.get(wrapper_pid)
        if wrapper is None or wrapper.state == "Z" or wrapper.ppid != watcher_runsv_pid:
            return None
        sleep_child = safe_idle_sleep(wrapper, table)
        return (wrapper, sleep_child) if sleep_child else None

    result = wait_for(sample, timeout, interval=1)
    if not result:
        raise DeployError("watcher_idle_sleep_not_observed")
    return result


def stop_exact_process(proc: ProcIdentity, sig: int) -> None:
    actual = proc_table().get(proc.pid)
    if not same_process(proc, actual):
        raise DeployError(f"process_identity_changed_before_signal:{proc.pid}")
    os.kill(proc.pid, sig)


def freeze_idle_wrapper(wrapper: ProcIdentity, sleep_child: ProcIdentity) -> ProcIdentity:
    stop_exact_process(wrapper, signal.SIGSTOP)

    def stopped():
        actual = proc_table().get(wrapper.pid)
        return actual if same_process(wrapper, actual) and actual.state in {"T", "t"} else None

    frozen = wait_for(stopped, 5)
    if not frozen:
        raise DeployError("wrapper_did_not_stop")

    table = proc_table()
    current_wrapper = table.get(wrapper.pid)
    if not same_process(wrapper, current_wrapper):
        raise DeployError("wrapper_identity_changed_after_stop")
    owned = descendants(table, wrapper.pid)
    if len(owned) > 1 or any(proc_basename(p) != "sleep" or p.state == "Z" for p in owned):
        raise DeployError("wrapper_not_sleep_only_after_stop")
    if owned:
        current_sleep = owned[0]
        if not same_process(sleep_child, current_sleep):
            raise DeployError("sleep_identity_changed_after_stop")
        stop_exact_process(current_sleep, signal.SIGTERM)
        if not wait_for(lambda: proc_table().get(current_sleep.pid) is None, 10):
            raise DeployError("sleep_descendant_did_not_exit")
    if descendants(proc_table(), wrapper.pid):
        raise DeployError("wrapper_descendants_remain")
    return frozen


def terminate_frozen_wrapper(wrapper: ProcIdentity) -> None:
    actual = proc_table().get(wrapper.pid)
    if not same_process(wrapper, actual) or actual.state not in {"T", "t"}:
        raise DeployError("frozen_wrapper_identity_lost_before_restart")
    os.kill(wrapper.pid, signal.SIGTERM)
    os.kill(wrapper.pid, signal.SIGCONT)
    if not wait_for(lambda: proc_table().get(wrapper.pid) is None, 15):
        raise DeployError("old_wrapper_did_not_exit")


def resume_frozen_wrapper_after_failure(wrapper: ProcIdentity) -> None:
    actual = proc_table().get(wrapper.pid)
    if not same_process(wrapper, actual):
        return
    try:
        os.kill(wrapper.pid, signal.SIGTERM)
        os.kill(wrapper.pid, signal.SIGCONT)
    except ProcessLookupError:
        return


def wait_for_new_wrapper(service_root: Path, old_pid: int, timeout: float) -> ProcIdentity:
    pidfile = service_root / "bota-watcher" / "supervise" / "pid"

    def sample():
        try:
            pid = read_pid(pidfile)
        except DeployError:
            return None
        if pid == old_pid:
            return None
        proc = proc_table().get(pid)
        return proc if proc and proc.state != "Z" else None

    result = wait_for(sample, timeout, interval=0.5)
    if not result:
        raise DeployError("replacement_wrapper_not_live")
    return result


def backup_current(root: Path, backup_dir: Path) -> list[BackupEntry]:
    entries: list[BackupEntry] = []
    files_dir = backup_dir / "files"
    for relpath in RUNTIME_FILES:
        source = root / relpath
        if source.exists():
            if not source.is_file():
                raise DeployError(f"runtime_target_not_file:{relpath}")
            mode = stat.S_IMODE(source.stat().st_mode)
            destination = files_dir / relpath
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            entries.append(BackupEntry(relpath, True, mode, sha256_file(source)))
        else:
            entries.append(BackupEntry(relpath, False, None, None))
    payload = [entry.__dict__ for entry in entries]
    durable_write(backup_dir / "backup_manifest.json", (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode(), 0o600)
    return entries


def load_backup_manifest(backup_dir: Path) -> list[BackupEntry]:
    try:
        raw = json.loads((backup_dir / "backup_manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DeployError(f"backup_manifest_invalid:{type(exc).__name__}") from exc
    if not isinstance(raw, list):
        raise DeployError("backup_manifest_not_list")
    entries = []
    for item in raw:
        if not isinstance(item, dict):
            raise DeployError("backup_manifest_entry_invalid")
        entries.append(BackupEntry(**item))
    return entries


def target_mode(root: Path, relpath: str) -> int:
    target = root / relpath
    if relpath == "tools/telegram_send.sh":
        return 0o700
    if target.exists():
        return stat.S_IMODE(target.stat().st_mode)
    return 0o644


def install_files(root: Path, stage: Path, expected_blobs: dict[str, str], *, fail_after: int = 0) -> None:
    for index, relpath in enumerate(RUNTIME_FILES, start=1):
        data = (stage / relpath).read_bytes()
        if git_blob_sha(data) != expected_blobs[relpath]:
            raise DeployError(f"stage_hash_changed:{relpath}")
        durable_write(root / relpath, data, target_mode(root, relpath))
        if git_blob_sha((root / relpath).read_bytes()) != expected_blobs[relpath]:
            raise DeployError(f"installed_hash_mismatch:{relpath}")
        if fail_after and index == fail_after:
            raise DeployError(f"fault_injected_after_file:{index}")


def rollback_files(root: Path, backup_dir: Path, entries: Iterable[BackupEntry] | None = None) -> None:
    manifest = list(entries) if entries is not None else load_backup_manifest(backup_dir)
    for entry in manifest:
        target = root / entry.path
        if entry.existed:
            backup = backup_dir / "files" / entry.path
            if not backup.is_file():
                raise DeployError(f"rollback_backup_missing:{entry.path}")
            data = backup.read_bytes()
            if sha256_bytes(data) != entry.sha256:
                raise DeployError(f"rollback_backup_hash_mismatch:{entry.path}")
            durable_write(target, data, entry.mode or 0o644)
            if sha256_file(target) != entry.sha256:
                raise DeployError(f"rollback_restore_hash_mismatch:{entry.path}")
        else:
            try:
                target.unlink()
                fsync_dir(target.parent)
            except FileNotFoundError:
                pass


def validate_installed(root: Path, expected_blobs: dict[str, str]) -> None:
    for relpath, expected in expected_blobs.items():
        path = root / relpath
        if not path.is_file() or git_blob_sha(path.read_bytes()) != expected:
            raise DeployError(f"postinstall_hash_mismatch:{relpath}")
    if not os.access(root / "tools" / "telegram_send.sh", os.X_OK):
        raise DeployError("telegram_sender_not_executable")
    python_files = [str(root / p) for p in RUNTIME_FILES if p.endswith(".py")]
    for path in python_files:
        run([sys.executable, "-m", "py_compile", path], timeout=20)
    for relpath in RUNTIME_FILES:
        if relpath.endswith(".sh"):
            run(["bash", "-n", str(root / relpath)], timeout=15)


def pipeline_cycle_id(state: dict[str, Any]) -> str:
    return str((state.get("last_terminal_outcome") or {}).get("cycle_id") or "")


def read_pipeline_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def evaluate_live_cycle(state: dict[str, Any], previous_cycle: str) -> tuple[str, list[str]]:
    last = state.get("last_terminal_outcome") or {}
    cycle_id = str(last.get("cycle_id") or "")
    terminal = str(last.get("terminal_outcome") or "")
    reasons: list[str] = []
    if not cycle_id or cycle_id == previous_cycle:
        return "WAIT", ["no_new_cycle"]
    if terminal == "MARKET_CLOSED":
        return "PENDING_MARKET_CLOSED", []
    if terminal in EXTERNAL_OR_ENV_TERMINALS:
        return "EXTERNAL_OR_ENV_FAILURE", [terminal]
    if terminal not in LIVE_TERMINAL_OK:
        return "FAILED", [f"unexpected_terminal:{terminal}"]

    decisions = state.get("decisions") or {}
    for key in REQUIRED_DECISIONS:
        row = decisions.get(key)
        if not isinstance(row, dict):
            reasons.append(f"decision_missing:{key}")
            continue
        if str(row.get("cycle_id") or "") != cycle_id:
            reasons.append(f"decision_cycle_mismatch:{key}")
        if row.get("status") != "completed":
            reasons.append(f"decision_not_completed:{key}")
        if str(row.get("outcome") or "") in UNHEALTHY_DECISION_OUTCOMES:
            reasons.append(f"decision_unhealthy:{key}:{row.get('outcome')}")
        outcome = str(row.get("outcome") or "")
        if outcome not in {"raw_cache_invalid", "candle_stale", "pause_guard", "news_gate", "calendar_gate"}:
            if row.get("alerts_csv_persisted") is not True:
                reasons.append(f"decision_not_persisted:{key}")
        if row.get("telegram_result") == "unknown_outcome":
            reasons.append(f"telegram_unknown:{key}")
    return ("PASS", []) if not reasons else ("FAILED", reasons)


def wait_live_acceptance(path: Path, previous_cycle: str, timeout: float) -> tuple[str, list[str], str]:
    deadline = time.monotonic() + timeout
    last_status = "WAIT"
    last_reasons: list[str] = []
    last_cycle = ""
    while time.monotonic() < deadline:
        state = read_pipeline_state(path)
        if state:
            status, reasons = evaluate_live_cycle(state, previous_cycle)
            last_cycle = pipeline_cycle_id(state)
            if status != "WAIT":
                return status, reasons, last_cycle
            last_status, last_reasons = status, reasons
        time.sleep(2)
    return "TIMEOUT", last_reasons or [last_status], last_cycle


def snapshot_tree(root: Path, exclude_prefixes: tuple[str, ...] = ()) -> dict[str, tuple[str, int]]:
    result: dict[str, tuple[str, int]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in exclude_prefixes):
            continue
        result[rel] = (sha256_file(path), stat.S_IMODE(path.stat().st_mode))
    return result


def write_deploy_metadata(backup_dir: Path, payload: dict[str, Any]) -> None:
    durable_write(
        backup_dir / "deployment.json",
        (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode(),
        0o600,
    )


def deploy(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr")).resolve()
    service_root = prefix / "var" / "service"
    if not (root / ".git").exists():
        raise DeployError(f"not_git_repo:{root}")

    ensure_source_commit(root, RUNTIME_COMMIT)
    deployment_id = f"observability-{uuid.uuid4().hex}"
    backup_dir = root / "state" / "deployments" / deployment_id
    stage = backup_dir / "stage"
    backup_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__).resolve(), backup_dir / "phone_deploy_observability.py")

    expected_blobs = stage_sources(root, RUNTIME_COMMIT, stage)
    validate_staged_sources(stage)
    backup_entries = backup_current(root, backup_dir)

    pre_pipeline = read_pipeline_state(root / "state" / "pipeline_progress.json") or {}
    pre_cycle = pipeline_cycle_id(pre_pipeline)
    staged_checker = stage / "tools" / "control_plane_status.py"
    pre_samples = require_stable_control_plane(staged_checker, prefix, samples=args.stability_samples)
    watcher_runsv_pid = pre_samples[-1]["services"]["bota-watcher"]["runsv_pid"]

    write_deploy_metadata(backup_dir, {
        "schema_version": "1.0",
        "deployment_id": deployment_id,
        "runtime_commit": RUNTIME_COMMIT,
        "runtime_files": list(RUNTIME_FILES),
        "expected_blobs": expected_blobs,
        "pre_cycle": pre_cycle,
        "status": "PREPARED",
    })

    wrapper, sleep_child = wait_for_idle_wrapper(service_root, watcher_runsv_pid, args.idle_timeout)
    frozen = False
    mutated = False
    replacement_live = False
    try:
        freeze_idle_wrapper(wrapper, sleep_child)
        frozen = True
        # Rollback is armed before file #1 is replaced.
        mutated = True
        install_files(root, stage, expected_blobs, fail_after=args.inject_fail_after)
        validate_installed(root, expected_blobs)
        if args.inject_restart_failure:
            raise DeployError("fault_injected_before_wrapper_restart")
        terminate_frozen_wrapper(wrapper)
        frozen = False
        new_wrapper = wait_for_new_wrapper(service_root, wrapper.pid, args.restart_timeout)
        replacement_live = True
    except Exception:
        if mutated and not replacement_live:
            rollback_files(root, backup_dir, backup_entries)
        if frozen:
            resume_frozen_wrapper_after_failure(wrapper)
            frozen = False
        raise

    # Once a fresh wrapper is live, do not perform a mid-cycle auto-rollback.
    # Retain the exact rollback artifact and report post-deploy validation truth.
    post_samples = require_stable_control_plane(root / "tools" / "control_plane_status.py", prefix, samples=args.stability_samples)
    live_status, live_reasons, live_cycle = wait_live_acceptance(
        root / "state" / "pipeline_progress.json",
        pre_cycle,
        args.live_timeout,
    )

    status = "DEPLOYED"
    if live_status == "PASS":
        status = "DEPLOYED_LIVE_ACCEPTANCE_PASS"
    elif live_status == "PENDING_MARKET_CLOSED":
        status = "DEPLOYED_LIVE_ACCEPTANCE_PENDING_MARKET_CLOSED"
    else:
        status = "DEPLOYED_LIVE_ACCEPTANCE_NOT_PASSED"

    write_deploy_metadata(backup_dir, {
        "schema_version": "1.0",
        "deployment_id": deployment_id,
        "runtime_commit": RUNTIME_COMMIT,
        "runtime_files": list(RUNTIME_FILES),
        "expected_blobs": expected_blobs,
        "pre_cycle": pre_cycle,
        "post_cycle": live_cycle,
        "old_wrapper_pid": wrapper.pid,
        "new_wrapper_pid": new_wrapper.pid,
        "post_control_samples": len(post_samples),
        "live_acceptance": live_status,
        "live_reasons": live_reasons,
        "status": status,
    })

    print(f"DEPLOYMENT_ID={deployment_id}")
    print(f"RUNTIME_COMMIT={RUNTIME_COMMIT}")
    print(f"BACKUP_DIR={backup_dir}")
    print(f"OLD_WRAPPER_PID={wrapper.pid}")
    print(f"NEW_WRAPPER_PID={new_wrapper.pid}")
    print(f"POST_CONTROL_SAMPLES={len(post_samples)}")
    print(f"LIVE_ACCEPTANCE={live_status}")
    if live_reasons:
        print("LIVE_REASONS=" + "|".join(live_reasons))
    print(f"STATUS={status}")
    print(f"ROLLBACK_COMMAND=python3 {backup_dir / 'phone_deploy_observability.py'} --rollback {backup_dir} --root {root}")
    return 0 if live_status in {"PASS", "PENDING_MARKET_CLOSED"} else 4


def rollback(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    backup_dir = Path(args.rollback).expanduser().resolve()
    metadata = json.loads((backup_dir / "deployment.json").read_text(encoding="utf-8"))
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr")).resolve()
    service_root = prefix / "var" / "service"
    checker = root / "tools" / "control_plane_status.py"
    samples = require_stable_control_plane(checker, prefix, samples=args.stability_samples)
    watcher_runsv_pid = samples[-1]["services"]["bota-watcher"]["runsv_pid"]
    wrapper, sleep_child = wait_for_idle_wrapper(service_root, watcher_runsv_pid, args.idle_timeout)
    freeze_idle_wrapper(wrapper, sleep_child)
    try:
        rollback_files(root, backup_dir)
        terminate_frozen_wrapper(wrapper)
    except Exception:
        resume_frozen_wrapper_after_failure(wrapper)
        raise
    new_wrapper = wait_for_new_wrapper(service_root, wrapper.pid, args.restart_timeout)
    require_stable_control_plane(root / "tools" / "control_plane_status.py", prefix, samples=args.stability_samples)
    metadata["status"] = "ROLLED_BACK"
    metadata["rollback_old_wrapper_pid"] = wrapper.pid
    metadata["rollback_new_wrapper_pid"] = new_wrapper.pid
    write_deploy_metadata(backup_dir, metadata)
    print(f"STATUS=ROLLED_BACK")
    print(f"BACKUP_DIR={backup_dir}")
    print(f"NEW_WRAPPER_PID={new_wrapper.pid}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path.home() / "BotA"))
    parser.add_argument("--rollback", default="")
    parser.add_argument("--stability-samples", type=int, default=3)
    parser.add_argument("--idle-timeout", type=float, default=420)
    parser.add_argument("--restart-timeout", type=float, default=30)
    parser.add_argument("--live-timeout", type=float, default=480)
    parser.add_argument("--inject-fail-after", type=int, default=int(os.environ.get("BOTA_DEPLOY_INJECT_FAIL_AFTER", "0") or "0"))
    parser.add_argument("--inject-restart-failure", action="store_true")
    args = parser.parse_args()
    if args.stability_samples < 2:
        parser.error("--stability-samples must be >=2")
    if args.inject_fail_after < 0 or args.inject_fail_after > len(RUNTIME_FILES):
        parser.error("--inject-fail-after out of range")
    return args


def main() -> int:
    args = parse_args()
    try:
        if args.rollback:
            return rollback(args)
        return deploy(args)
    except DeployError as exc:
        print(f"STATUS=FAILED", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("STATUS=INTERRUPTED", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
