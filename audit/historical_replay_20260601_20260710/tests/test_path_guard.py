from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.path_guard import PathGuardError, assert_safe_output


def test_allows_output_under_root(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    root.mkdir()
    target = assert_safe_output(root, Path("evidence/result.json"))
    assert target == root / "evidence" / "result.json"


def test_rejects_escape(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    root.mkdir()
    with pytest.raises(PathGuardError):
        assert_safe_output(root, Path("../production.txt"))


def test_rejects_symlink_component(tmp_path: Path) -> None:
    root = tmp_path / "audit"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PathGuardError):
        assert_safe_output(root, Path("link/result.json"))
