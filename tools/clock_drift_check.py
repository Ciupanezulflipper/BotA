#!/usr/bin/env python3
"""
FILE: tools/clock_drift_check.py
ROLE: BotA local-vs-server UTC observability for cruise/ship clock drift.

This script is reporting-only. It does not decide whether the market is open,
does not alter strategy, and does not change thresholds.
"""
from __future__ import annotations

import argparse
import email.utils
import json
import os
import statistics
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_URLS = [
    "https://www.google.com",
    "https://api-fxpractice.oanda.com",
    "https://query1.finance.yahoo.com",
    "https://www.cloudflare.com",
]


@dataclass
class ServerClockResult:
    ok: bool
    server_epoch: int | None
    server_iso: str
    count: int
    spread_seconds: int | None
    sources: list[str]
    errors: list[str]
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_date_header(url: str, timeout: int) -> tuple[int | None, str | None]:
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "Mozilla/5.0 BotA-clock-drift-check"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            date_header = response.headers.get("Date")
    except urllib.error.HTTPError as exc:
        # Many useful HTTP errors still include a trustworthy Date header.
        date_header = exc.headers.get("Date")
    except Exception as exc:  # noqa: BLE001 - must stay best-effort on ship internet
        return None, f"{url}: {type(exc).__name__}: {exc}"

    if not date_header:
        return None, f"{url}: missing Date header"

    try:
        parsed = email.utils.parsedate_to_datetime(date_header)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp()), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{url}: bad Date header: {exc}"


def compute_server_clock(
    urls: Iterable[str],
    timeout: int,
    max_spread_seconds: int,
) -> ServerClockResult:
    epochs: list[int] = []
    sources: list[str] = []
    errors: list[str] = []

    for url in urls:
        epoch, error = read_date_header(url, timeout)
        if epoch is None:
            if error:
                errors.append(error)
            continue
        epochs.append(epoch)
        sources.append(url)

    if len(epochs) < 2:
        return ServerClockResult(
            ok=False,
            server_epoch=None,
            server_iso="NA",
            count=len(epochs),
            spread_seconds=None,
            sources=sources,
            errors=errors,
            reason="server_clock_unavailable",
        )

    spread = max(epochs) - min(epochs)
    if spread > max_spread_seconds:
        return ServerClockResult(
            ok=False,
            server_epoch=None,
            server_iso="NA",
            count=len(epochs),
            spread_seconds=spread,
            sources=sources,
            errors=errors,
            reason="server_clock_spread_too_high",
        )

    server_epoch = int(statistics.median(epochs))
    server_dt = datetime.fromtimestamp(server_epoch, timezone.utc)
    return ServerClockResult(
        ok=True,
        server_epoch=server_epoch,
        server_iso=iso_z(server_dt),
        count=len(epochs),
        spread_seconds=spread,
        sources=sources,
        errors=errors,
        reason="server_clock_ok",
    )


def build_status(args: argparse.Namespace) -> dict:
    local_dt = utc_now()
    result = compute_server_clock(
        urls=args.url,
        timeout=args.timeout,
        max_spread_seconds=args.max_spread_seconds,
    )

    status = {
        "generated_utc": iso_z(local_dt),
        "local_utc": iso_z(local_dt),
        "server_clock_ok": result.ok,
        "server_utc": result.server_iso,
        "server_sources_count": result.count,
        "server_spread_seconds": result.spread_seconds,
        "server_reason": result.reason,
        "clock_drift_warn_seconds": args.warn_seconds,
        "local_clock_unsafe": None,
        "drift_seconds": None,
        "drift_abs_seconds": None,
        "status": "SERVER_CLOCK_UNAVAILABLE",
        "sources": result.sources,
        "errors": result.errors[:8],
        "strategy_changed": "NO",
        "thresholds_changed": "NO",
        "production_changed_by_this_report": "NO",
    }

    if result.ok and result.server_epoch is not None:
        local_epoch = int(local_dt.timestamp())
        drift = local_epoch - result.server_epoch
        unsafe = abs(drift) > args.warn_seconds
        status.update(
            {
                "local_clock_unsafe": unsafe,
                "drift_seconds": drift,
                "drift_abs_seconds": abs(drift),
                "status": "DRIFT_WARN" if unsafe else "OK",
            }
        )

    return status


def default_state_file() -> Path:
    root = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")))
    return root / "logs" / "clock_drift_status.json"


def write_state(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_plain(status: dict) -> None:
    print("=== BotA Clock Drift Status ===")
    print(f"Generated UTC: {status['generated_utc']}")
    print(f"Local UTC: {status['local_utc']}")
    print(f"Server UTC: {status['server_utc']}")
    print(f"Server clock OK: {'YES' if status['server_clock_ok'] else 'NO'}")
    print(f"Server sources: {status['server_sources_count']}")
    print(f"Server spread seconds: {status['server_spread_seconds']}")
    print(f"Reason: {status['server_reason']}")

    if status["drift_seconds"] is None:
        print("Clock drift seconds: UNKNOWN")
        print("Local clock unsafe: UNKNOWN")
    else:
        print(f"Clock drift seconds: {status['drift_seconds']}")
        print(f"Clock drift abs seconds: {status['drift_abs_seconds']}")
        print(f"Warn threshold seconds: {status['clock_drift_warn_seconds']}")
        print(f"Local clock unsafe: {'YES' if status['local_clock_unsafe'] else 'NO'}")

    print(f"Status: {status['status']}")
    print("Strategy changed: NO")
    print("Thresholds changed: NO")
    print("Production changed by this report: NO")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report BotA local-vs-server UTC drift without changing trading logic."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of plain text.")
    parser.add_argument("--plain", action="store_true", help="Print plain text. Default.")
    parser.add_argument("--write-state", action="store_true", help="Write logs/clock_drift_status.json.")
    parser.add_argument("--state-file", default=str(default_state_file()), help="State JSON path.")
    parser.add_argument(
        "--warn-seconds",
        type=int,
        default=int(os.environ.get("CLOCK_DRIFT_WARN_SECS", "300")),
        help="Mark local clock unsafe above this absolute drift. Default: 300.",
    )
    parser.add_argument(
        "--max-spread-seconds",
        type=int,
        default=int(os.environ.get("CLOCK_SERVER_MAX_SPREAD_SECS", "120")),
        help="Reject server samples if their spread is above this value. Default: 120.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("CLOCK_HTTP_TIMEOUT_SECS", "12")),
        help="HTTP timeout per clock source. Default: 12.",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=None,
        help="Override/add HTTPS URL to sample for Date header. Can be repeated.",
    )
    args = parser.parse_args(argv)
    if args.url is None:
        args.url = DEFAULT_URLS
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    status = build_status(args)

    if args.write_state:
        try:
            write_state(Path(args.state_file), status)
        except Exception as exc:  # noqa: BLE001
            # Observability must not fail the caller.
            status.setdefault("state_write_error", f"{type(exc).__name__}: {exc}")

    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print_plain(status)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
