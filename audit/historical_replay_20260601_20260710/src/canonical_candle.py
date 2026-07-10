from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class CanonicalCandle:
    provider: str
    instrument: str
    granularity: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    complete: bool

    def to_json(self) -> dict:
        return {
            "provider": self.provider,
            "instrument": self.instrument,
            "granularity": self.granularity,
            "time": self.time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "complete": self.complete,
        }


_ALLOWED_PROVIDERS = {"oanda", "dukascopy"}
_ALLOWED_INSTRUMENTS = {"EURUSD", "GBPUSD"}
_ALLOWED_GRANULARITIES = {"M15", "H1", "H4", "D1"}


def normalize_provider_rows(
    rows: Iterable[object],
    *,
    provider: str,
    instrument: str,
    granularity: str,
    default_complete: bool,
) -> list[CanonicalCandle]:
    provider_key = provider.strip().lower()
    instrument_key = instrument.replace("_", "").upper()
    granularity_key = "D1" if granularity.upper() == "D" else granularity.upper()
    if provider_key not in _ALLOWED_PROVIDERS:
        raise ValueError("unsupported provider")
    if instrument_key not in _ALLOWED_INSTRUMENTS:
        raise ValueError("unsupported instrument")
    if granularity_key not in _ALLOWED_GRANULARITIES:
        raise ValueError("unsupported granularity")

    normalized: list[CanonicalCandle] = []
    previous: datetime | None = None
    for row in rows:
        stamp = getattr(row, "time", None)
        if not isinstance(stamp, datetime) or stamp.tzinfo is None:
            raise ValueError("provider row requires timezone-aware datetime .time")
        stamp = stamp.astimezone(timezone.utc)
        values = {
            field: float(getattr(row, field))
            for field in ("open", "high", "low", "close")
        }
        volume = float(getattr(row, "volume", 0.0))
        if not all(isfinite(value) and value > 0 for value in values.values()):
            raise ValueError("OHLC values must be finite and positive")
        if not isfinite(volume) or volume < 0:
            raise ValueError("volume must be finite and non-negative")
        if values["high"] < max(values["open"], values["close"]):
            raise ValueError("high below candle body")
        if values["low"] > min(values["open"], values["close"]):
            raise ValueError("low above candle body")
        if values["low"] > values["high"]:
            raise ValueError("low exceeds high")
        if previous is not None and stamp <= previous:
            raise ValueError("canonical timestamps must be strictly increasing")
        previous = stamp
        complete = bool(getattr(row, "complete", default_complete))
        normalized.append(
            CanonicalCandle(
                provider=provider_key,
                instrument=instrument_key,
                granularity=granularity_key,
                time=stamp,
                open=values["open"],
                high=values["high"],
                low=values["low"],
                close=values["close"],
                volume=volume,
                complete=complete,
            )
        )
    if not normalized:
        raise ValueError("provider rows are empty")
    return normalized
