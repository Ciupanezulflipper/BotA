#!/usr/bin/env python3
"""Synchronize BotA D1 trend cache from already-built local D1 indicators.

The indicator updater already fetches and builds D1 bundles for the configured
pairs. This helper derives the lightweight d1_trend_<PAIR>.json files from those
local bundles, avoiding a second provider request and keeping USDJPY on the same
provider/candle state as the rest of the pipeline.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PAIRS = ("EURUSD", "GBPUSD", "USDJPY")


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def sync_pair(root: Path, pair: str) -> dict[str, Any]:
    pair = pair.upper().strip()
    source = root / "cache" / f"indicators_{pair}_D1.json"
    target = root / "cache" / f"d1_trend_{pair}.json"

    if not source.is_file():
        raise FileNotFoundError(f"missing D1 indicators: {source}")

    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"D1 indicator bundle is not an object: {source}")
    if data.get("tf_ok", True) is False or data.get("error") == "tf_mismatch":
        raise ValueError(f"D1 indicator bundle failed timeframe validation: {source}")

    ema9 = _finite(data.get("ema9"))
    ema21 = _finite(data.get("ema21"))
    if ema9 is None or ema21 is None or ema9 <= 0.0 or ema21 <= 0.0:
        raise ValueError(f"invalid D1 EMA values: {source}")

    trend = "BUY" if ema9 > ema21 else "SELL"
    payload = {
        "pair": pair,
        "ema9": ema9,
        "ema21": ema21,
        "trend": trend,
        "weak": False,
        "error": "",
        "source": "local_indicators_D1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write_json(target, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync BotA D1 trend caches from local D1 indicator bundles"
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("BOTA_ROOT", str(Path.home() / "BotA")),
    )
    parser.add_argument("--pairs", nargs="+", default=list(DEFAULT_PAIRS))
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    failures = 0
    for raw_pair in args.pairs:
        pair = str(raw_pair).upper().strip()
        try:
            result = sync_pair(root, pair)
            print(
                f"D1_SYNC={pair}|trend={result['trend']}|"
                f"ema9={result['ema9']:.5f}|ema21={result['ema21']:.5f}"
            )
        except Exception as exc:
            failures += 1
            print(f"D1_SYNC_FAIL={pair}|error={type(exc).__name__}")
    print(f"D1_SYNC_STATUS={'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
