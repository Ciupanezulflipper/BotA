from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Iterable

from .chunk_plan import iso_z, plan_chunks
from .request_serialization import serialize_planned_chunk

UTC = timezone.utc
_ALLOWED_INSTRUMENTS = ("EUR_USD", "GBP_USD")
_ALLOWED_GRANULARITIES = ("M15", "H1", "H4", "D")


def _parse_utc(value: str) -> datetime:
    raw = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def build_acquisition_plan(
    *,
    start_utc: datetime,
    end_utc: datetime,
    instruments: Iterable[str] = _ALLOWED_INSTRUMENTS,
    granularities: Iterable[str] = _ALLOWED_GRANULARITIES,
    max_candles: int = 5000,
) -> dict:
    normalized_instruments = tuple(str(item).upper() for item in instruments)
    normalized_granularities = tuple(str(item).upper() for item in granularities)
    if not normalized_instruments or any(item not in _ALLOWED_INSTRUMENTS for item in normalized_instruments):
        raise ValueError("unsupported acquisition instrument set")
    if not normalized_granularities or any(item not in _ALLOWED_GRANULARITIES for item in normalized_granularities):
        raise ValueError("unsupported acquisition granularity set")

    requests: list[dict] = []
    for instrument in normalized_instruments:
        for granularity in normalized_granularities:
            for index, chunk in enumerate(
                plan_chunks(
                    start_utc=start_utc,
                    end_utc=end_utc,
                    granularity=granularity,
                    max_candles=max_candles,
                )
            ):
                request = serialize_planned_chunk(
                    chunk,
                    instrument=instrument,
                    granularity=granularity,
                )
                requests.append(
                    {
                        "instrument": instrument,
                        "granularity": granularity,
                        "chunk_index": index,
                        "start_utc": iso_z(chunk.start_utc),
                        "end_utc": iso_z(chunk.end_utc),
                        "expected_max_candles": chunk.expected_max_candles,
                        "method": request["method"],
                        "path_and_query": request["url"],
                    }
                )

    payload = {
        "schema_version": 1,
        "mode": "dry_run_no_network",
        "interval": {
            "semantics": "half_open",
            "start_utc": iso_z(start_utc),
            "end_utc": iso_z(end_utc),
        },
        "instruments": list(normalized_instruments),
        "granularities": list(normalized_granularities),
        "max_candles_per_chunk": max_candles,
        "request_count": len(requests),
        "requests": requests,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["plan_sha256"] = sha256(canonical).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a no-network OANDA acquisition plan")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--max-candles", type=int, default=5000)
    args = parser.parse_args()
    plan = build_acquisition_plan(
        start_utc=_parse_utc(args.start),
        end_utc=_parse_utc(args.end),
        max_candles=args.max_candles,
    )
    print(json.dumps(plan, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
