from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DukascopyCandle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _parse_time(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("missing timestamp")
    if raw.isdigit():
        dt = datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc)
    else:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        dt = dt.astimezone(timezone.utc)
    return dt


def parse_dukascopy_csv(raw: bytes) -> list[DukascopyCandle]:
    """Parse a synthetic Dukascopy-style CSV export into UTC candles.

    Accepted headers are case-insensitive aliases for time/open/high/low/close/volume.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Dukascopy fixture must be UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV header missing")
    aliases = {name.strip().lower(): name for name in reader.fieldnames}
    required = {"time", "open", "high", "low", "close"}
    if not required.issubset(aliases):
        raise ValueError("CSV missing required OHLC columns")

    out: list[DukascopyCandle] = []
    previous: datetime | None = None
    for row in reader:
        candle = DukascopyCandle(
            time=_parse_time(row[aliases["time"]]),
            open=float(row[aliases["open"]]),
            high=float(row[aliases["high"]]),
            low=float(row[aliases["low"]]),
            close=float(row[aliases["close"]]),
            volume=float(row[aliases["volume"]]) if "volume" in aliases and row[aliases["volume"]] else 0.0,
        )
        if candle.high < max(candle.open, candle.close) or candle.low > min(candle.open, candle.close):
            raise ValueError("invalid OHLC envelope")
        if candle.low > candle.high:
            raise ValueError("low exceeds high")
        if previous is not None and candle.time <= previous:
            raise ValueError("timestamps must be strictly increasing")
        previous = candle.time
        out.append(candle)

    if not out:
        raise ValueError("CSV contains no candles")
    return out
