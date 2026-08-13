#!/usr/bin/env python3
"""Recover only an incomplete Telegram->Supabase watcher transaction.

A confirmed Telegram text is durable in state/telegram_delivery before the
outer watcher publishes to Supabase.  The legacy cooldown/hash pair is the
commit marker for the *whole* delivery transaction.  If the newest confirmed
Telegram state for a pair/timeframe does not match the committed legacy hash,
its cooldown must not suppress the retry cycle.  Remove only that cooldown;
never alter Telegram authoritative state or the committed hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

MAX_STATE_BYTES = 131_072


def root_path() -> Path:
    return Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()


def legacy_hash(identity: dict[str, Any]) -> str:
    keys = ("pair", "timeframe", "direction", "score", "entry", "sl", "tp")
    values = [str(identity.get(key) or "").strip() for key in keys]
    if any(not value for value in values):
        raise ValueError("telegram_state_identity_incomplete")
    raw = "|".join(values)
    return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()


def read_regular_json(path: Path) -> dict[str, Any]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STATE_BYTES:
        raise ValueError("telegram_state_file_invalid")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("telegram_state_json_invalid")
    return value


def main() -> int:
    root = root_path()
    expected_delivery = (root / "logs" / "state").resolve()
    raw_delivery = os.environ.get("BOTA_DELIVERY_STATE_DIR", "").strip()
    if not raw_delivery:
        print("[WATCHER_RECOVERY] delivery_state_dir_missing", file=sys.stderr)
        return 64
    try:
        delivery_dir = Path(raw_delivery).expanduser().resolve(strict=True)
    except OSError:
        print("[WATCHER_RECOVERY] delivery_state_dir_invalid", file=sys.stderr)
        return 64
    if delivery_dir != expected_delivery:
        print("[WATCHER_RECOVERY] delivery_state_dir_mismatch", file=sys.stderr)
        return 64

    telegram_dir = root / "state" / "telegram_delivery"
    if not telegram_dir.exists():
        return 0
    try:
        if telegram_dir.is_symlink() or not telegram_dir.is_dir():
            raise ValueError("telegram_state_dir_invalid")

        latest: dict[tuple[str, str], tuple[tuple[int, int, int], str]] = {}
        for path in telegram_dir.glob("*.json"):
            value = read_regular_json(path)
            if str(value.get("status") or "") != "sent":
                continue
            identity = value.get("identity")
            if not isinstance(identity, dict):
                raise ValueError("telegram_state_identity_invalid")
            pair = str(identity.get("pair") or "").upper().strip()
            tf = str(identity.get("timeframe") or "").upper().strip()
            if not pair or not tf:
                raise ValueError("telegram_state_scope_missing")
            expected_hash = legacy_hash(identity)
            rank = (
                int(value.get("server_epoch") or 0),
                int(value.get("monotonic_ns") or 0),
                int(path.stat().st_mtime_ns),
            )
            scope = (pair, tf)
            if scope not in latest or rank > latest[scope][0]:
                latest[scope] = (rank, expected_hash)

        changed = False
        for (pair, tf), (_rank, expected_hash) in latest.items():
            hash_path = delivery_dir / f"last_hash_{pair}_{tf}.txt"
            cooldown_path = delivery_dir / f"last_sent_{pair}_{tf}.txt"
            committed_hash = ""
            if hash_path.exists():
                if hash_path.is_symlink() or not hash_path.is_file():
                    raise ValueError("legacy_hash_file_invalid")
                committed_hash = hash_path.read_text(encoding="utf-8").strip()
            if committed_hash == expected_hash:
                continue
            if cooldown_path.exists():
                if cooldown_path.is_symlink() or not cooldown_path.is_file():
                    raise ValueError("legacy_cooldown_file_invalid")
                cooldown_path.unlink()
                changed = True
                print(
                    f"[WATCHER_RECOVERY] cleared_pending_cooldown scope={pair}:{tf}",
                    file=sys.stderr,
                )
        if changed:
            fd = os.open(str(delivery_dir), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"[WATCHER_RECOVERY] fail_closed {type(exc).__name__}", file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
