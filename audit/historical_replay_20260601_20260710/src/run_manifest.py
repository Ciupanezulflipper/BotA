from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .path_guard import ensure_within_root


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def write_run_manifest(root: Path, run_id: str, payload: dict[str, Any]) -> Path:
    if not run_id or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_." for ch in run_id):
        raise ValueError("unsafe run_id")
    root = root.resolve()
    target = ensure_within_root(root, root / "manifests" / f"{run_id}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite run manifest: {target}")
    doc = {
        "schema_version": 1,
        "run_id": run_id,
        "created_utc": utc_now_iso(),
        **payload,
    }
    target.write_bytes(canonical_json_bytes(doc))
    return target
