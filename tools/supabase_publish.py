#!/usr/bin/env python3
"""Publish a BotA signal to the ProfitLab Supabase dashboard.

Uses only the Python standard library. Publication is serialized locally so the
legacy watcher path and the independent ProfitLab worker cannot race each other.
"""
from __future__ import annotations

import argparse
import fcntl
import http.client
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SUPABASE_HOST = "ozgkeslgjqbqfewojnmr.supabase.co"


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
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


def active_signal_exists(pair: str, key: str) -> bool | None:
    """Return active-state truth, or None if the dedup query failed."""
    path = (
        "/rest/v1/signals"
        f"?status=eq.ACTIVE&pair=eq.{pair.upper()}&select=id"
    )
    connection = http.client.HTTPSConnection(SUPABASE_HOST, timeout=10)
    try:
        connection.request("GET", path, headers=auth_headers(key))
        response = connection.getresponse()
        body = response.read()
        if not 200 <= response.status < 300:
            print(
                f"[supabase_publish] dedup HTTP {response.status}",
                file=sys.stderr,
            )
            return None
        rows = json.loads(body.decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException) as exc:
        print(
            f"[supabase_publish] dedup check failed: {type(exc).__name__}",
            file=sys.stderr,
        )
        return None
    finally:
        connection.close()

    if rows:
        print(
            f"[supabase_publish] SKIP {pair.upper()} — "
            f"{len(rows)} ACTIVE signal(s) already open",
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
        print(
            f"[supabase_publish] HTTP {response.status}: {body[:200]}",
            file=sys.stderr,
        )
        return False
    except (OSError, http.client.HTTPException) as exc:
        print(
            f"[supabase_publish] publish failed: {type(exc).__name__}",
            file=sys.stderr,
        )
        return False
    finally:
        connection.close()


def publish(pair, direction, entry, sl, tp, score, tf, tier) -> bool:
    tier = str(tier).upper()
    if tier != "GREEN":
        print(
            f"[supabase_publish] SKIP non-GREEN tier={tier} — "
            "only GREEN publishes ACTIVE signals",
            file=sys.stderr,
        )
        return True

    key = service_key()
    if not key:
        print("[supabase_publish] SUPABASE_SERVICE_KEY not set", file=sys.stderr)
        return False

    with publication_lock():
        active = active_signal_exists(pair, key)
        if active is None:
            return False
        if active:
            return True

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
            return False

        print(
            f"[supabase_publish] published {pair} {direction} entry={entry}",
            file=sys.stderr,
        )
        return True


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
    ok = publish(
        args.pair,
        args.direction,
        args.entry,
        args.sl,
        args.tp,
        args.score,
        args.tf,
        args.tier,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
