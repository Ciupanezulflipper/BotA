from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .path_guard import assert_safe_output


@dataclass(frozen=True)
class ArtifactRecord:
    relative_path: str
    sha256: str
    size_bytes: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_record(root: Path, artifact: Path) -> ArtifactRecord:
    root_resolved = root.resolve(strict=True)
    artifact_resolved = artifact.resolve(strict=True)
    relative = artifact_resolved.relative_to(root_resolved)
    return ArtifactRecord(
        relative_path=relative.as_posix(),
        sha256=sha256_file(artifact_resolved),
        size_bytes=artifact_resolved.stat().st_size,
    )


def write_manifest(root: Path, records: list[ArtifactRecord], output: Path) -> Path:
    safe_output = assert_safe_output(root, output)
    safe_output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": [asdict(record) for record in sorted(records, key=lambda x: x.relative_path)],
    }
    safe_output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return safe_output
