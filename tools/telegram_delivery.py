#!/usr/bin/env python3
"""Crash-consistent Telegram delivery boundary for BotA watcher signals.

Contract:
- Prove the matching decision row exists in the current watcher cycle's alerts.csv append segment.
- Fsync the decision journal before any network side effect.
- Persist a durable intent before the Telegram request.
- Persist authoritative Telegram confirmation (message_id/date) after ok=true.
- If a previous attempt is left in intent/unknown_outcome, never blindly resend it.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

LEGACY_FIELDS = (
    "timestamp","pair","tf","direction","score","confidence","entry","sl","tp",
    "provider","rejected","filter_str","reasons",
)
CURRENT_FIELDS = (
    "ts","pair","tf","direction","score","confidence","entry","sl","tp","provider",
    "filter_rejected","filter_reasons","reasons","ema_comp","rsi_comp","macd_comp",
    "adx_comp","adx_raw","rsi_raw","macd_hist_raw","macro6","h1_trend","tier","session",
    "adx_regime",
)
PAIR_RE = re.compile(r"\bBotA\s+([A-Z]{6})\s+([A-Z0-9]+)\s+(BUY|SELL)\b")
SCORE_RE = re.compile(r"(?:Score:\s*|score=)([0-9]+(?:\.[0-9]+)?)", re.I)
ENTRY_RE = re.compile(r"Entry:\s*([0-9]+(?:\.[0-9]+)?)", re.I)
ALERTS_OFFSET_ENV = "BOTA_ALERTS_OFFSET"


def root_path() -> Path:
    return Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))).expanduser().resolve()


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1","true","yes","y","on"}


def parse_message(message: str) -> dict[str, str]:
    identity = PAIR_RE.search(message)
    score = SCORE_RE.search(message)
    if not identity or not score:
        raise ValueError("message_identity_unparseable")
    entry = ENTRY_RE.search(message)
    return {
        "pair": identity.group(1),
        "timeframe": identity.group(2).upper(),
        "direction": identity.group(3),
        "score": score.group(1),
        "entry": entry.group(1) if entry else "",
    }


def row_dict(values: list[str]) -> dict[str, str] | None:
    if len(values) == len(CURRENT_FIELDS):
        return dict(zip(CURRENT_FIELDS, values, strict=True))
    if len(values) == len(LEGACY_FIELDS):
        return dict(zip(LEGACY_FIELDS, values, strict=True))
    return None


def decision_matches(row: dict[str, str], identity: dict[str, str]) -> bool:
    if str(row.get("pair","")).upper() != identity["pair"]:
        return False
    if str(row.get("tf", row.get("timeframe",""))).upper() != identity["timeframe"]:
        return False
    if str(row.get("direction","")).upper() != identity["direction"]:
        return False
    rejected = row.get("filter_rejected")
    if rejected is None or str(rejected).strip() == "":
        rejected = row.get("rejected")
    if truthy(rejected):
        return False
    try:
        if abs(float(row.get("score","0")) - float(identity["score"])) > 0.011:
            return False
    except (TypeError, ValueError):
        return False
    if identity["entry"]:
        try:
            if abs(float(row.get("entry","0")) - float(identity["entry"])) > 0.000001:
                return False
        except (TypeError, ValueError):
            return False
    return True


def cycle_alerts_offset() -> int:
    raw = os.environ.get(ALERTS_OFFSET_ENV, "").strip()
    if not raw or not raw.isdigit():
        raise ValueError("alerts_offset_missing_or_invalid")
    return int(raw)


def read_cycle_rows(path: Path, offset: int) -> list[list[str]]:
    size = path.stat().st_size
    if offset < 0 or offset > size:
        raise ValueError("alerts_offset_out_of_range")
    with path.open("rb") as handle:
        handle.seek(offset)
        segment = handle.read(1_048_577)
    if len(segment) > 1_048_576:
        raise ValueError("alerts_cycle_segment_too_large")
    return list(csv.reader(io.StringIO(segment.decode("utf-8", "replace"))))


def fsync_directory(directory: Path) -> None:
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_file_and_parent(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_directory(path.parent)


def prove_decision_persisted(identity: dict[str, str]) -> bool:
    path = root_path() / "logs" / "alerts.csv"
    try:
        offset = cycle_alerts_offset()
        rows = read_cycle_rows(path, offset)
    except (OSError, ValueError):
        return False
    matched = False
    for values in reversed(rows):
        row = row_dict(values)
        if row is not None and decision_matches(row, identity):
            matched = True
            break
    if not matched:
        return False
    try:
        fsync_file_and_parent(path)
    except OSError:
        return False
    return True


def delivery_key(identity: dict[str, str], chat_id: str) -> str:
    canonical = "|".join(
        [chat_id] + [identity[key] for key in ("pair","timeframe","direction","score","entry")]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def state_paths(key: str) -> tuple[Path, Path]:
    directory = root_path() / "state" / "telegram_delivery"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{key}.json", directory / f"{key}.lock"


def runtime_provenance() -> dict[str, Any]:
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        boot_id = "unknown"
    clock = getattr(time, "CLOCK_BOOTTIME", None)
    monotonic_ns = time.clock_gettime_ns(clock) if clock is not None else time.monotonic_ns()
    raw_epoch = os.environ.get("BOTA_SERVER_EPOCH", "").strip()
    server_epoch = int(raw_epoch) if raw_epoch.isdigit() and int(raw_epoch) > 1_000_000_000 else 0
    return {
        "boot_id": boot_id,
        "cycle_id": os.environ.get("BOTA_CYCLE_ID", ""),
        "monotonic_ns": monotonic_ns,
        "server_epoch": server_epoch,
    }


def write_json_durable(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",",":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        fsync_directory(path.parent)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def read_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"status": "unknown_outcome", "reason": "state_unreadable"}
    return value if isinstance(value, dict) else {"status": "unknown_outcome", "reason": "state_invalid"}


def telegram_credentials() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or ""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID") or ""
    if not token or not chat_id:
        raise ValueError("telegram_credentials_missing")
    return token, chat_id


def send_request(message: str) -> tuple[str, dict[str, Any]]:
    token, chat_id = telegram_credentials()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message.replace("\\n","\n")}).encode("utf-8")
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
    except (urllib.error.URLError, TimeoutError, OSError):
        return "unknown_outcome", {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "unknown_outcome", {}
    if not isinstance(payload, dict):
        return "unknown_outcome", {}
    if payload.get("ok") is not True:
        code = payload.get("error_code")
        if isinstance(code, int) and 400 <= code < 500:
            return "definite_failure", {"telegram_error_code": code}
        return "unknown_outcome", {"telegram_error_code": code}
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
        return "unknown_outcome", {}
    return "sent", {"message_id": result["message_id"], "telegram_date": result.get("date")}


def deliver(message: str) -> int:
    try:
        identity = parse_message(message)
        _token, chat_id = telegram_credentials()
    except ValueError as exc:
        print(f"[telegram_delivery] BLOCK {exc}", file=sys.stderr)
        return 64

    if not prove_decision_persisted(identity):
        print("[telegram_delivery] BLOCK current_cycle_decision_not_durable", file=sys.stderr)
        return 65

    key = delivery_key(identity, chat_id)
    state_path, lock_path = state_paths(key)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        prior = read_state(state_path)
        if prior:
            status = str(prior.get("status",""))
            if status == "sent":
                print(f"[telegram_delivery] RECONCILED sent message_id={prior.get('message_id','')}", file=sys.stderr)
                return 0
            if status in {"intent","unknown_outcome"}:
                prior["status"] = "unknown_outcome"
                prior["reason"] = prior.get("reason") or "prior_attempt_unconfirmed"
                write_json_durable(state_path, prior)
                print("[telegram_delivery] BLOCK unknown_outcome_no_blind_resend", file=sys.stderr)
                return 75

        intent = {
            "schema_version": "1.0",
            "status": "intent",
            "identity": identity,
            "chat_id": chat_id,
            "delivery_key": key,
            "pid": os.getpid(),
            **runtime_provenance(),
        }
        write_json_durable(state_path, intent)

        outcome, detail = send_request(message)
        if outcome == "sent":
            confirmed = {**intent, **detail, "status": "sent"}
            write_json_durable(state_path, confirmed)
            print(f"[telegram_delivery] SENT message_id={confirmed['message_id']}", file=sys.stderr)
            return 0
        if outcome == "definite_failure":
            failed = {**intent, **detail, "status": "definite_failure"}
            write_json_durable(state_path, failed)
            print("[telegram_delivery] FAILED definite_rejection", file=sys.stderr)
            return 1

        unknown = {**intent, **detail, "status": "unknown_outcome", "reason": "no_authoritative_response"}
        write_json_durable(state_path, unknown)
        print("[telegram_delivery] UNKNOWN_OUTCOME no_blind_resend", file=sys.stderr)
        return 75


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()
    return deliver(args.message)


if __name__ == "__main__":
    raise SystemExit(main())
