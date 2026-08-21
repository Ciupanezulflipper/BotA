#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TwelveData free-tier provider (HTTP time_series).
Returns standardized JSON with candles. Handles 'status:error'.

CLI:
  python3 tools/data_provider_twelvedata.py --symbol EURUSD --tf 15 --limit 150
"""
import os
import sys
from pathlib import Path

if __package__:
    from tools import provider_http as http
else:  # direct execution or file-based module loading
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import provider_http as http

PROVIDER = "twelve_data"


def _format_symbol(sym: str) -> str:
    # TD needs "EUR/USD" with slash
    s = sym.upper().replace(" ", "")
    if "/" not in s and len(s) == 6:
        s = s[:3] + "/" + s[3:]
    return s


def fetch(symbol: str, tf, limit: int):
    key = os.getenv("TWELVE_DATA_API_KEY","").strip()
    if not key:
        return http.failure("TWELVE_DATA_API_KEY not set")

    interval = http.tf_to_interval(tf)
    sym = _format_symbol(symbol)
    url = ( "https://api.twelvedata.com/time_series"
            f"?symbol={sym}&interval={interval}&outputsize={limit}&apikey={key}" )

    data, error = http.get_json(url)
    if error:
        return http.failure(error)

    # Handle error format
    if isinstance(data, dict) and data.get("status") == "error":
        msg = data.get("message","unknown")
        return http.failure(f"twelvedata error: {msg}")

    values = data.get("values")
    if not values:
        return http.failure("no values")

    # TD values are newest-first; convert to ascending
    values = list(reversed(values))
    if len(values) > limit:
        values = values[-limit:]

    candles = []
    last_ts_utc = None
    for row in values:
        # example "datetime": "2025-11-03 12:45:00"
        ts = http.parse_candle_time(row["datetime"])
        last_ts_utc = ts
        candles.append({
            "ts": http.utc_iso(ts),
            "o": float(row["open"]),
            "h": float(row["high"]),
            "l": float(row["low"]),
            "c": float(row["close"]),
            "v": float(row.get("volume") or 0.0),
        })

    return http.success(
        provider=PROVIDER,
        symbol=symbol,
        interval=interval,
        candles=candles,
        last_ts_utc=last_ts_utc,
    )


def main():
    http.run_cli(fetch)


if __name__ == "__main__":
    main()
