from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from .path_guard import ensure_within_root


def build_artifact_index(root: Path, artifact_paths: Iterable[Path]) -> dict:
    root_resolved = root.resolve()
    rows = []
    for path in sorted((Path(p) for p in artifact_paths), key=lambda p: str(p)):
        safe = ensure_within_root(root_resolved, path)
        if not safe.is_file():
            raise ValueError(f"artifact is not a file: {safe}")
        data = safe.read_bytes()
        rows.append(
            {
                "path": safe.relative_to(root_resolved).as_posix(),
                "bytes": len(data),
                "sha256": sha256(data).hexdigest(),
            }
        )

    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "algorithm": "sha256",
        "artifact_count": len(rows),
        "artifacts": rows,
        "index_sha256": sha256(canonical).hexdigest(),
    }
