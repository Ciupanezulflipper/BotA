#!/usr/bin/env python3
"""Crash-consistent Telegram delivery boundary for BotA watcher signals.

Contract:
- Prove the matching decision row already exists in logs/alerts.csv.
- Persist a durable intent before the network request.
- Persist Telegram confirmation (message_id/date) after an authoritative ok=true response.
- If a previous attempt is left in intent/unknown_outcome, never blindly resend it.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
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


def prove_decision_persisted(identity: dict[str, str]) -> bool:
    path = root_path() / "logs" / "alerts.csv"
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            rows = list(csv.reader(handle))
    except OSError:
        return False
    for values in reversed(rows[1:] if rows else []):
        row = row_dict(values)
        if row is not None and decision_matches(row, identity):
            return True
    return False


def delivery_key(identity: dict[str, str]) -> str:
    canonical = "|".join(identity[key] for key in ("pair","timeframe","direction","score","entry"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def state_paths(key: str) -> tuple[Path, Path]:
    directory = root_path() / "state" / "telegram_delivery"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{key}.json", directory / f"{key}.lock"


def fsync_directory(directory: Path) -> None:
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


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
        return "definite_failure", {"http_status": int(exc.code)}
    except (urllib.error.URLError, TimeoutError, OSError):
        return "unknown_outcome", {}
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "unknown_outcome", {}
    if not isinstance(payload, dict):
        return "unknown_outcome", {}
    if payload.get("ok") is not True:
        return "definite_failure", {"telegram_error_code": payload.get("error_code")}
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
        return "unknown_outcome", {}
    return "sent", {"message_id": result["message_id"], "telegram_date": result.get("date")}


def deliver(message: str) -> int:
    try:
        identity = parse_message(message)
    except ValueError as exc:
        print(f"[telegram_delivery] BLOCK {exc}", file=sys.stderr)
        return 64

    if not prove_decision_persisted(identity):
        print("[telegram_delivery] BLOCK decision_not_persisted", file=sys.stderr)
        return 65

    key = delivery_key(identity)
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
            "delivery_key": key,
            "pid": os.getpid(),
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

        unknown = {**intent, "status": "unknown_outcome", "reason": "no_authoritative_response"}
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
