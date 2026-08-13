#!/usr/bin/env python3
"""Delivery-aware wrapper around the unchanged BotA chart renderer.

A Telegram text delivery that was already authoritatively confirmed and merely
reconciled in this cycle must not produce a second Telegram chart. All normal
chart rendering is delegated byte-for-byte to ``chart_generator_core.py``.
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
            return False
        if not path.name.startswith("watcher_telegram.") or not path.name.endswith(".jsonl"):
            return False
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    except (OSError, ValueError):
        return False
    matches = [
        item for item in records
        if str(item.get("pair") or "").upper() == pair
        and str(item.get("timeframe") or "").upper() == timeframe
    ]
    return len(matches) == 1 and str(matches[0].get("status") or "") == "reconciled_sent"


def main() -> None:
    if reconciled_text_delivery():
        print("[chart] SKIP reconciled prior Telegram text delivery", file=sys.stderr)
        return
    runpy.run_path(str(CORE), run_name="__main__")


if __name__ == "__main__":
    main()
