from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Sequence


_STOP = False


def _handle_stop(_signum: int, _frame: object) -> None:
    global _STOP
    _STOP = True


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dummy runtime for BotA R1 owner tests")
    parser.add_argument("--heartbeat-interval", type=float, default=0.1)
    parser.add_argument("--exit-after", type=float, default=-1.0)
    parser.add_argument("--stale-after", type=float, default=-1.0)
    parser.add_argument("--exit-code", type=int, default=7)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    heartbeat_path_raw = os.environ.get("BOTA_HEARTBEAT_PATH")
    instance_id = os.environ.get("BOTA_RUNTIME_INSTANCE_ID")
    if not heartbeat_path_raw or not instance_id:
        print("BOTA_DUMMY_RUNTIME=ENV_MISSING", file=sys.stderr)
        return 2

    heartbeat_path = Path(heartbeat_path_raw)
    started_monotonic = time.monotonic()
    cycle = 0

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    while not _STOP:
        elapsed = time.monotonic() - started_monotonic
        if args.exit_after >= 0 and elapsed >= args.exit_after:
            return args.exit_code

        if args.stale_after < 0 or elapsed < args.stale_after:
            cycle += 1
            now = time.time()
            _atomic_write_json(
                heartbeat_path,
                {
                    "runtime_instance_id": instance_id,
                    "runtime_pid": os.getpid(),
                    "runtime_start_utc": now - elapsed,
                    "heartbeat_write_utc": now,
                    "last_watcher_cycle_complete_utc": now,
                    "cycle_count_total": cycle,
                },
            )

        time.sleep(max(args.heartbeat_interval, 0.01))

    return 0


if __name__ == "__main__":
    sys.exit(main())
