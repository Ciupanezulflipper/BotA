import json
from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.run_manifest import write_run_manifest


def test_manifest_is_write_once_and_structured(tmp_path: Path) -> None:
    path = write_run_manifest(tmp_path, "run-001", {"provider": "oanda", "artifacts": []})
    data = json.loads(path.read_text())
    assert data["schema_version"] == 1
    assert data["run_id"] == "run-001"
    assert data["provider"] == "oanda"
    with pytest.raises(FileExistsError):
        write_run_manifest(tmp_path, "run-001", {"provider": "oanda"})


def test_manifest_rejects_unsafe_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_run_manifest(tmp_path, "../escape", {})
