#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alpha Vantage free-tier FX provider.
Handles rate-limit/Note cases and returns standardized JSON.

CLI:
  python3 tools/data_provider_alphavantage.py --symbol EURUSD --tf 15 --limit 150
"""
import os
import sys
from pathlib import Path

if __package__:
    from tools import provider_http as http
else:  # direct execution or file-based module loading
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import provider_http as http

PROVIDER = "alpha_vantage"


def fetch(symbol: str, tf, limit: int):
    key = os.getenv("ALPHA_VANTAGE_API_KEY","").strip()
    if not key:
        return http.failure("ALPHA_VANTAGE_API_KEY not set")

    from_sym = symbol.replace("/","").upper()[:3]
    to_sym = symbol.replace("/","").upper()[3:]
    interval = http.tf_to_interval(tf)

    url = ( "https://www.alphavantage.co/query"
            f"?function=FX_INTRADAY&from_symbol={from_sym}&to_symbol={to_sym}"
            f"&interval={interval}&outputsize=compact&apikey={key}" )

    data, error = http.get_json(url)
    if error:
        return http.failure(error)

    # Handle common free-tier messages
    if "Note" in data:
        return http.failure(f"rate-limited: {data['Note'][:100]}...")
    if "Information" in data:
        return http.failure(f"info: {data['Information'][:100]}...")
    if "Error Message" in data:
        return http.failure(f"error: {data['Error Message']}")

    # Expected key
    key_ts = next((k for k in data.keys() if k.startswith("Time Series FX")), None)
    if not key_ts or not isinstance(data.get(key_ts), dict):
        return http.failure("no time series returned")

    series = data[key_ts]  # dict of time-> { "1. open": "...", ... }
    if not series:
        return http.failure("empty time series")

    # Convert to ascending list
    items = sorted(series.items(), key=lambda kv: kv[0])
    if len(items) > limit:
        items = items[-limit:]

    candles = []
    last_ts_utc = None
    for tstr, row in items:
        # AV timestamps are in UTC like "2025-11-03 12:45:00"
        ts = http.parse_candle_time(tstr)
        last_ts_utc = ts
        candles.append({
            "ts": http.utc_iso(ts),
            "o": float(row.get("1. open", "nan")),
            "h": float(row.get("2. high", "nan")),
            "l": float(row.get("3. low", "nan")),
            "c": float(row.get("4. close", "nan")),
            "v": 0.0  # FX intraday endpoint lacks volume
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
