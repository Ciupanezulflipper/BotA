from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .path_guard import ensure_within_root


@dataclass(frozen=True)
class RawArtifact:
    relative_path: str
    sha256: str
    size_bytes: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_once(root: Path, relative_path: str, data: bytes) -> RawArtifact:
    root = root.resolve()
    target = ensure_within_root(root, root / relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite raw artifact: {target}")
    target.write_bytes(data)
    return RawArtifact(
        relative_path=str(target.relative_to(root)),
        sha256=sha256_bytes(data),
        size_bytes=len(data),
    )
