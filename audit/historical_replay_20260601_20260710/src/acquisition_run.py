from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Mapping

from .artifact_index import build_artifact_index
from .oanda_payload import parse_oanda_mid_candles
from .raw_artifact import write_once
from .request_metadata import build_request_metadata
from .response_metadata import capture_response_metadata
from .run_manifest import write_run_manifest


def execute_synthetic_acquisition(
    *,
    root: Path,
    run_id: str,
    request_url: str,
    request_headers: Mapping[str, str],
    response_status: int,
    response_headers: Mapping[str, str],
    response_body: bytes,
) -> dict:
    """Persist and verify one synthetic provider acquisition without network access."""
    root = root.resolve()

    request_meta = build_request_metadata(
        method="GET",
        url=request_url,
        headers=request_headers,
    )
    response_meta = capture_response_metadata(response_status, response_headers)

    payload = json.loads(response_body.decode("utf-8"))
    candles = parse_oanda_mid_candles(payload)

    raw = write_once(root, f"raw/{run_id}/response.json", response_body)
    request_doc = json.dumps(asdict(request_meta), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    response_doc = json.dumps(asdict(response_meta), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    candle_doc = json.dumps(candles, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"

    req_artifact = write_once(root, f"metadata/{run_id}/request.json", request_doc)
    resp_artifact = write_once(root, f"metadata/{run_id}/response.json", response_doc)
    parsed_artifact = write_once(root, f"derived/{run_id}/candles.json", candle_doc)

    artifact_paths = [
        root / raw.relative_path,
        root / req_artifact.relative_path,
        root / resp_artifact.relative_path,
        root / parsed_artifact.relative_path,
    ]
    index = build_artifact_index(root, artifact_paths)

    manifest_payload = {
        "provider": "oanda",
        "mode": "synthetic",
        "request": asdict(request_meta),
        "response": asdict(response_meta),
        "candle_count": len(candles),
        "artifacts": index,
    }
    manifest_path = write_run_manifest(root, run_id, manifest_payload)

    return {
        "run_id": run_id,
        "manifest_path": str(manifest_path.relative_to(root)),
        "candle_count": len(candles),
        "artifacts": index,
    }
