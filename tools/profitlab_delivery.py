#!/usr/bin/env python3
"""Deliver accepted GREEN BotA alerts to ProfitLab independently of Telegram.

The worker consumes new rows appended to logs/alerts.csv. It keeps an independent
byte cursor, retries the same eligible row until Supabase publication succeeds,
and never replays historical rows on first activation.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def root_path() -> Path:
    return Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()


def paths() -> tuple[Path, Path, Path, Path]:
    root = root_path()
    alerts = Path(
        os.environ.get("PROFITLAB_ALERTS_CSV", str(root / "logs" / "alerts.csv"))
    )
    state = Path(
        os.environ.get(
            "PROFITLAB_DELIVERY_STATE",
            str(root / "state" / "profitlab_delivery_cursor.json"),
        )
    )
    lock = Path(
        os.environ.get(
            "PROFITLAB_DELIVERY_LOCK",
            str(root / "state" / "profitlab_delivery.lock"),
        )
    )
    publisher = Path(
        os.environ.get(
            "PROFITLAB_PUBLISHER",
            str(root / "tools" / "supabase_publish.py"),
        )
    )
    return alerts, state, lock, publisher


def load_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def write_state(path: Path, offset: int, source_size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "offset": int(offset),
        "source_size": int(source_size),
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def header_fields(alerts: Path) -> list[str]:
    with alerts.open("rb") as handle:
        first = handle.readline()
    if not first:
        raise ValueError("alerts.csv header missing")
    text = first.decode("utf-8", "replace").rstrip("\r\n")
    fields = next(csv.reader([text]))
    required = {
        "pair",
        "tf",
        "direction",
        "score",
        "entry",
        "sl",
        "tp",
        "filter_rejected",
        "tier",
    }
    missing = sorted(required.difference(fields))
    if missing:
        raise ValueError(f"alerts.csv missing fields: {','.join(missing)}")
    return fields


def parse_row(raw: bytes, fields: list[str]) -> dict[str, str] | None:
    try:
        text = raw.decode("utf-8", "replace").rstrip("\r\n")
        values = next(csv.reader([text]))
    except (csv.Error, StopIteration):
        return None
    if len(values) != len(fields):
        return None
    return dict(zip(fields, values))


def is_true(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def eligible(row: dict[str, str]) -> bool:
    if row.get("direction", "").strip().upper() not in {"BUY", "SELL"}:
        return False
    if is_true(row.get("filter_rejected")):
        return False
    if row.get("tier", "").strip().upper() != "GREEN":
        return False
    try:
        score = float(row.get("score", ""))
        entry = float(row.get("entry", ""))
        sl = float(row.get("sl", ""))
        tp = float(row.get("tp", ""))
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(score) and entry > 0 and sl > 0 and tp > 0


def publish(row: dict[str, str], publisher: Path) -> bool:
    try:
        score_int = int(math.floor(float(row["score"]) + 1e-9))
    except (TypeError, ValueError, OverflowError):
        return False

    command = [
        sys.executable,
        str(publisher),
        "--pair",
        row["pair"].strip().upper(),
        "--direction",
        row["direction"].strip().upper(),
        "--entry",
        row["entry"].strip(),
        "--sl",
        row["sl"].strip(),
        "--tp",
        row["tp"].strip(),
        "--score",
        str(score_int),
        "--tf",
        row["tf"].strip().upper(),
        "--tier",
        "GREEN",
    ]
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=None,
            timeout=25,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def run(*, bootstrap: bool = False) -> int:
    alerts, state_path, lock_path, publisher = paths()

    if not alerts.exists():
        print("PROFITLAB_DELIVERY_SOURCE=MISSING")
        return 0

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("PROFITLAB_DELIVERY=ALREADY_RUNNING")
            return 0

        source_size = alerts.stat().st_size
        if bootstrap:
            write_state(state_path, source_size, source_size)
            print(f"PROFITLAB_DELIVERY_BOOTSTRAP=PASS offset={source_size}")
            return 0

        state = load_state(state_path)
        if state is None:
            write_state(state_path, source_size, source_size)
            print(f"PROFITLAB_DELIVERY_BOOTSTRAP=PASS offset={source_size}")
            return 0

        try:
            offset = int(state.get("offset", source_size))
        except (TypeError, ValueError, OverflowError):
            offset = source_size

        if offset < 0 or source_size < offset:
            write_state(state_path, source_size, source_size)
            print(f"PROFITLAB_DELIVERY_CURSOR_RESET=TO_END offset={source_size}")
            return 0

        if offset == source_size:
            print("PROFITLAB_DELIVERY=NO_NEW_ROWS")
            return 0

        try:
            fields = header_fields(alerts)
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"PROFITLAB_DELIVERY_HEADER_ERROR={type(exc).__name__}", file=sys.stderr)
            return 1

        with alerts.open("rb") as handle:
            handle.seek(offset)
            while True:
                row_start = handle.tell()
                raw = handle.readline()
                if not raw:
                    break
                row_end = handle.tell()

                if not raw.endswith(b"\n"):
                    print(f"PROFITLAB_DELIVERY_PARTIAL_ROW offset={row_start}")
                    return 0

                row = parse_row(raw, fields)
                if row is None:
                    write_state(state_path, row_end, source_size)
                    print(f"PROFITLAB_DELIVERY_SKIP=MALFORMED offset={row_start}")
                    continue

                if not eligible(row):
                    write_state(state_path, row_end, source_size)
                    continue

                if not publisher.is_file():
                    print("PROFITLAB_DELIVERY_PUBLISHER=MISSING", file=sys.stderr)
                    return 1

                if publish(row, publisher):
                    write_state(state_path, row_end, source_size)
                    print(
                        "PROFITLAB_DELIVERY=PASS "
                        f"pair={row['pair'].strip().upper()} "
                        f"tf={row['tf'].strip().upper()} "
                        f"direction={row['direction'].strip().upper()} "
                        f"score={row['score'].strip()}"
                    )
                    continue

                print(
                    "PROFITLAB_DELIVERY=RETRY_REQUIRED "
                    f"pair={row['pair'].strip().upper()} "
                    f"tf={row['tf'].strip().upper()} "
                    f"offset={row_start}",
                    file=sys.stderr,
                )
                return 1

        final_size = alerts.stat().st_size
        final_state = load_state(state_path) or {}
        final_offset = int(final_state.get("offset", offset))
        print(f"PROFITLAB_DELIVERY_DONE offset={final_offset} size={final_size}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Set the cursor to the current end of alerts.csv without publishing history.",
    )
    args = parser.parse_args()
    return run(bootstrap=args.bootstrap)


if __name__ == "__main__":
    raise SystemExit(main())
