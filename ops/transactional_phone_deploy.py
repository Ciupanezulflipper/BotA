#!/data/data/com.termux/files/usr/bin/python3
"""Transactional installer for the pinned BotA runtime delta.

Two independent invariants gate a green runtime generation report:

* MANIFEST_PARITY  - every file in MANIFEST is resolvable from the pinned
  RELEASE and its staged bytes hash to the pinned blob.
* DEPENDENCY_CLOSURE - every local runtime dependency reachable from those
  manifest files is either included in the deployed payload or already
  present on the target with content matching the pinned RELEASE blob.

Manifest parity alone must never be reported as full runtime parity; the
Package-6 (2026-08-16) incident where a 12-file manifest silently omitted
watcher_persistence_gate.py and telegram_delivery.py is the reason this
distinction exists.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RELEASE = "f36836315526fd2be826e8abff1c333004b64b0c"
MANIFEST = (
    "tools/chart_generator.py",
    "tools/chart_generator_core.py",
    "tools/run_signal_watcher_with_ledger.sh",
    "tools/signal_watcher_core.sh",
    "tools/signal_watcher_pro.sh",
    "tools/supabase_publish.py",
    "tools/telegram_delivery_boundary.py",
    "tools/telegram_send.sh",
    "tools/telegram_send_guard.py",
    "tools/watcher_cycle_contract.py",
    "tools/watcher_evidence_retention.py",
    "tools/watcher_pending_delivery_recovery.py",
)
SERVICE = "bota-watcher"
DEPLOYMENT_METADATA = "deployment.json"
GENERATION_MARKER = "runtime_deploy_in_progress.json"
# Git modes are authoritative except telegram_send.sh: the reviewed watcher
# boundary explicitly requires that transport to be executable at runtime.
EXECUTABLE = {
    "tools/run_signal_watcher_with_ledger.sh",
    "tools/signal_watcher_pro.sh",
    "tools/telegram_send.sh",
}
COMMAND_TIMEOUT_SECONDS = 30.0
SERVICE_TIMEOUT_SECONDS = 15.0


class Abort(RuntimeError):
    pass


def emit(message: str) -> None:
    print(message, flush=True)


def run(argv: list[str], cwd: Path, *, check: bool = True, capture: bool = True,
        timeout: float = COMMAND_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str]:
    # argv is always a list, shell=False is retained, and production executable
    # names are fixed by this module rather than accepted from CLI input.
    if os.environ.get("BOTA_ALLOW_NON_TERMUX") == "1":
        timeout = float(os.environ.get("BOTA_TEST_COMMAND_TIMEOUT_SECONDS", timeout))
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=capture, check=False,
                                timeout=timeout)  # NOSONAR
    except subprocess.TimeoutExpired as exc:
        identity = Path(argv[0]).name
        raise Abort(f"COMMAND_TIMEOUT:{identity}") from exc
    if check and result.returncode:
        raise Abort(f"COMMAND_FAILED:{argv[0]}:rc={result.returncode}")
    return result


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def git(root: Path, *args: str) -> str:
    return run(["git", *args], root).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_copy(source: Path, target: Path, mode: int, label: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.{label}.", dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temp_name)
        os.chmod(temp_name, mode)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def service(root: Path, action: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = os.environ.get("BOTA_SV_COMMAND", "sv") if os.environ.get("BOTA_ALLOW_NON_TERMUX") == "1" else "sv"
    return run([command, action, SERVICE], root, check=check, timeout=SERVICE_TIMEOUT_SECONDS)


def service_running(root: Path) -> bool:
    result = service(root, "status", check=False)
    return result.returncode == 0 and result.stdout.lstrip().startswith("run:")


def watcher_instance_count(root: Path) -> int:
    override = os.environ.get("BOTA_TEST_WATCHER_INSTANCE_COUNT")
    if override is not None:
        return int(override)
    result = run(["pgrep", "-f", "^runsv bota-watcher$"], root, check=False)
    return len([line for line in result.stdout.splitlines() if line.strip()])


def mutable_sentinels(root: Path) -> list[str]:
    candidates = [".env", ".env.runtime", "credentials", "secrets", "logs", "state", "cache", "alerts.csv"]
    found = {name for name in candidates if (root / name).exists()}
    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        for path in root.rglob(pattern):
            relative = path.relative_to(root)
            if relative.parts[0] not in {".git", "audits"}:
                found.add(str(relative))
    return sorted(found)


def journal_paths(root: Path) -> tuple[Path, Path]:
    state = root / "state" / "transactional_phone_deploy"
    return state, state / "active.json"


def validate_root(root: Path) -> None:
    if not root.is_absolute() or root.name != "BotA":
        raise Abort("INVALID_BOTA_ROOT")
    if not (root / ".git").exists():
        raise Abort("BOTA_ROOT_NOT_GIT_CHECKOUT")
    if os.environ.get("BOTA_ALLOW_NON_TERMUX") != "1":
        prefix = os.environ.get("PREFIX", "")
        if not prefix.startswith("/data/data/com.termux/files/usr"):
            raise Abort("NOT_TERMUX_ENVIRONMENT")


def required_configuration(root: Path) -> None:  # NOSONAR - explicit secret-safe parser is clearer inline
    configs = [root / ".env", root / ".env.runtime"]
    if not any(p.is_file() for p in configs):
        raise Abort("RUNTIME_CONFIGURATION_MISSING")
    names: set[str] = set()
    for path in configs:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                if value.strip().strip("'\""):
                    names.add(key.strip())
    token = bool({"TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN"} & names)
    if not token or "TELEGRAM_CHAT_ID" not in names or "SUPABASE_SERVICE_KEY" not in names:
        raise Abort("REQUIRED_CREDENTIALS_MISSING")


def ensure_no_incomplete(root: Path) -> None:
    _, active = journal_paths(root)
    if not active.exists():
        return
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        if data.get("schema") != 1:
            raise ValueError("journal schema")
        phase = data["phase"]
        source = data["source"]
        audit = Path(data["audit"]).resolve()
    except Exception as exc:
        raise Abort("INCOMPLETE_JOURNAL_AMBIGUOUS") from exc
    allowed = (root / "audits").resolve()
    if allowed not in audit.parents:
        raise Abort("INCOMPLETE_JOURNAL_AMBIGUOUS")
    if phase == "complete":
        if source != RELEASE or not audit.is_dir():
            raise Abort("INCOMPLETE_JOURNAL_AMBIGUOUS")
        for record_name in (DEPLOYMENT_METADATA, "provenance.json"):
            record = audit / record_name
            if record.is_file():
                try:
                    record_data = json.loads(record.read_text(encoding="utf-8"))
                except Exception as exc:
                    raise Abort("INCOMPLETE_JOURNAL_AMBIGUOUS") from exc
                if record_data.get("source") != RELEASE:
                    raise Abort("INCOMPLETE_JOURNAL_AMBIGUOUS")
        active.unlink()
        return
    if phase == "rollback_complete":
        raise Abort("COMPLETED_ROLLBACK_JOURNAL_REQUIRES_REVIEW")
    raise Abort(f"INCOMPLETE_JOURNAL_DETECTED:{phase}:MANUAL_ROLLBACK_REQUIRED")


def validate_preflight_environment(root: Path, source: str) -> None:
    validate_root(root)
    if source != RELEASE:
        raise Abort("SOURCE_COMMIT_NOT_ALLOWED")
    if git(root, "rev-parse", f"{source}^{{commit}}") != RELEASE:
        raise Abort("SOURCE_COMMIT_MISSING_OR_DIFFERENT")
    utilities = ("bash", "git", "python3") if os.environ.get("BOTA_ALLOW_NON_TERMUX") == "1" else ("bash", "git", "python3", "pgrep")
    for utility in utilities:
        if shutil.which(utility) is None:
            raise Abort(f"UTILITY_MISSING:{utility}")
    command = os.environ.get("BOTA_SV_COMMAND", "sv") if os.environ.get("BOTA_ALLOW_NON_TERMUX") == "1" else "sv"
    if shutil.which(command) is None and not Path(command).is_file():
        raise Abort("SERVICE_CONTROL_MISSING")
    required_configuration(root)
    ensure_no_incomplete(root)
    runit = root / "ops" / "runit" / "bota-watcher.run"
    if not runit.is_file() or "tools/watcher_gated_cycle.sh" not in runit.read_text(encoding="utf-8"):
        raise Abort("CANONICAL_WATCHER_RUNIT_PATH_INVALID")


def resolve_source_objects(root: Path, source: str) -> dict[str, tuple[str, str]]:
    objects: dict[str, tuple[str, str]] = {}
    for path in MANIFEST:
        if os.environ.get("BOTA_TEST_MISSING_SOURCE_PATH") == path:
            raise Abort(f"SOURCE_PATH_MISSING:{path}")
        mode_type_name = git(root, "ls-tree", source, "--", path).split()
        if len(mode_type_name) < 4 or mode_type_name[1] != "blob":
            raise Abort(f"SOURCE_PATH_MISSING:{path}")
        objects[path] = (mode_type_name[0], mode_type_name[2])
        parent = (root / path).parent
        probe = parent
        while not probe.exists() and probe != root:
            probe = probe.parent
        if not os.access(probe, os.W_OK):
            raise Abort(f"TARGET_NOT_WRITABLE:{path}")
    return objects


def validate_deployment_space(root: Path, objects: dict[str, tuple[str, str]]) -> None:
    if not os.access(root, os.W_OK):
        raise Abort("AUDIT_LOCATION_NOT_WRITABLE")
    required_bytes = sum((root / path).stat().st_size for path in MANIFEST if (root / path).is_file())
    required_bytes += sum(int(git(root, "cat-file", "-s", blob)) for _, blob in objects.values())
    if shutil.disk_usage(root).free < max(required_bytes * 2, 16 * 1024 * 1024):
        raise Abort("INSUFFICIENT_DEPLOYMENT_SPACE")


# Bounded, explainable dependency parser.
#
# The parser looks only for two well-scoped signals in the pinned RELEASE
# blobs of the MANIFEST files:
#
#   1. Shell references of the form ${TOOLS}/name.(py|sh) or
#      ${SCRIPT_DIR}/name.(py|sh) (with or without braces). These are how the
#      BotA watcher shell layer invokes its Python and shell helpers.
#   2. Python "import name" / "from name import ..." statements where the
#      module resolves to tools/<name>.py in the same RELEASE tree. Stdlib
#      and third-party imports are ignored by construction.
#
# The Python signal is scanned in both .py files (via ast) and in .sh files
# (via a bounded regex), because the BotA shell scripts embed python3
# heredocs whose "from news_filter_real import ..." lines are real runtime
# dependencies. Only names that resolve against the release's tools/
# directory are ever counted, so spurious matches on unrelated text do not
# produce ghost dependencies.
_SHELL_TOOLS_REF = re.compile(
    r"\$\{?(?:TOOLS|SCRIPT_DIR)\}?/(?P<name>[A-Za-z0-9_.-]+\.(?:py|sh))\b"
)
_PY_IMPORT_LINE = re.compile(
    r"^\s*(?:from\s+([A-Za-z_][A-Za-z0-9_]*)\s+import|"
    r"import\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s|$|,))",
    re.MULTILINE,
)


def _list_release_python_modules(root: Path, source: str) -> set[str]:
    """Return the set of top-level module names present as tools/<name>.py at RELEASE."""
    result = run(["git", "ls-tree", "-r", "--name-only", source, "--", "tools/"], root)
    modules: set[str] = set()
    for line in result.stdout.splitlines():
        name = line.strip()
        if not name.endswith(".py"):
            continue
        # Only top-level tools/<name>.py (no nested packages).
        rest = name[len("tools/"):]
        if "/" in rest:
            continue
        modules.add(rest[: -len(".py")])
    return modules


def _release_blob_id(root: Path, source: str, path: str) -> str | None:
    result = run(["git", "ls-tree", source, "--", path], root, check=False)
    if result.returncode != 0:
        return None
    parts = result.stdout.split()
    if len(parts) < 4 or parts[1] != "blob":
        return None
    return parts[2]


def _release_blob_text(root: Path, source: str, path: str) -> str:
    return run(["git", "cat-file", "-p", f"{source}:{path}"], root).stdout


def _scan_shell_tool_refs(text: str) -> set[str]:
    refs: set[str] = set()
    for match in _SHELL_TOOLS_REF.finditer(text):
        name = match.group("name")
        if "/" in name or ".." in name:
            continue
        refs.add(f"tools/{name}")
    return refs


def _scan_python_local_imports(text: str, release_modules: set[str]) -> set[str]:
    refs: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # Fall back to the same bounded regex used for embedded heredocs.
        for match in _PY_IMPORT_LINE.finditer(text):
            name = match.group(1) or match.group(2)
            if name in release_modules:
                refs.add(f"tools/{name}.py")
        return refs
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in release_modules:
                    refs.add(f"tools/{top}.py")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                top = node.module.split(".")[0]
                if top in release_modules:
                    refs.add(f"tools/{top}.py")
        elif isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "runpy"
                    and func.attr in ("run_path", "run_module")
                    and node.args):
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    literal = first.value
                    if literal.endswith(".py") and "/" not in literal:
                        module = literal[: -len(".py")]
                        if module in release_modules:
                            refs.add(f"tools/{module}.py")
    return refs


def _scan_shell_embedded_python_imports(text: str, release_modules: set[str]) -> set[str]:
    refs: set[str] = set()
    for match in _PY_IMPORT_LINE.finditer(text):
        name = match.group(1) or match.group(2)
        if name in release_modules:
            refs.add(f"tools/{name}.py")
    return refs


def _scan_local_refs(path: str, text: str, modules: set[str]) -> set[str]:
    """Return local (tools/) dependency refs discoverable from `text`.

    Shell scripts and .py files use the same scanners, because both may embed
    the other (shell heredocs contain python; python spawns subprocesses that
    reference ${TOOLS}/foo). The scanners themselves are bounded and only
    accept names that resolve against the pinned RELEASE tools/ tree.
    """
    if path.endswith(".sh"):
        return _scan_shell_tool_refs(text) | _scan_shell_embedded_python_imports(text, modules)
    return _scan_shell_tool_refs(text) | _scan_python_local_imports(text, modules)


def _transitive_closure(
    entries: set[str],
    modules: set[str],
    resolve_text,
) -> set[str]:
    """Return the transitive fixed-point closure of `entries` under `resolve_text`.

    resolve_text(path) must return the text content of the pinned RELEASE blob
    at that path, or None if the path is not resolvable at RELEASE. The scan
    iterates until no new dependency is discovered; unresolvable frontier
    entries are still retained in the closure so the caller can fail closed
    with an explanation. Cycles are handled by the `seen` set.
    """
    seen: set[str] = set()
    frontier: set[str] = set(entries)
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        text = resolve_text(current)
        if text is None:
            continue
        for ref in _scan_local_refs(current, text, modules):
            if ref not in seen:
                frontier.add(ref)
    return seen


def discover_runtime_dependencies(root: Path, source: str) -> set[str]:
    """Return runtime deps transitively reachable from MANIFEST, excluding MANIFEST itself.

    The scan is a true fixed-point closure: every newly discovered local
    dependency is itself scanned for further local dependencies until no new
    dependency is observed. That is what makes the invariant meaningful --
    a MANIFEST -> B -> C chain where C only appears in B (not in MANIFEST)
    is still discovered and gated.
    """
    modules = _list_release_python_modules(root, source)

    def resolve_text(path: str) -> str | None:
        if _release_blob_id(root, source, path) is None:
            return None
        return _release_blob_text(root, source, path)

    manifest_set = set(MANIFEST)
    closure = _transitive_closure(manifest_set, modules, resolve_text)
    return {dep for dep in closure if dep not in manifest_set}


def verify_dependency_closure(root: Path, source: str) -> list[str]:
    """Fail closed unless every discovered runtime dep matches its RELEASE blob.

    Returns the sorted list of dependencies that were verified successfully.
    """
    deps = sorted(discover_runtime_dependencies(root, source))
    for dep in deps:
        expected_blob = _release_blob_id(root, source, dep)
        if expected_blob is None:
            emit("DEPENDENCY_CLOSURE=FAIL")
            emit(f"DEPENDENCY_UNRESOLVABLE_AT_RELEASE={dep}")
            raise Abort(f"DEPENDENCY_UNRESOLVABLE_AT_RELEASE:{dep}")
        target = root / dep
        if not target.is_file():
            emit("DEPENDENCY_CLOSURE=FAIL")
            emit(f"DEPENDENCY_MISSING={dep}")
            raise Abort(f"DEPENDENCY_MISSING:{dep}")
        actual_blob = git(root, "hash-object", str(target))
        if actual_blob != expected_blob:
            emit("DEPENDENCY_CLOSURE=FAIL")
            emit(f"DEPENDENCY_STALE={dep}")
            raise Abort(f"DEPENDENCY_STALE:{dep}")
    emit("DEPENDENCY_CLOSURE=PASS")
    return deps


def preflight(root: Path, source: str) -> dict[str, tuple[str, str]]:
    validate_preflight_environment(root, source)
    objects = resolve_source_objects(root, source)
    emit("MANIFEST_PARITY=PASS")
    verify_dependency_closure(root, source)
    validate_deployment_space(root, objects)
    service(root, "status", check=False)
    return objects


def restore(root: Path, audit: Path, journal: Path | None = None) -> bool:
    state, _ = journal_paths(root)
    marker = state / GENERATION_MARKER
    try:
        meta = json.loads((audit / DEPLOYMENT_METADATA).read_text(encoding="utf-8"))
        atomic_json(marker, {"source": RELEASE, "audit": str(audit), "operation": "rollback"})
        service(root, "down")
        for item in reversed(meta["files"]):
            item_path = str(item["path"])
            target = root / item_path
            if item["existed"]:
                backup = audit / "backup" / item_path
                atomic_copy(backup, target, item["mode"], "rollback")
            elif target.exists() or target.is_symlink():
                target.unlink()
        if meta["service_was_running"]:
            service(root, "up")
        else:
            service(root, "down")
        if journal:
            atomic_json(journal, {"phase": "rollback_complete", "audit": str(audit), "source": RELEASE})
        marker.unlink(missing_ok=True)
        emit("ROLLBACK=PASS")
        return True
    except Exception as exc:
        emit(f"ROLLBACK=FAIL:{type(exc).__name__}")
        return False


def manual_rollback(root: Path, audit_arg: str) -> int:
    validate_root(root)
    audit = Path(audit_arg).resolve()
    allowed = (root / "audits").resolve()
    if allowed not in audit.parents or not (audit / DEPLOYMENT_METADATA).is_file():
        raise Abort("ROLLBACK_AUDIT_INVALID")
    _, active = journal_paths(root)
    ok = restore(root, audit, active)
    if ok:
        active.unlink(missing_ok=True)
    return 0 if ok else 1


def stage_files(root: Path, source: str, objects: dict[str, tuple[str, str]], stage: Path) -> tuple[list[dict[str, object]], list[str]]:
    files: list[dict[str, object]] = []
    changed: list[str] = []
    for path, (git_mode, blob) in objects.items():
        staged = stage / path
        staged.parent.mkdir(parents=True, exist_ok=True)
        data = run(["git", "show", f"{source}:{path}"], root, capture=True).stdout.encode()
        staged.write_bytes(data)
        if os.environ.get("BOTA_TEST_CORRUPT_STAGE_PATH") == path:
            staged.write_bytes(data + b"corrupt")
        actual_blob = git(root, "hash-object", str(staged))
        if actual_blob != blob:
            raise Abort(f"STAGED_BLOB_MISMATCH:{path}")
        target = root / path
        existed = target.is_file()
        old_mode = stat.S_IMODE(target.stat().st_mode) if existed else 0
        old_hash = sha256(target) if existed else None
        expected_hash = sha256(staged)
        files.append({"path": path, "blob": blob, "git_mode": git_mode, "existed": existed,
                      "mode": old_mode, "pre_sha256": old_hash, "expected_sha256": expected_hash})
        mode_needs_repair = path in EXECUTABLE and (not existed or not (old_mode & stat.S_IXUSR))
        if not existed or old_hash != expected_hash or mode_needs_repair:
            changed.append(path)
    return files, changed


def back_up_files(root: Path, backup: Path, files: list[dict[str, object]]) -> None:
    for index, item in enumerate(files):
        if item["existed"]:
            if (os.environ.get("BOTA_ALLOW_NON_TERMUX") == "1"
                    and os.environ.get("BOTA_TEST_FAIL_BACKUP_AT") == str(index)):
                raise Abort("INJECTED_BACKUP_FAILURE")
            item_path = str(item["path"])
            destination = backup / item_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / item_path, destination)


def finish_if_current(root: Path, active: Path, audit: Path, stage: Path, source: str,
                      service_was_running: bool, changed: list[str]) -> bool:
    if changed:
        return False
    if service_was_running and (not service_running(root) or watcher_instance_count(root) != 1):
        raise Abort("SERVICE_TOPOLOGY_FAILED")
    atomic_json(active, {"schema": 1, "phase": "complete", "source": source, "audit": str(audit)})
    active.unlink()
    shutil.rmtree(stage)
    emit("DEPLOYMENT=ALREADY_CURRENT")
    emit("RUNTIME_GENERATION=PASS MANIFEST_PARITY=PASS DEPENDENCY_CLOSURE=PASS")
    emit(f"AUDIT_DIRECTORY={audit}")
    return True


def install_changed(root: Path, stage: Path, files: list[dict[str, object]], changed: list[str]) -> None:
    for index, item in enumerate(files):
        item_path = str(item["path"])
        if item_path not in changed:
            continue
        if os.environ.get("BOTA_TEST_FAIL_INSTALL_AT") == str(index):
            raise Abort("INJECTED_INSTALL_FAILURE")
        target = root / item_path
        mode = 0o755 if item_path in EXECUTABLE else 0o644
        atomic_copy(stage / item_path, target, mode, "deploy")


def verify_file_content(root: Path, files: list[dict[str, object]]) -> None:
    for item in files:
        item_path = str(item["path"])
        target = root / item_path
        if not target.is_file() or sha256(target) != item["expected_sha256"]:
            raise Abort(f"POST_DEPLOY_MISMATCH:{item_path}")
        if item_path in EXECUTABLE and not os.access(target, os.X_OK):
            raise Abort(f"POST_DEPLOY_MODE_MISMATCH:{item_path}")
    if os.environ.get("BOTA_TEST_POST_VERIFY_MISMATCH"):
        raise Abort("POST_DEPLOY_MISMATCH:INJECTED")


def verify_runtime_state(root: Path, metadata: dict[str, object], service_was_running: bool) -> None:
    if service_was_running and not service_running(root):
        raise Abort("SERVICE_HEALTH_FAILED")
    if not service_was_running and service_running(root):
        raise Abort("SERVICE_STATE_CHANGED")
    if service_was_running and watcher_instance_count(root) != 1:
        raise Abort("WATCHER_DUPLICATE_OR_MISSING")
    sentinels = metadata["mutable_sentinels"]
    if not isinstance(sentinels, list):
        raise Abort("MUTABLE_SENTINELS_INVALID")
    for path in sentinels:
        if not (root / str(path)).exists():
            raise Abort(f"MUTABLE_STATE_MISSING:{path}")
    runit = root / "ops/runit/bota-watcher.run"
    if "tools/watcher_gated_cycle.sh" not in runit.read_text(encoding="utf-8"):
        raise Abort("CANONICAL_WATCHER_RUNIT_PATH_INVALID")


def verify_installed(root: Path, files: list[dict[str, object]], metadata: dict[str, object],
                     service_was_running: bool) -> None:
    verify_file_content(root, files)
    verify_runtime_state(root, metadata, service_was_running)


def deploy(root: Path, source: str) -> int:
    objects = preflight(root, source)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit = root / "audits" / f"transactional_phone_deploy_{stamp}_{os.getpid()}"
    stage, backup = audit / "stage", audit / "backup"
    state, active = journal_paths(root)
    service_was_running = service_running(root)
    try:
        stage.mkdir(parents=True)
        backup.mkdir(parents=True)
        state.mkdir(parents=True, exist_ok=True)
        files, changed = stage_files(root, source, objects, stage)
        metadata = {"schema": 1, "source": source, "service": SERVICE,
                    "service_was_running": service_was_running, "files": files,
                    "mutable_sentinels": mutable_sentinels(root)}
        (audit / "source_commit.txt").write_text(source + "\n", encoding="ascii")
        (audit / "runtime_manifest.txt").write_text("\n".join(MANIFEST) + "\n", encoding="utf-8")
        try:
            back_up_files(root, backup, files)
        except Exception as exc:
            atomic_json(audit / "backup_failure.json",
                        {"schema": 1, "source": source, "status": "backup_failed",
                         "error_type": type(exc).__name__})
            raise
        atomic_json(audit / DEPLOYMENT_METADATA, metadata)
        atomic_json(active, {"schema": 1, "phase": "backups_complete", "source": source, "audit": str(audit)})
        if finish_if_current(root, active, audit, stage, source, service_was_running, changed):
            return 0
        marker = state / GENERATION_MARKER
        atomic_json(marker, {"source": source, "audit": str(audit)})
        service(root, "down")
        atomic_json(active, {"schema": 1, "phase": "service_quiesced", "source": source, "audit": str(audit)})
        install_changed(root, stage, files, changed)
        atomic_json(active, {"schema": 1, "phase": "files_installed", "source": source, "audit": str(audit)})
        if service_was_running:
            service(root, "up")
        verify_installed(root, files, metadata, service_was_running)
        atomic_json(audit / "provenance.json", {"source": source, "manifest": list(MANIFEST)})
        marker.unlink(missing_ok=True)
        shutil.rmtree(stage)
        atomic_json(active, {"schema": 1, "phase": "complete", "source": source, "audit": str(audit)})
        active.unlink()
        emit("DEPLOYMENT=PASS")
        emit("RUNTIME_GENERATION=PASS MANIFEST_PARITY=PASS DEPENDENCY_CLOSURE=PASS")
        emit(f"AUDIT_DIRECTORY={audit}")
        return 0
    except Exception:
        rollback_ok = False
        if (audit / DEPLOYMENT_METADATA).exists():
            rollback_ok = restore(root, audit, active)
        if rollback_ok:
            (state / GENERATION_MARKER).unlink(missing_ok=True)
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--rollback-audit")
    args = parser.parse_args()
    if not args.apply:
        raise Abort("APPLY_FLAG_REQUIRED")
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).resolve()
    if args.rollback_audit:
        return manual_rollback(root, args.rollback_audit)
    return deploy(root, args.source_commit)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Abort as exc:
        emit(f"DEPLOYMENT_ABORTED={exc}")
        raise SystemExit(2)
