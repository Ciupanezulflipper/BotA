#!/usr/bin/env python3
"""Independent, crash-consistent Telegram closure notifier for BotA signals.

The signal lifecycle has two independent user-visible sinks, mirroring the
qualified-signal fan-out:

    SL/TP result
       +----+------------------+
       |                       |
       v                       v
    Telegram closure        ProfitLab status/result

``tools/signal_closer.py`` owns the ProfitLab/Supabase lifecycle update
(status=CLOSED/CANCELLED, result_pips). This module owns the Telegram
closure message only. Neither sink may block or be reverted by the other:
the Supabase PATCH already happened (or was attempted and logged) by the
time this module runs, and a Telegram failure here never re-opens or
re-writes the Supabase row. Conversely a Supabase failure never suppresses
this Telegram attempt.

Per-signal-id durable state prevents a duplicate Telegram closure message
on watcher/cron restart or retry: once a signal_id is durably marked
"sent", every subsequent call for that same signal_id is a no-op.

The state file also doubles as a safe retry outbox. If Supabase already
closed the row but this module could not confirm a Telegram send (missing
credentials, or a definite HTTP rejection), the non-secret closure payload
(signal_id, pair, direction, closure_status, result_pips, entry) is kept
durably in a retryable status so ``retry_pending_closures()`` can resend it
on a later run without requiring the signal to still be ACTIVE in Supabase.
An "unknown_outcome" (indeterminate network/response state) is never
retried automatically, since a duplicate send cannot be ruled out.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

RETRYABLE_STATUSES = frozenset({"definite_failure", "missing_credentials"})


def mutable_root() -> Path:
    value = os.environ.get("BOTA_MUTABLE_ROOT", "").strip()
    if not value:
        value = os.environ.get("BOTA_ROOT", "").strip()
    return Path(value or Path.home() / "BotA").expanduser().resolve()


def _state_dir() -> Path:
    directory = mutable_root() / "state" / "telegram_closure"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def state_path(signal_id: str) -> Path:
    return _state_dir() / f"{signal_id}.json"


def _lock_path(signal_id: str) -> Path:
    return _state_dir() / f"{signal_id}.lock"


@contextlib.contextmanager
def _signal_lock(signal_id: str) -> Iterator[None]:
    """Serialize read-state/intent/send/state-transition per signal_id.

    Uses a dedicated lock file (not the state JSON itself) so a crash mid
    write never leaves a stale exclusive lock baked into the state file's
    own lifecycle. flock() is scoped to the open file description, so two
    independent open() calls -- from separate threads or separate closer
    invocations -- block each other even within the same process.
    """
    lock_path = _lock_path(signal_id)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_json_durable(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write, then fsync both the file and its containing directory.

    A bare os.replace() is only durable once the directory entry pointing at
    the new inode survives a crash; without an explicit directory fsync, a
    host crash right after a successful Telegram send can lose the rename
    and resurrect the pre-send "intent"/retryable state on restart, risking
    a duplicate closure message. Both the intent and terminal-state writes
    go through this helper, so both transitions are crash durable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
    dir_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _read_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"status": "unknown_outcome", "reason": "state_unreadable"}
    return value if isinstance(value, dict) else {"status": "unknown_outcome", "reason": "state_invalid"}


def format_closure_message(pair: str, direction: str, status: str, result_pips: float, entry: float) -> str:
    outcome_emoji = {"CLOSED": "✅" if result_pips >= 0 else "\U0001f534", "CANCELLED": "⚪"}
    emoji = outcome_emoji.get(status, "⚪")
    if status == "CANCELLED":
        return (
            f"{emoji} BotA {pair} {direction} CANCELLED\n"
            f"━━━━━━━━━━━━━━\n"
            f"Entry: {entry}\nNo TP/SL hit before max age."
        )
    return (
        f"{emoji} BotA {pair} {direction} CLOSED\n"
        f"━━━━━━━━━━━━━━\n"
        f"Entry: {entry}\nResult: {result_pips:+.1f} pips"
    )


def _telegram_credentials() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or ""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID") or ""
    return token, chat_id


def _send_request(message: str, token: str, chat_id: str) -> tuple[str, dict[str, Any]]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        try:
            exc.read()
        except Exception:
            pass
        if 400 <= int(exc.code) < 500:
            return "definite_failure", {"http_status": int(exc.code)}
        return "unknown_outcome", {"http_status": int(exc.code)}
    except OSError:
        return "unknown_outcome", {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except ValueError:
        return "unknown_outcome", {}
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return "unknown_outcome", {}
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
        return "unknown_outcome", {}
    return "sent", {"message_id": result["message_id"]}


def send_closure(
    signal_id: str,
    pair: str,
    direction: str,
    status: str,
    result_pips: float,
    entry: float,
) -> bool:
    """Attempt exactly one durable Telegram closure notification per signal_id.

    Returns True only when this signal_id's closure is durably confirmed sent
    (including a prior confirmed send being reconciled). Returns False on any
    other outcome (missing credentials, failure, or an unresolved prior
    attempt that must not be blindly resent). Never raises: a Telegram
    problem here must never propagate into the caller's Supabase lifecycle
    update.

    The Supabase row may already be CLOSED by the time this fails, so every
    non-terminal outcome durably persists the closure payload (no secrets)
    under a retryable status. retry_pending_closures() is the only other
    caller allowed to resend from that durable state.
    """
    payload = {"signal_id": signal_id, "pair": pair, "direction": direction,
               "closure_status": status, "result_pips": result_pips, "entry": entry}
    try:
        with _signal_lock(signal_id):
            path = state_path(signal_id)
            prior = _read_state(path)
            if prior:
                prior_status = str(prior.get("status", ""))
                if prior_status == "sent":
                    return True
                if prior_status in {"intent", "unknown_outcome"}:
                    print(
                        f"[telegram_closure] BLOCK signal_id={signal_id} unknown_outcome_no_blind_resend",
                        file=sys.stderr,
                    )
                    return False

            token, chat_id = _telegram_credentials()
            if not token or not chat_id:
                _write_json_durable(path, {**payload, "status": "missing_credentials"})
                print(f"[telegram_closure] SKIP signal_id={signal_id} credentials_missing", file=sys.stderr)
                return False

            message = format_closure_message(pair, direction, status, result_pips, entry)
            _write_json_durable(path, {**payload, "status": "intent"})

            outcome, detail = _send_request(message, token, chat_id)
            if outcome == "sent":
                _write_json_durable(path, {**payload, **detail, "status": "sent"})
                print(f"[telegram_closure] SENT signal_id={signal_id} message_id={detail['message_id']}",
                      file=sys.stderr)
                return True
            if outcome == "definite_failure":
                _write_json_durable(path, {**payload, **detail, "status": "definite_failure"})
                print(f"[telegram_closure] FAILED signal_id={signal_id} definite_rejection", file=sys.stderr)
                return False
            _write_json_durable(path, {**payload, **detail, "status": "unknown_outcome"})
            print(f"[telegram_closure] UNKNOWN_OUTCOME signal_id={signal_id}", file=sys.stderr)
            return False
    except Exception as exc:  # noqa: BLE001 - closure notification must never crash the caller
        print(f"[telegram_closure] ERROR signal_id={signal_id} {type(exc).__name__}", file=sys.stderr)
        return False


def retry_pending_closures() -> dict[str, int]:
    """Scan the durable outbox and retry only retryable closure states.

    Only entries whose persisted status is "definite_failure" or
    "missing_credentials" are retried -- both mean the Telegram closure
    attempt never definitely happened. "sent" is terminal and "unknown_outcome"
    (and a leftover "intent" from a crash mid-send) are deliberately never
    retried automatically since a duplicate send cannot be ruled out.

    Every file in the outbox directory is treated as untrusted input: this
    only ever resends payloads durably written by send_closure() itself, so
    malformed, unrelated, or historical files are skipped rather than raised.
    """
    summary = {"candidates": 0, "sent": 0, "skipped": 0}
    directory = _state_dir()
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            summary["skipped"] += 1
            continue
        if not isinstance(record, dict) or record.get("status") not in RETRYABLE_STATUSES:
            continue
        try:
            signal_id = str(record["signal_id"])
            pair = str(record["pair"])
            direction = str(record["direction"])
            closure_status = str(record["closure_status"])
            result_pips = float(record["result_pips"])
            entry = float(record["entry"])
        except (KeyError, TypeError, ValueError):
            summary["skipped"] += 1
            continue
        summary["candidates"] += 1
        if send_closure(signal_id, pair, direction, closure_status, result_pips, entry):
            summary["sent"] += 1
    return summary
