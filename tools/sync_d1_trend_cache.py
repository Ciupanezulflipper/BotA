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
PAIR_FILES = {
    "EURUSD": ("indicators_EURUSD_D1.json", "d1_trend_EURUSD.json"),
    "GBPUSD": ("indicators_GBPUSD_D1.json", "d1_trend_GBPUSD.json"),
    "USDJPY": ("indicators_USDJPY_D1.json", "d1_trend_USDJPY.json"),
}


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def _cache_paths(root: Path, pair: str) -> tuple[Path, Path]:
    normalized = pair.upper().strip()
    filenames = PAIR_FILES.get(normalized)
    if filenames is None:
        raise ValueError(f"unsupported production pair: {normalized}")

    cache = (root / "cache").resolve()
    source = (cache / filenames[0]).resolve()
    target = (cache / filenames[1]).resolve()
    if source.parent != cache or target.parent != cache:
        raise ValueError("D1 cache path escaped cache directory")
    return source, target


def sync_pair(root: Path, pair: str) -> dict[str, Any]:
    pair = pair.upper().strip()
    source, target = _cache_paths(root.resolve(), pair)

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
        "--pairs",
        nargs="+",
        choices=DEFAULT_PAIRS,
        default=list(DEFAULT_PAIRS),
    )
    return parser


def _root() -> Path:
    configured = os.environ.get("BOTA_ROOT")
    return Path(configured).expanduser().resolve() if configured else (Path.home() / "BotA").resolve()


def main() -> int:
    args = _parser().parse_args()
    root = _root()
    failures = 0
    for pair in args.pairs:
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
