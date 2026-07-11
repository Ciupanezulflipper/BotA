from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ParsedCandle:
    time: datetime
    complete: bool
    volume: int
    open: float
    high: float
    low: float
    close: float


def parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def parse_oanda_mid_payload(raw: bytes) -> list[ParsedCandle]:
    payload: dict[str, Any] = json.loads(raw.decode("utf-8"))
    candles = payload.get("candles")
    if not isinstance(candles, list):
        raise ValueError("payload.candles must be a list")
    out: list[ParsedCandle] = []
    for item in candles:
        if not isinstance(item, dict):
            raise ValueError("candle must be an object")
        mid = item.get("mid")
        if not isinstance(mid, dict):
            raise ValueError("midpoint candle missing mid object")
        out.append(
            ParsedCandle(
                time=parse_utc(str(item["time"])),
                complete=bool(item.get("complete", False)),
                volume=int(item.get("volume", 0)),
                open=float(mid["o"]),
                high=float(mid["h"]),
                low=float(mid["l"]),
                close=float(mid["c"]),
            )
        )
    return out
