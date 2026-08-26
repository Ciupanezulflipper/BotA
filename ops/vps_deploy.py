#!/usr/bin/env python3
"""Transactional, exact-generation BotA VPS release deployment."""
from __future__ import annotations

import argparse
import fcntl
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Sequence

SERVICE_USER = "bota"
SERVICE_GROUP = "bota"
RELEASE_ROOT = Path("/opt/bota/releases")
CURRENT_RELEASE = Path("/opt/bota/current")
MUTABLE_ROOT = Path("/var/lib/bota")
SECRET_ROOT = Path("/etc/bota")
DEPLOY_LOCK = Path("/run/lock/bota-deploy.lock")
SYSTEMD_SERVICE = "bota.service"
JOURNAL_RELATIVE = Path("state/vps_deploy_journal.json")
MANIFEST_NAME = ".bota-release.json"
SHA_RE = re.compile(r"[0-9a-f]{40}")
TERMINAL_PHASES = {"COMPLETE", "ROLLED_BACK", "RECOVERED_ROLLED_BACK"}


class DeployError(RuntimeError):
    pass


class DeployLocked(DeployError):
    pass


class CommandError(DeployError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_tree(root: Path) -> None:
    """Flush staged regular files and directories before release publication."""
    directories = [root]
    for current, names, files in os.walk(root, followlinks=False):
        directory = Path(current)
        directories.extend(directory / name for name in names
                           if not (directory / name).is_symlink())
        for name in files:
            path = directory / name
            if path.is_symlink():
                continue
            fd = os.open(path, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    for directory in reversed(directories):
        fsync_directory(directory)


def durable_json(path: Path, value: object,
                 directory_fsync: Callable[[Path], None] = fsync_directory,
                 *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fsync(path.parent)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


class Runner:
    def run(self, argv: Sequence[str], *, cwd: Path | None = None,
            env: Mapping[str, str] | None = None) -> bytes:
        result = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace")[-1000:]
            raise CommandError(f"command_failed:{argv[0]}:{result.returncode}:{detail}")
        return result.stdout


class DeployLock:
    def __init__(self, path: Path):
        self.path = path
        self.stream = None

    def __enter__(self) -> "DeployLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+")
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.stream.close()
            self.stream = None
            raise DeployLocked("another deployment owns the exclusive lock") from exc
        self.stream.seek(0)
        self.stream.truncate()
        self.stream.write(f"pid={os.getpid()} acquired_at_utc={utc_now()}\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())
        return self

    def __exit__(self, *_args: object) -> None:
        if self.stream is not None:
            self.stream.close()
            self.stream = None


def resolve_exact_commit(repo: Path, requested: str, runner: Runner) -> tuple[str, str]:
    if not SHA_RE.fullmatch(requested):
        raise DeployError("target_must_be_full_lowercase_40_character_sha")
    commit = runner.run(("git", "rev-parse", "--verify", f"{requested}^{{commit}}"),
                        cwd=repo).decode("ascii").strip()
    if commit != requested:
        raise DeployError("resolved_commit_does_not_equal_requested_sha")
    kind = runner.run(("git", "cat-file", "-t", requested), cwd=repo).decode("ascii").strip()
    if kind != "commit":
        raise DeployError("target_is_not_commit")
    tree = runner.run(("git", "show", "-s", "--format=%T", requested),
                      cwd=repo).decode("ascii").strip()
    if not SHA_RE.fullmatch(tree):
        raise DeployError("invalid_tree_identity")
    return commit, tree


def _safe_member(member: tarfile.TarInfo) -> PurePosixPath:
    path = PurePosixPath(member.name)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise DeployError(f"unsafe_archive_path:{member.name}")
    if member.islnk():
        raise DeployError(f"archive_hardlink_rejected:{member.name}")
    if member.issym():
        target = PurePosixPath(member.linkname)
        if target.is_absolute():
            raise DeployError(f"unsafe_symlink_target:{member.name}")
        combined: list[str] = list(path.parent.parts)
        for part in target.parts:
            if part in ("", "."):
                continue
            if part == "..":
                if not combined:
                    raise DeployError(f"unsafe_symlink_target:{member.name}")
                combined.pop()
            else:
                combined.append(part)
    elif not (member.isdir() or member.isfile()):
        raise DeployError(f"unsupported_archive_member:{member.name}")
    return path


def extract_archive_safely(archive: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as bundle:
        members = bundle.getmembers()
        checked = [(member, _safe_member(member)) for member in members]
        for member, relative in checked:
            output = destination.joinpath(*relative.parts)
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
                os.chmod(output, 0o755)
            elif member.isfile():
                output.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                if source is None:
                    raise DeployError(f"archive_file_unreadable:{member.name}")
                with output.open("wb") as stream:
                    shutil.copyfileobj(source, stream)
                os.chmod(output, 0o755 if member.mode & 0o111 else 0o644)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(member.linkname, output)


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise DeployError(f"invalid_json:{path.name}") from exc
    if not isinstance(value, dict):
        raise DeployError(f"invalid_json_object:{path.name}")
    return value


def validate_manifest(path: Path, commit: str, tree: str) -> dict[str, object]:
    value = read_json(path / MANIFEST_NAME)
    if (value.get("schema_version") != "1.0" or value.get("git_commit_sha") != commit
            or value.get("git_tree_sha") != tree
            or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("effective_config_fingerprint", "")))):
        raise DeployError("finalized_release_manifest_mismatch")
    return value


def validate_finalized_release(path: Path, commit: str, tree: str) -> dict[str, object]:
    if not path.is_dir() or path.is_symlink():
        raise DeployError("finalized_release_not_directory")
    if stat.S_IMODE(path.stat().st_mode) != 0o755:
        raise DeployError("finalized_release_mode_invalid")
    manifest_path = path / MANIFEST_NAME
    if (not manifest_path.is_file() or manifest_path.is_symlink()
            or stat.S_IMODE(manifest_path.stat().st_mode) != 0o644):
        raise DeployError("finalized_release_manifest_mode_invalid")
    return validate_manifest(path, commit, tree)


class Systemd:
    def __init__(self, runner: Runner, cgroup_root: Path = Path("/sys/fs/cgroup")):
        self.runner = runner
        self.cgroup_root = cgroup_root

    def stop(self) -> None:
        self.runner.run(("systemctl", "stop", SYSTEMD_SERVICE))

    def start(self) -> None:
        self.runner.run(("systemctl", "start", SYSTEMD_SERVICE))

    def properties(self) -> dict[str, str]:
        raw = self.runner.run(("systemctl", "show", SYSTEMD_SERVICE, "--property=ActiveState",
                               "--property=SubState", "--property=MainPID",
                               "--property=ControlGroup")).decode("utf-8")
        return dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)

    def prove_stopped(self) -> None:
        props = self.properties()
        if props.get("ActiveState") not in {"inactive", "failed"}:
            raise DeployError("service_not_stopped")
        if props.get("MainPID") not in {"0", ""}:
            raise DeployError("stale_main_pid")
        control = props.get("ControlGroup", "")
        if control:
            group = self.cgroup_root / control.lstrip("/")
            procs = group / "cgroup.procs"
            if group.exists() and not procs.exists():
                raise DeployError("service_cgroup_unverifiable")
            if procs.exists() and procs.read_text(encoding="ascii").strip():
                raise DeployError("service_cgroup_not_empty")

    def prove_active(self) -> int:
        props = self.properties()
        if props.get("ActiveState") != "active" or props.get("SubState") != "running":
            raise DeployError("service_not_active")
        try:
            pid = int(props.get("MainPID", "0"))
        except ValueError as exc:
            raise DeployError("service_main_pid_invalid") from exc
        if pid <= 0:
            raise DeployError("service_main_pid_missing")
        return pid

    def is_active(self) -> bool:
        props = self.properties()
        active = props.get("ActiveState")
        sub = props.get("SubState")
        try:
            pid = int(props.get("MainPID", ""))
        except ValueError as exc:
            raise DeployError("service_runtime_state_invalid") from exc
        if active == "active" and sub == "running" and pid > 0:
            return True
        if active in {"inactive", "failed"} and pid == 0:
            return False
        raise DeployError("service_runtime_state_ambiguous")


@dataclass
class Paths:
    release_root: Path = RELEASE_ROOT
    current: Path = CURRENT_RELEASE
    mutable_root: Path = MUTABLE_ROOT
    deploy_lock: Path = DEPLOY_LOCK

    @property
    def journal(self) -> Path:
        return self.mutable_root / JOURNAL_RELATIVE


class Deployer:
    def __init__(self, repo: Path, paths: Paths = Paths(), *, runner: Runner | None = None,
                 systemd: Systemd | None = None, python: str = "python3.14",
                 activation_timeout: float = 60.0, progress_max_age: float = 90.0,
                 fault: Callable[[str], None] | None = None,
                 directory_fsync: Callable[[Path], None] = fsync_directory):
        self.repo = repo.resolve()
        self.paths = paths
        self.runner = runner or Runner()
        self.systemd = systemd or Systemd(self.runner)
        self.python = python
        self.activation_timeout = activation_timeout
        self.progress_max_age = progress_max_age
        self.fault = fault or (lambda _point: None)
        self.directory_fsync = directory_fsync
        self.journal: dict[str, object] = {}
        self.service_stopped = False

    def _write_journal(self, phase: str, **changes: object) -> None:
        self.journal.update(changes, phase=phase, updated_at_utc=utc_now())
        durable_json(self.paths.journal, self.journal, self.directory_fsync)

    def _current_target(self) -> Path | None:
        current = self.paths.current
        if not os.path.lexists(current):
            return None
        if not current.is_symlink():
            raise DeployError("current_is_not_symlink")
        raw = Path(os.readlink(current))
        return raw if raw.is_absolute() else (current.parent / raw).resolve()

    def _switch(self, target: Path | None) -> None:
        current = self.paths.current
        current.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(current) and not current.is_symlink():
            raise DeployError("current_is_not_symlink")
        temporary = current.parent / f".{current.name}.{uuid.uuid4().hex}.tmp"
        try:
            if target is None:
                if os.path.lexists(current):
                    current.unlink()
            else:
                os.symlink(str(target), temporary)
                os.replace(temporary, current)
            self.directory_fsync(current.parent)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _fingerprint(self, release: Path) -> str:
        sys.path.insert(0, str(self.repo))
        try:
            from tools.vps_orchestrator import effective_config_evidence
            return str(effective_config_evidence(
                policy_path=release / "config/production-vps.env",
                dependency_path=release / "requirements-runtime.txt",
                pyproject_path=release / "pyproject.toml")["fingerprint_sha256"])
        finally:
            sys.path.pop(0)

    def _stage(self, commit: str, tree: str) -> tuple[Path, dict[str, object], bool]:
        final = self.paths.release_root / commit
        self.paths.release_root.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.paths.release_root.parent, 0o755)
        self.paths.release_root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.paths.release_root, 0o755)
        if final.exists():
            manifest = validate_finalized_release(final, commit, tree)
            try:
                actual_fingerprint = self._fingerprint(final)
            except Exception as exc:
                raise DeployError("finalized_release_fingerprint_unverifiable") from exc
            if manifest["effective_config_fingerprint"] != actual_fingerprint:
                raise DeployError("finalized_release_fingerprint_mismatch")
            return final, manifest, True
        previous_umask = os.umask(0o022)
        staging: Path | None = None
        try:
            staging = Path(tempfile.mkdtemp(
                prefix=f".staging-{commit}-", dir=self.paths.release_root))
            os.chmod(staging, 0o755)
            archive = self.runner.run(("git", "archive", "--format=tar", commit), cwd=self.repo)
            extract_archive_safely(archive, staging)
            self.fault("after_staging")
            self.runner.run((self.python, "-m", "venv", str(staging / ".venv")))
            candidate_python = staging / ".venv/bin/python"
            self.runner.run((str(candidate_python), "-m", "pip", "install", "--disable-pip-version-check",
                             "-r", str(staging / "requirements-runtime.txt")))
            self.runner.run((str(candidate_python), "-m", "pip", "check"))
            fingerprint = self._fingerprint(staging)
            manifest = {"schema_version": "1.0", "git_commit_sha": commit,
                        "git_tree_sha": tree, "created_at_utc": utc_now(),
                        "effective_config_fingerprint": fingerprint}
            durable_json(staging / MANIFEST_NAME, manifest, self.directory_fsync, mode=0o644)
            env = dict(os.environ, BOTA_CODE_ROOT=str(staging), BOTA_ROOT=str(staging),
                       BOTA_MUTABLE_ROOT=str(self.paths.mutable_root))
            output = self.runner.run((str(candidate_python), str(staging / "tools/vps_orchestrator.py"),
                                      "--release-preflight"), cwd=staging, env=env)
            result = json.loads(output.decode("utf-8"))
            if not isinstance(result, dict) or result.get("healthy") is not True:
                raise DeployError("candidate_preflight_failed")
            fsync_tree(staging)
            os.chmod(staging, 0o755)
            os.replace(staging, final)
            self.directory_fsync(self.paths.release_root)
            return final, manifest, False
        except BaseException:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)
            raise
        finally:
            os.umask(previous_umask)

    def _read_health_optional(self) -> dict[str, object] | None:
        path = self.paths.mutable_root / "state/vps_orchestrator_health.json"
        try:
            return read_json(path)
        except DeployError:
            return None

    def _prove_activation(self, sha: str, fingerprint: str,
                          previous_instance: str | None) -> dict[str, object]:
        deadline = time.monotonic() + self.activation_timeout
        last_failure = "activation_timeout"
        while time.monotonic() <= deadline:
            try:
                main_pid = self.systemd.prove_active()
                health = self._read_health_optional()
                if health is None:
                    raise DeployError("health_missing")
                health_pid = health.get("orchestrator_pid")
                if (not isinstance(health_pid, int) or isinstance(health_pid, bool)
                        or health_pid <= 0 or health_pid != main_pid):
                    raise DeployError("health_orchestrator_pid_mismatch")
                instance = health.get("runtime_instance_id")
                if health.get("lifecycle") != "RUNNING" or health.get("process_liveness") is not True:
                    raise DeployError("health_not_running")
                if not isinstance(instance, str) or not instance or instance == previous_instance:
                    raise DeployError("runtime_instance_not_new")
                if health.get("release_git_sha") != sha:
                    raise DeployError("health_release_mismatch")
                if health.get("effective_config_fingerprint") != fingerprint:
                    raise DeployError("health_fingerprint_mismatch")
                progress = health.get("last_loop_progress_utc")
                if not isinstance(progress, str):
                    raise DeployError("loop_progress_missing")
                moment = datetime.fromisoformat(progress.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - moment).total_seconds()
                if age < -5 or age > self.progress_max_age:
                    raise DeployError("loop_progress_stale")
                main_pid_after = self.systemd.prove_active()
                if main_pid_after != main_pid:
                    raise DeployError("service_main_pid_changed")
                return health
            except (DeployError, ValueError) as exc:
                last_failure = str(exc)
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        raise DeployError(last_failure)

    def _recover_incomplete(self) -> None:
        if not self.paths.journal.exists():
            return
        old = read_json(self.paths.journal)
        if old.get("phase") in TERMINAL_PHASES:
            return
        target = self.paths.release_root / str(old.get("target_sha", ""))
        previous_raw = old.get("previous_release")
        previous = Path(previous_raw) if isinstance(previous_raw, str) and previous_raw else None
        actual = self._current_target()
        if actual not in {target, previous}:
            raise DeployError("incomplete_deployment_ambiguous_current")
        self.journal = old
        self.systemd.stop()
        self.systemd.prove_stopped()
        self._switch(previous)
        if previous is not None and old.get("previous_expected_running") is True:
            manifest = validate_manifest(previous, previous.name,
                                         str(read_json(previous / MANIFEST_NAME)["git_tree_sha"]))
            before_restart = self._read_health_optional() or {}
            prior_instance = before_restart.get("runtime_instance_id")
            self.systemd.start()
            self._prove_activation(previous.name, str(manifest["effective_config_fingerprint"]),
                                   str(prior_instance) if prior_instance else None)
        self._write_journal("RECOVERED_ROLLED_BACK", rollback_result="PASS")
        raise DeployError("incomplete_deployment_recovered_rerun_required")

    def _rollback(self, failure: BaseException) -> None:
        previous_raw = self.journal.get("previous_release")
        previous = Path(previous_raw) if isinstance(previous_raw, str) and previous_raw else None
        try:
            self.systemd.stop()
            self.systemd.prove_stopped()
            rollback_fault = None
            try:
                self.fault("during_rollback")
            except BaseException as injected:
                rollback_fault = f"{type(injected).__name__}:{injected}"
            self._switch(previous)
            if previous is not None and self.journal.get("previous_expected_running") is True:
                prior_manifest = read_json(previous / MANIFEST_NAME)
                before_restart = self._read_health_optional() or {}
                self.systemd.start()
                self._prove_activation(previous.name,
                    str(prior_manifest["effective_config_fingerprint"]),
                    str(before_restart.get("runtime_instance_id") or ""))
            rollback_result = "PASS" if rollback_fault is None else f"PASS_AFTER_RETRY:{rollback_fault}"
            self._write_journal("ROLLED_BACK", failure=str(failure), rollback_result=rollback_result)
        except BaseException as rollback_exc:
            self._write_journal("ROLLBACK_FAILED", failure=str(failure),
                                rollback_result=f"FAIL:{type(rollback_exc).__name__}:{rollback_exc}")
            raise DeployError(f"rollback_failed:{rollback_exc}") from failure

    def deploy(self, requested: str) -> dict[str, object]:
        with DeployLock(self.paths.deploy_lock):
            self._recover_incomplete()
            commit, tree = resolve_exact_commit(self.repo, requested, self.runner)
            final, manifest, _reused = self._stage(commit, tree)
            previous = self._current_target()
            previous_health = self._read_health_optional()
            previous_instance = (previous_health or {}).get("runtime_instance_id")
            previous_running = self.systemd.is_active()
            self.journal = {"schema_version": "1.0", "deployment_id": str(uuid.uuid4()),
                            "target_sha": commit, "target_tree_sha": tree,
                            "previous_release": str(previous) if previous else None,
                            "previous_runtime_instance_id": previous_instance,
                            "previous_expected_running": previous_running,
                            "started_at_utc": utc_now(), "failure": None,
                            "rollback_result": None}
            self._write_journal("PREPARED")
            self.fault("after_journal_prepared")
            try:
                self.systemd.stop()
                self.service_stopped = True
                self.systemd.prove_stopped()
                self.fault("after_service_stop")
                self._switch(final)
                self.fault("after_current_switch")
                self._write_journal("ACTIVATING")
                self.systemd.start()
                self.fault("after_service_start")
                health = self._prove_activation(commit,
                    str(manifest["effective_config_fingerprint"]),
                    str(previous_instance) if previous_instance else None)
                self.fault("before_activation_proof_completion")
                self._write_journal("COMPLETE",
                                    target_runtime_instance_id=health["runtime_instance_id"])
                return dict(self.journal)
            except BaseException as exc:
                if self.service_stopped:
                    self._rollback(exc)
                raise

    def stage_only(self, requested: str) -> dict[str, object]:
        """Finalize an exact immutable release without inspecting or changing runtime state."""
        with DeployLock(self.paths.deploy_lock):
            commit, tree = resolve_exact_commit(self.repo, requested, self.runner)
            final, manifest, reused = self._stage(commit, tree)
            return {
                "healthy": True,
                "operation": "STAGE_ONLY",
                "requested_sha": requested,
                "resolved_commit_sha": commit,
                "tree_sha": tree,
                "finalized_release_path": str(final),
                "effective_config_fingerprint": manifest["effective_config_fingerprint"],
                "reused_existing_release": reused,
                "service_touched": False,
                "current_release_changed": False,
            }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("git_commit_sha")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--stage-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        deployer = Deployer(args.repo)
        if args.stage_only:
            result = deployer.stage_only(args.git_commit_sha)
        else:
            result = {"healthy": True, "journal": deployer.deploy(args.git_commit_sha)}
    except DeployError as exc:
        print(json.dumps({"healthy": False, "failure": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
