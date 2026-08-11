from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


EXIT_OK = 0
EXIT_ALREADY_RUNNING = 23
EXIT_CONFIG_ERROR = 24
EXIT_MAX_STARTS_REACHED = 25


@dataclass(frozen=True)
class OwnerConfig:
    state_dir: Path
    poll_seconds: float
    stale_seconds: float
    terminate_grace_seconds: float
    restart_backoff_seconds: float
    max_runtime_starts: int
    runtime_command: tuple[str, ...]

    @property
    def lock_path(self) -> Path:
        return self.state_dir / "owner.lock"

    @property
    def heartbeat_path(self) -> Path:
        return self.state_dir / "runtime_heartbeat.json"

    @property
    def events_path(self) -> Path:
        return self.state_dir / "owner_events.jsonl"


def _utc_epoch() -> float:
    return time.time()


def _append_event(path: Path, event: str, **fields: object) -> None:
    payload = {"event": event, "timestamp_utc": _utc_epoch(), **fields}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _read_heartbeat(path: Path) -> dict[str, object] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def heartbeat_is_stale(path: Path, stale_seconds: float, now: float | None = None) -> bool:
    now_value = _utc_epoch() if now is None else now
    payload = _read_heartbeat(path)
    if payload is None:
        return True
    value = payload.get("heartbeat_write_utc")
    if not isinstance(value, (int, float)):
        return True
    return now_value - float(value) > stale_seconds


def _terminate_process_group(proc: subprocess.Popen[bytes], grace_seconds: float) -> None:
    if proc.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=max(grace_seconds, 1.0))


def _start_runtime(config: OwnerConfig, instance_id: str) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env["BOTA_RUNTIME_INSTANCE_ID"] = instance_id
    env["BOTA_HEARTBEAT_PATH"] = str(config.heartbeat_path)
    return subprocess.Popen(
        config.runtime_command,
        env=env,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=None,
        stderr=None,
    )


def run_owner(config: OwnerConfig) -> int:
    config.state_dir.mkdir(parents=True, exist_ok=True)
    lock_handle = config.lock_path.open("a+")
    try:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("BOTA_RUNTIME_OWNER=ALREADY_RUNNING")
            return EXIT_ALREADY_RUNNING

        starts = 0
        while True:
            if config.max_runtime_starts >= 0 and starts >= config.max_runtime_starts:
                _append_event(config.events_path, "max_runtime_starts_reached", starts=starts)
                return EXIT_MAX_STARTS_REACHED

            starts += 1
            instance_id = str(uuid.uuid4())
            with contextlib.suppress(FileNotFoundError):
                config.heartbeat_path.unlink()
            proc = _start_runtime(config, instance_id)
            _append_event(
                config.events_path,
                "runtime_started",
                runtime_pid=proc.pid,
                runtime_instance_id=instance_id,
                start_number=starts,
            )

            while True:
                rc = proc.poll()
                if rc is not None:
                    _append_event(
                        config.events_path,
                        "runtime_exited",
                        runtime_pid=proc.pid,
                        runtime_instance_id=instance_id,
                        return_code=rc,
                    )
                    break

                if heartbeat_is_stale(config.heartbeat_path, config.stale_seconds):
                    _append_event(
                        config.events_path,
                        "runtime_zombie_detected",
                        runtime_pid=proc.pid,
                        runtime_instance_id=instance_id,
                    )
                    _terminate_process_group(proc, config.terminate_grace_seconds)
                    _append_event(
                        config.events_path,
                        "runtime_zombie_terminated",
                        runtime_pid=proc.pid,
                        runtime_instance_id=instance_id,
                        return_code=proc.returncode,
                    )
                    break

                time.sleep(config.poll_seconds)

            if config.restart_backoff_seconds > 0:
                time.sleep(config.restart_backoff_seconds)
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0 or not (parsed < float("inf")):
        raise argparse.ArgumentTypeError("must be finite and > 0")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> OwnerConfig:
    parser = argparse.ArgumentParser(description="BotA R1 minimal runtime owner/restarter")
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--poll-seconds", type=_positive_float, default=1.0)
    parser.add_argument("--stale-seconds", type=_positive_float, default=30.0)
    parser.add_argument("--terminate-grace-seconds", type=_positive_float, default=2.0)
    parser.add_argument("--restart-backoff-seconds", type=float, default=1.0)
    parser.add_argument("--max-runtime-starts", type=int, default=-1)
    parser.add_argument("runtime_command", nargs=argparse.REMAINDER)
    ns = parser.parse_args(argv)
    runtime_command = list(ns.runtime_command)
    if runtime_command and runtime_command[0] == "--":
        runtime_command = runtime_command[1:]
    if not runtime_command:
        parser.error("runtime command is required after --")
    if ns.restart_backoff_seconds < 0 or ns.restart_backoff_seconds == float("inf"):
        parser.error("--restart-backoff-seconds must be finite and >= 0")
    if ns.max_runtime_starts == 0 or ns.max_runtime_starts < -1:
        parser.error("--max-runtime-starts must be -1 or >= 1")
    return OwnerConfig(
        state_dir=ns.state_dir,
        poll_seconds=ns.poll_seconds,
        stale_seconds=ns.stale_seconds,
        terminate_grace_seconds=ns.terminate_grace_seconds,
        restart_backoff_seconds=ns.restart_backoff_seconds,
        max_runtime_starts=ns.max_runtime_starts,
        runtime_command=tuple(runtime_command),
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        config = parse_args(argv)
    except SystemExit:
        raise
    return run_owner(config)


if __name__ == "__main__":
    sys.exit(main())
