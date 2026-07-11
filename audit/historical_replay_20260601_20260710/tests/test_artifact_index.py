from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.artifact_index import (
    build_artifact_index,
)


def test_artifact_index_is_deterministic(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"alpha")
    b.write_bytes(b"beta")

    first = build_artifact_index(tmp_path, [b, a])
    second = build_artifact_index(tmp_path, [a, b])

    assert first == second
    assert first["artifact_count"] == 2
    assert [row["path"] for row in first["artifacts"]] == ["a.bin", "b.bin"]


def test_artifact_index_rejects_outside_root(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"x")

    with pytest.raises(ValueError):
        build_artifact_index(root, [outside])
