#!/usr/bin/env python3
"""Publish a BotA signal to the ProfitLab Supabase dashboard.

Uses only the Python standard library. Publication is serialized locally so the
legacy watcher path and the independent ProfitLab worker cannot race each other.
When ``BOTA_SUPABASE_RESULT_LOG`` is inherited from a watcher cycle, one
structured result is appended for exact cycle reconciliation.
"""
from __future__ import annotations

import argparse
import fcntl
import http.client
import json
import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SUPABASE_HOST = "ozgkeslgjqbqfewojnmr.supabase.co"
RESULT_LOG_ENV = "BOTA_SUPABASE_RESULT_LOG"
RESULT_LOG_PREFIX = "watcher_supabase."
RESULT_LOG_SUFFIX = ".jsonl"


def service_key() -> str:
    return os.environ.get("SUPABASE_SERVICE_KEY", "")


def root_path() -> Path:
    return Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()


@contextmanager
def publication_lock() -> Iterator[None]:
    lock_path = root_path() / "state" / "supabase_publish.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def score_to_strength(score: int) -> int:
    if score >= 85:
        return 5
    if score >= 70:
        return 4
    if score >= 55:
        return 3
    if score >= 40:
        return 2
    return 1


def auth_headers(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def active_signal_exists(pair: str, key: str) -> bool | None:
    """Return active-state truth, or None if the dedup query failed."""
    path = "/rest/v1/signals" f"?status=eq.ACTIVE&pair=eq.{pair.upper()}&select=id"
    connection = http.client.HTTPSConnection(SUPABASE_HOST, timeout=10)
    try:
        connection.request("GET", path, headers=auth_headers(key))
        response = connection.getresponse()
        body = response.read()
        if not 200 <= response.status < 300:
            print(f"[supabase_publish] dedup HTTP {response.status}", file=sys.stderr)
            return None
        rows = json.loads(body.decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException) as exc:
        print(f"[supabase_publish] dedup check failed: {type(exc).__name__}", file=sys.stderr)
        return None
    finally:
        connection.close()

    if rows:
        print(
            f"[supabase_publish] SKIP {pair.upper()} — {len(rows)} ACTIVE signal(s) already open",
            file=sys.stderr,
        )
        return True
    return False


def insert_signal(payload: dict[str, object], key: str) -> bool:
    data = json.dumps(payload).encode("utf-8")
    headers = {
        **auth_headers(key),
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    connection = http.client.HTTPSConnection(SUPABASE_HOST, timeout=10)
    try:
        connection.request("POST", "/rest/v1/signals", body=data, headers=headers)
        response = connection.getresponse()
        body = response.read().decode("utf-8", "replace")
        if 200 <= response.status < 300:
            return True
        print(f"[supabase_publish] HTTP {response.status}: {body[:200]}", file=sys.stderr)
        return False
    except (OSError, http.client.HTTPException) as exc:
        print(f"[supabase_publish] publish failed: {type(exc).__name__}", file=sys.stderr)
        return False
    finally:
        connection.close()


def publish_with_status(pair, direction, entry, sl, tp, score, tf, tier) -> tuple[bool, str]:
    tier = str(tier).upper()
    if tier != "GREEN":
        print(
            f"[supabase_publish] SKIP non-GREEN tier={tier} — only GREEN publishes ACTIVE signals",
            file=sys.stderr,
        )
        return True, "skipped_non_green"

    key = service_key()
    if not key:
        print("[supabase_publish] SUPABASE_SERVICE_KEY not set", file=sys.stderr)
        return False, "failed_missing_service_key"

    with publication_lock():
        active = active_signal_exists(pair, key)
        if active is None:
            return False, "failed_dedup_check"
        if active:
            return True, "skipped_active_exists"

        payload = {
            "pair": pair.upper(),
            "direction": direction.upper(),
            "entry_price": float(entry),
            "stop_loss": float(sl),
            "take_profit": float(tp),
            "signal_strength": score_to_strength(int(score)),
            "status": "ACTIVE",
            "timeframe": tf.upper(),
            "min_tier": "pro",
            "rationale": f"BotA score={score} tier={tier}",
        }
        if not insert_signal(payload, key):
            return False, "failed_publish"

        print(f"[supabase_publish] published {pair} {direction} entry={entry}", file=sys.stderr)
        return True, "published"


def publish(pair, direction, entry, sl, tp, score, tf, tier) -> bool:
    """Backward-compatible boolean publication API used by existing callers/tests."""
    ok, _status = publish_with_status(pair, direction, entry, sl, tp, score, tf, tier)
    return ok


def cycle_result_path() -> Path | None:
    """Validate the watcher-owned evidence path before allowing any append."""
    raw_path = os.environ.get(RESULT_LOG_ENV, "").strip()
    if not raw_path:
        return None
    try:
        path = Path(raw_path).expanduser().resolve(strict=True)
        state_dir = (root_path() / "state").resolve(strict=True)
        info = path.stat()
    except OSError as exc:
        print(f"[supabase_publish] invalid cycle evidence path: {type(exc).__name__}", file=sys.stderr)
        return Path()
    if (
        path.parent != state_dir
        or not path.name.startswith(RESULT_LOG_PREFIX)
        or not path.name.endswith(RESULT_LOG_SUFFIX)
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        print("[supabase_publish] invalid cycle evidence path ownership", file=sys.stderr)
        return Path()
    return path


def emit_cycle_result(*, pair: str, direction: str, entry: str, tf: str, tier: str, status: str) -> bool:
    """Append one sanitized result to the validated watcher-owned evidence file."""
    path = cycle_result_path()
    if path is None:
        return True
    if not str(path):
        return False
    payload = {
        "schema_version": "1.0",
        "pair": pair.upper(),
        "timeframe": tf.upper(),
        "direction": direction.upper(),
        "entry": str(entry),
        "tier": tier.upper(),
        "status": status,
    }
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        return True
    except OSError as exc:
        print(f"[supabase_publish] cycle evidence write failed: {type(exc).__name__}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True)
    parser.add_argument("--direction", required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--sl", required=True)
    parser.add_argument("--tp", required=True)
    parser.add_argument("--score", required=True)
    parser.add_argument("--tf", required=True)
    parser.add_argument("--tier", default="GREEN")
    args = parser.parse_args()
    ok, status = publish_with_status(
        args.pair, args.direction, args.entry, args.sl, args.tp, args.score, args.tf, args.tier
    )
    evidence_ok = emit_cycle_result(
        pair=args.pair,
        direction=args.direction,
        entry=args.entry,
        tf=args.tf,
        tier=args.tier,
        status=status,
    )
    return 0 if ok and evidence_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
