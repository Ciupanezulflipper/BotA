from pathlib import Path

import pytest

from audit.historical_replay_20260601_20260710.src.raw_artifact import write_once


def test_write_once_creates_hashed_artifact(tmp_path: Path) -> None:
    item = write_once(tmp_path, "raw/oanda/sample.json", b"abc")
    assert item.relative_path == "raw/oanda/sample.json"
    assert item.size_bytes == 3
    assert item.sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_write_once_refuses_overwrite(tmp_path: Path) -> None:
    write_once(tmp_path, "raw/item.bin", b"one")
    with pytest.raises(FileExistsError):
        write_once(tmp_path, "raw/item.bin", b"two")
