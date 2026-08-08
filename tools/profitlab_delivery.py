#!/usr/bin/env python3
"""Deliver accepted GREEN BotA alerts to ProfitLab independently of Telegram.

The worker consumes new rows appended to logs/alerts.csv. It keeps an independent
byte cursor, retries the same eligible row until Supabase publication succeeds,
never replays historical rows on first activation, and records local useful
progress in BotA's monotonic pipeline ledger.
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

ALERT_FIELDS = [
    "ts",
    "pair",
    "tf",
    "direction",
    "score",
    "confidence",
    "entry",
    "sl",
    "tp",
    "provider",
    "filter_rejected",
    "filter_reasons",
    "reasons",
    "ema_comp",
    "rsi_comp",
    "macd_comp",
    "adx_comp",
    "adx_raw",
    "rsi_raw",
    "macd_hist_raw",
    "macro6",
    "h1_trend",
    "tier",
    "session",
    "adx_regime",
]


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


def record_progress(status: str, details: str = "") -> None:
    """Record local delivery progress without making network calls."""
    ledger = Path(__file__).resolve().with_name("pipeline_ledger.py")
    if not ledger.is_file():
        return
    command = [
        sys.executable,
        str(ledger),
        "component",
        "--component",
        "profitlab_delivery",
        "--status",
        status,
        "--cycle-id",
        f"profitlab:{os.getpid()}",
        "--details",
        details[:1000],
    ]
    try:
        subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        # Delivery remains fail-closed through pipeline_health: if the ledger
        # cannot advance, the previous event becomes stale instead of being
        # falsely refreshed by a secondary health mechanism.
        return


def load_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
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


def source_has_header(alerts: Path) -> bool:
    try:
        with alerts.open("rb") as handle:
            return bool(handle.readline())
    except OSError:
        return False


def parse_row(raw: bytes) -> dict[str, str] | None:
    try:
        text = raw.decode("utf-8", "replace").rstrip("\r\n")
        values = next(csv.reader([text]))
    except (csv.Error, StopIteration):
        return None
    if len(values) != len(ALERT_FIELDS):
        return None
    return dict(zip(ALERT_FIELDS, values))


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
    values = (score, entry, sl, tp)
    return all(math.isfinite(value) for value in values) and all(
        value > 0 for value in (entry, sl, tp)
    )


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


def prepare_cursor(
    alerts: Path,
    state_path: Path,
    *,
    bootstrap: bool,
) -> tuple[int | None, int]:
    source_size = alerts.stat().st_size
    if bootstrap:
        write_state(state_path, source_size, source_size)
        print(f"PROFITLAB_DELIVERY_BOOTSTRAP=PASS offset={source_size}")
        return None, source_size

    state = load_state(state_path)
    if state is None:
        write_state(state_path, source_size, source_size)
        print(f"PROFITLAB_DELIVERY_BOOTSTRAP=PASS offset={source_size}")
        return None, source_size

    try:
        offset = int(state.get("offset", source_size))
    except (TypeError, ValueError, OverflowError):
        offset = source_size

    if offset < 0 or source_size < offset:
        write_state(state_path, source_size, source_size)
        print(f"PROFITLAB_DELIVERY_CURSOR_RESET=TO_END offset={source_size}")
        return None, source_size

    if offset == source_size:
        print("PROFITLAB_DELIVERY=NO_NEW_ROWS")
        return None, source_size

    return offset, source_size


def process_new_rows(
    alerts: Path,
    state_path: Path,
    publisher: Path,
    offset: int,
    source_size: int,
) -> int:
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

            row = parse_row(raw)
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

            if not publish(row, publisher):
                print(
                    "PROFITLAB_DELIVERY=RETRY_REQUIRED "
                    f"pair={row['pair'].strip().upper()} "
                    f"tf={row['tf'].strip().upper()} "
                    f"offset={row_start}",
                    file=sys.stderr,
                )
                return 1

            write_state(state_path, row_end, source_size)
            print(
                "PROFITLAB_DELIVERY=PASS "
                f"pair={row['pair'].strip().upper()} "
                f"tf={row['tf'].strip().upper()} "
                f"direction={row['direction'].strip().upper()} "
                f"score={row['score'].strip()}"
            )

    final_size = alerts.stat().st_size
    final_state = load_state(state_path) or {}
    final_offset = int(final_state.get("offset", offset))
    print(f"PROFITLAB_DELIVERY_DONE offset={final_offset} size={final_size}")
    return 0


def progress_details(alerts: Path, state_path: Path, result: str) -> str:
    """Build a compact non-secret progress summary."""
    try:
        source_size = alerts.stat().st_size
    except OSError:
        source_size = -1
    state = load_state(state_path) or {}
    try:
        offset = int(state.get("offset", -1))
    except (TypeError, ValueError, OverflowError):
        offset = -1
    pending = source_size - offset if source_size >= 0 and offset >= 0 else -1
    return (
        f"result={result};offset={offset};source_size={source_size};"
        f"pending_bytes={pending}"
    )


def run(*, bootstrap: bool = False) -> int:
    alerts, state_path, lock_path, publisher = paths()
    if not alerts.exists():
        record_progress("failed", "result=source_missing")
        print("PROFITLAB_DELIVERY_SOURCE=MISSING")
        return 0
    if not source_has_header(alerts):
        record_progress("failed", "result=source_empty")
        print("PROFITLAB_DELIVERY_SOURCE=EMPTY")
        return 0

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Do not refresh health from a second instance. If the lock owner
            # becomes stuck, its earlier started event will age out naturally.
            print("PROFITLAB_DELIVERY=ALREADY_RUNNING")
            return 0

        record_progress("started", progress_details(alerts, state_path, "started"))
        try:
            offset, source_size = prepare_cursor(
                alerts,
                state_path,
                bootstrap=bootstrap,
            )
        except OSError as exc:
            record_progress(
                "failed",
                progress_details(alerts, state_path, f"cursor_error:{type(exc).__name__}"),
            )
            print(
                f"PROFITLAB_DELIVERY_CURSOR_ERROR={type(exc).__name__}",
                file=sys.stderr,
            )
            return 1

        if offset is None:
            record_progress(
                "completed",
                progress_details(alerts, state_path, "idle_or_bootstrap"),
            )
            return 0

        result = process_new_rows(
            alerts,
            state_path,
            publisher,
            offset,
            source_size,
        )
        record_progress(
            "completed" if result == 0 else "failed",
            progress_details(
                alerts,
                state_path,
                "processed" if result == 0 else "retry_required",
            ),
        )
        return result


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
