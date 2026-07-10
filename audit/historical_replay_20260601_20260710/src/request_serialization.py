from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlencode

ALLOWED_INSTRUMENTS = {"EUR_USD", "GBP_USD"}
ALLOWED_GRANULARITIES = {"M15", "H1", "H4", "D"}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _utc_z(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def serialize_chunk_request(
    *,
    instrument: str,
    granularity: str,
    start: datetime,
    end: datetime,
    price: str = "M",
) -> dict[str, Any]:
    """Serialize one explicit half-open OANDA candles request without count."""
    instrument = instrument.upper()
    granularity = granularity.upper()
    if instrument not in ALLOWED_INSTRUMENTS:
        raise ValueError("unsupported instrument")
    if granularity not in ALLOWED_GRANULARITIES:
        raise ValueError("unsupported granularity")
    if price != "M":
        raise ValueError("historical replay requires midpoint price=M")

    start_utc = _utc(start)
    end_utc = _utc(end)
    if end_utc <= start_utc:
        raise ValueError("end must be after start")

    params = {
        "from": _utc_z(start_utc),
        "to": _utc_z(end_utc),
        "granularity": granularity,
        "price": price,
    }
    path = f"/v3/instruments/{instrument}/candles"
    return {
        "method": "GET",
        "path": path,
        "params": params,
        "url": f"{path}?{urlencode(params)}",
    }


def serialize_planned_chunk(
    chunk: Any, *, instrument: str, granularity: str
) -> dict[str, Any]:
    """Accept a mapping or dataclass exposing start/end fields."""
    if is_dataclass(chunk):
        chunk = asdict(chunk)
    if not isinstance(chunk, Mapping):
        raise TypeError("chunk must be a mapping or dataclass")
    start = chunk.get("start") or chunk.get("start_utc")
    end = chunk.get("end") or chunk.get("end_utc")
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise ValueError("chunk start/end must be datetimes")
    return serialize_chunk_request(
        instrument=instrument,
        granularity=granularity,
        start=start,
        end=end,
    )
