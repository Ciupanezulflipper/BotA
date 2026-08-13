#!/usr/bin/env python3
"""Shared HTTP scaffolding for the free-tier FX candle providers.

The per-provider modules keep only their own URL, payload shape and error
vocabulary; interval mapping, timestamp rendering, the JSON GET and the
standardized CLI live here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

INTERVAL_BY_MINUTES = {
    "1": "1min",
    "5": "5min",
    "15": "15min",
    "30": "30min",
    "60": "60min",
}
DEFAULT_INTERVAL = "15min"
DEFAULT_TIMEOUT_SEC = 20
CANDLE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

FetchFn = Callable[[str, Any, int], dict]


def tf_to_interval(tf: Any) -> str:
    """Map a BotA timeframe (``15``, ``M15``) to a provider interval string."""
    minutes = str(tf).lower().replace("m", "")
    return INTERVAL_BY_MINUTES.get(minutes, DEFAULT_INTERVAL)


def utc_iso(ts: dt.datetime) -> str:
    """Render a candle timestamp in UTC ``Z`` form, treating naive input as UTC."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_candle_time(value: str) -> dt.datetime:
    """Parse a provider candle timestamp, which is always UTC wall time."""
    return dt.datetime.strptime(value, CANDLE_TIME_FORMAT).replace(
        tzinfo=dt.timezone.utc
    )


def get_json(url: str, timeout: int = DEFAULT_TIMEOUT_SEC) -> tuple[Any, str]:
    """GET one JSON document, returning ``(payload, error)`` without raising."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            raw = response.read().decode("utf-8", "ignore")
        return json.loads(raw), ""
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:  # noqa: BLE001 - provider errors are reported, never raised
        return None, f"request failed: {exc}"


def candle_age_minutes(last_ts_utc: dt.datetime | None) -> float:
    """Minutes between the newest candle and now, or a sentinel when absent."""
    if last_ts_utc is None:
        return 1e9
    now_utc = dt.datetime.now(dt.timezone.utc)
    return (now_utc - last_ts_utc).total_seconds() / 60.0


def success(
    *,
    provider: str,
    symbol: str,
    interval: str,
    candles: list[dict],
    last_ts_utc: dt.datetime | None,
) -> dict:
    """Build the standardized provider success envelope."""
    return {
        "ok": True,
        "provider": provider,
        "symbol": symbol.upper(),
        "interval": interval,
        "rows": len(candles),
        "last_ts": utc_iso(last_ts_utc) if last_ts_utc else None,
        "age_min": round(candle_age_minutes(last_ts_utc), 3),
        "candles": candles,
    }


def failure(error: str) -> dict:
    """Build the standardized provider failure envelope."""
    return {"ok": False, "error": error}


def run_cli(fetch: FetchFn, argv: list[str] | None = None) -> None:
    """Run the shared ``--symbol/--tf/--limit`` provider CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--limit", type=int, default=150)
    args = parser.parse_args(argv)

    result = fetch(args.symbol, args.tf, args.limit)
    if not result.get("ok"):
        print(f"ERROR: {result.get('error','unknown')}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)
