from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .path_guard import ensure_within_root


def _canonical_index_hash(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(canonical).hexdigest()


def verify_completed_run(root: Path, run_id: str) -> dict[str, Any]:
    """Reopen a completed acquisition run and verify every stored integrity claim."""
    root = root.resolve()
    manifest_path = ensure_within_root(root, root / "manifests" / f"{run_id}.json")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != run_id:
        raise ValueError("manifest run_id mismatch")

    index = manifest.get("artifacts")
    if not isinstance(index, dict):
        raise ValueError("manifest artifacts index missing")
    rows = index.get("artifacts")
    if not isinstance(rows, list):
        raise ValueError("manifest artifacts list missing")
    if index.get("artifact_count") != len(rows):
        raise ValueError("artifact_count mismatch")
    if index.get("algorithm") != "sha256":
        raise ValueError("unsupported artifact index algorithm")

    expected_index_hash = _canonical_index_hash(rows)
    if index.get("index_sha256") != expected_index_hash:
        raise ValueError("artifact index hash mismatch")

    verified = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("artifact row must be an object")
        relative = str(row.get("path", ""))
        artifact = ensure_within_root(root, root / relative)
        if not artifact.is_file():
            raise FileNotFoundError(f"artifact missing: {relative}")
        data = artifact.read_bytes()
        actual_size = len(data)
        actual_sha = sha256(data).hexdigest()
        if row.get("bytes") != actual_size:
            raise ValueError(f"artifact size mismatch: {relative}")
        if row.get("sha256") != actual_sha:
            raise ValueError(f"artifact sha256 mismatch: {relative}")
        verified.append(relative)

    return {
        "run_id": run_id,
        "manifest": manifest_path.relative_to(root).as_posix(),
        "artifact_count": len(verified),
        "verified_artifacts": verified,
        "index_sha256": expected_index_hash,
        "status": "PASS",
    }
