from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from .artifact_index import build_artifact_index
from .boundary_reconciliation import reconcile_chunk_candles
from .chunk_plan import plan_chunks
from .live_oanda import fetch_oanda_chunk
from .oanda_payload import parse_oanda_mid_payload
from .raw_artifact import write_once
from .request_serialization import serialize_planned_chunk
from .run_manifest import write_run_manifest

Fetcher = Callable[..., dict]


def _candle_row(candle) -> dict:
    row = asdict(candle)
    row["time"] = candle.time.isoformat().replace("+00:00", "Z")
    return row


def acquire_oanda_range(
    *,
    output_root: Path,
    run_id: str,
    instrument: str,
    granularity: str,
    start_utc,
    end_utc,
    token: str,
    enabled: bool = False,
    base_url: str = "https://api-fxpractice.oanda.com",
    timeout_seconds: float = 30.0,
    fetcher: Fetcher = fetch_oanda_chunk,
) -> dict:
    """Acquire, persist, reconcile, and manifest one bounded OANDA range.

    Network access remains fail-closed because every delegated chunk fetch still
    requires enabled=True and an explicit token. Tests may inject a synthetic
    fetcher without touching the network.
    """
    root = output_root.resolve()
    chunks = plan_chunks(
        start_utc=start_utc,
        end_utc=end_utc,
        granularity=granularity,
    )

    chunk_candles: list[list[dict]] = []
    artifact_paths: list[Path] = []
    chunk_records: list[dict] = []

    for index, chunk in enumerate(chunks):
        request = serialize_planned_chunk(
            chunk,
            instrument=instrument,
            granularity=granularity,
        )
        result = fetcher(
            output_root=root,
            request_path_and_query=request["url"],
            token=token,
            enabled=enabled,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        raw_body = result["body"]
        parsed = parse_oanda_mid_payload(raw_body)
        rows = [_candle_row(candle) for candle in parsed]
        chunk_candles.append(rows)

        chunk_id = f"chunk-{index:04d}"
        raw = write_once(root, f"raw/{run_id}/{chunk_id}.json", raw_body)
        request_doc = json.dumps(
            asdict(result["request"]), sort_keys=True, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        response_doc = json.dumps(
            asdict(result["response"]), sort_keys=True, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        req = write_once(root, f"metadata/{run_id}/{chunk_id}.request.json", request_doc)
        resp = write_once(root, f"metadata/{run_id}/{chunk_id}.response.json", response_doc)
        artifact_paths.extend(
            [root / raw.relative_path, root / req.relative_path, root / resp.relative_path]
        )
        chunk_records.append(
            {
                "chunk": chunk_id,
                "start_utc": chunk.start_utc.isoformat().replace("+00:00", "Z"),
                "end_utc": chunk.end_utc.isoformat().replace("+00:00", "Z"),
                "expected_max_candles": chunk.expected_max_candles,
                "returned_candles": len(rows),
                "request_id": result["response"].request_id,
            }
        )

    reconciled = reconcile_chunk_candles(chunk_candles)
    derived_doc = json.dumps(
        reconciled, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8") + b"\n"
    derived = write_once(root, f"derived/{run_id}/candles.json", derived_doc)
    artifact_paths.append(root / derived.relative_path)

    index = build_artifact_index(root, artifact_paths)
    manifest = write_run_manifest(
        root,
        run_id,
        {
            "provider": "oanda",
            "mode": "live" if enabled else "synthetic",
            "instrument": instrument,
            "granularity": granularity,
            "range_start_utc": start_utc.isoformat().replace("+00:00", "Z"),
            "range_end_utc": end_utc.isoformat().replace("+00:00", "Z"),
            "chunks": chunk_records,
            "reconciled_candle_count": len(reconciled),
            "artifacts": index,
        },
    )
    return {
        "run_id": run_id,
        "manifest_path": manifest.relative_to(root).as_posix(),
        "chunk_count": len(chunks),
        "reconciled_candle_count": len(reconciled),
        "artifacts": index,
    }
