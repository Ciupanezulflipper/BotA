#!/usr/bin/env python3
"""Delivery-aware wrapper around the unchanged BotA chart renderer.

Canonical watcher production currently has durable Telegram text delivery but no
crash-consistent photo-delivery transaction. Therefore canonical cycles do not
create a chart PNG; this keeps the historical direct sendPhoto branch
unreachable. Manual/non-canonical chart generation remains unchanged.
"""
from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()
CORE = Path(__file__).with_name("chart_generator_core.py")


def _arg(name: str) -> str:
    try:
        index = sys.argv.index(name)
    except ValueError:
        return ""
    return sys.argv[index + 1] if index + 1 < len(sys.argv) else ""


def reconciled_text_delivery() -> bool:
    pair = _arg("--pair").upper()
    timeframe = _arg("--tf").upper()
    if not pair or not timeframe:
        return False
    raw = os.environ.get("BOTA_TELEGRAM_RESULT_LOG", "").strip()
    if not raw:
        return False
    try:
        path = Path(raw).expanduser().resolve(strict=True)
        state_dir = (ROOT / "state").resolve(strict=True)
        if path.parent != state_dir:
            raise ValueError("telegram_result_parent_invalid")
        if not path.name.startswith("watcher_telegram.") or not path.name.endswith(".jsonl"):
            raise ValueError("telegram_result_name_invalid")
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("telegram_result_type_invalid")
            records.append(value)
    except (OSError, ValueError) as exc:
        print(f"[chart] result-log validation failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from exc
    matches = [
        item for item in records
        if str(item.get("pair") or "").upper() == pair
        and str(item.get("timeframe") or "").upper() == timeframe
    ]
    return len(matches) == 1 and str(matches[0].get("status") or "") == "reconciled_sent"


def main() -> None:
    if os.environ.get("BOTA_CANONICAL_WATCHER_BOUNDARY", "").strip().lower() in {"1", "true", "yes", "on"}:
        if reconciled_text_delivery():
            print("[chart] SKIP reconciled prior Telegram text delivery", file=sys.stderr)
        else:
            print("[chart] SKIP untracked photo delivery on canonical boundary", file=sys.stderr)
        return
    runpy.run_path(str(CORE), run_name="__main__")


if __name__ == "__main__":
    main()
