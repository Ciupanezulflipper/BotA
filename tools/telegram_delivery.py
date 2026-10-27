#!/usr/bin/env python3
"""Crash-consistent Telegram delivery boundary for BotA watcher signals.

Contract:
- Prove the matching decision row exists in the current watcher cycle's alerts.csv append segment.
- Fsync the decision journal before any network side effect.
- Persist a durable intent before the Telegram request.
- Persist authoritative Telegram confirmation (message_id/date) after ok=true.
- If a previous attempt is left in intent/unknown_outcome, never blindly resend it.
- Reconcile BotA's existing cooldown and delivery hash after confirmed delivery.
- Persist structured watcher-cycle evidence before committing the legacy delivery hash.
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
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

LEGACY_FIELDS = (
    "timestamp", "pair", "tf", "direction", "score", "confidence", "entry", "sl", "tp",
    "provider", "rejected", "filter_str", "reasons",
)
CURRENT_FIELDS = (
    "ts", "pair", "tf", "direction", "score", "confidence", "entry", "sl", "tp", "provider",
    "filter_rejected", "filter_reasons", "reasons", "ema_comp", "rsi_comp", "macd_comp",
    "adx_comp", "adx_raw", "rsi_raw", "macd_hist_raw", "macro6", "h1_trend", "tier", "session",
    "adx_regime",
)
PAIR_RE = re.compile(r"\bBotA\s+([A-Z]{6})\s+([A-Z0-9]+)\s+(BUY|SELL)\b")
SCORE_RE = re.compile(r"(?:Score:\s*|score=)([0-9]+(?:\.[0-9]+)?)", re.I)
ENTRY_RE = re.compile(r"Entry:\s*([0-9]+(?:\.[0-9]+)?)", re.I)
ALERTS_OFFSET_ENV = "BOTA_ALERTS_OFFSET"
RESULT_LOG_ENV = "BOTA_TELEGRAM_RESULT_LOG"
DELIVERY_STATE_DIR_ENV = "BOTA_DELIVERY_STATE_DIR"
RESULT_LOG_PREFIX = "watcher_telegram."
RESULT_LOG_SUFFIX = ".jsonl"
RECONCILED_SENT_RC = 76
UNKNOWN_OUTCOME_RC = 75


def code_root() -> Path:
    return Path(os.environ.get("BOTA_CODE_ROOT") or os.environ.get("BOTA_ROOT") or Path.home() / "BotA").expanduser().resolve()


def mutable_root() -> Path:
    return Path(os.environ.get("BOTA_MUTABLE_ROOT") or os.environ.get("BOTA_ROOT") or code_root()).expanduser().resolve()


def root_path() -> Path:  # compatibility alias for mutable runtime state
    return mutable_root()


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


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


def decision_matches(row: dict[str, str], message_identity: dict[str, str]) -> bool:
    if str(row.get("pair", "")).upper() != message_identity["pair"]:
        return False
    if str(row.get("tf", row.get("timeframe", ""))).upper() != message_identity["timeframe"]:
        return False
    if str(row.get("direction", "")).upper() != message_identity["direction"]:
        return False
    rejected = row.get("filter_rejected")
    if rejected is None or str(rejected).strip() == "":
        rejected = row.get("rejected")
    if truthy(rejected):
        return False
    try:
        if abs(float(row.get("score", "0")) - float(message_identity["score"])) > 0.011:
            return False
    except (TypeError, ValueError):
        return False
    if message_identity["entry"]:
        try:
            if abs(float(row.get("entry", "0")) - float(message_identity["entry"])) > 0.000001:
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


def current_cycle_decision(message_identity: dict[str, str]) -> dict[str, str] | None:
    path = root_path() / "logs" / "alerts.csv"
    try:
        offset = cycle_alerts_offset()
        rows = read_cycle_rows(path, offset)
    except (OSError, ValueError):
        return None
    selected = None
    for values in reversed(rows):
        row = row_dict(values)
        if row is not None and decision_matches(row, message_identity):
            selected = row
            break
    if selected is None:
        return None
    try:
        fsync_file_and_parent(path)
    except OSError:
        return None
    return selected


def canonical_identity(row: dict[str, str]) -> dict[str, str]:
    return {
        "pair": str(row.get("pair", "")).upper(),
        "timeframe": str(row.get("tf", row.get("timeframe", ""))).upper(),
        "direction": str(row.get("direction", "")).upper(),
        "score": str(row.get("score", "")).strip(),
        "entry": str(row.get("entry", "")).strip(),
        "sl": str(row.get("sl", "")).strip(),
        "tp": str(row.get("tp", "")).strip(),
    }


def delivery_key(identity: dict[str, str], chat_id: str) -> str:
    canonical = "|".join(
        [chat_id] + [identity[key] for key in ("pair", "timeframe", "direction", "score", "entry", "sl", "tp")]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def legacy_delivery_hash(identity: dict[str, str]) -> str:
    raw = "|".join(identity[key] for key in ("pair", "timeframe", "direction", "score", "entry", "sl", "tp"))
    return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()


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
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
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


def write_text_durable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
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


def delivery_state_dir() -> Path:
    expected = (root_path() / "logs" / "state").resolve()
    raw = os.environ.get(DELIVERY_STATE_DIR_ENV, "").strip()
    if not raw:
        raise ValueError("delivery_state_dir_missing")
    supplied = Path(raw).expanduser().resolve()
    if supplied != expected:
        raise ValueError("delivery_state_dir_mismatch")
    supplied.mkdir(parents=True, exist_ok=True)
    return supplied


def prepare_legacy_cooldown(identity: dict[str, str], provenance: dict[str, Any]) -> bool:
    """Persist cooldown state before structured cycle evidence.

    The delivery hash is intentionally not written here. It is the final legacy
    commit marker and is written only after structured cycle evidence is durable.
    """
    try:
        directory = delivery_state_dir()
        boot_id = str(provenance.get("boot_id") or "unknown")
        monotonic_seconds = int(provenance.get("monotonic_ns") or 0) // 1_000_000_000
        if monotonic_seconds <= 0:
            return False
        cooldown = directory / f"last_sent_{identity['pair']}_{identity['timeframe']}.txt"
        write_text_durable(cooldown, f"{boot_id} {monotonic_seconds}\n")
        return True
    except (OSError, ValueError, TypeError):
        return False


def commit_legacy_delivery_hash(identity: dict[str, str]) -> bool:
    """Write the legacy delivery hash as the final local commit marker."""
    try:
        directory = delivery_state_dir()
        hash_path = directory / f"last_hash_{identity['pair']}_{identity['timeframe']}.txt"
        write_text_durable(hash_path, legacy_delivery_hash(identity))
        return True
    except (OSError, ValueError, TypeError):
        return False


def cycle_result_path() -> tuple[Path | None, bool]:
    raw = os.environ.get(RESULT_LOG_ENV, "").strip()
    if not raw:
        return None, True
    try:
        path = Path(raw).expanduser().resolve(strict=True)
        state_dir = (root_path() / "state").resolve(strict=True)
        info = path.stat()
    except OSError:
        return None, False
    valid = (
        path.parent == state_dir
        and path.name.startswith(RESULT_LOG_PREFIX)
        and path.name.endswith(RESULT_LOG_SUFFIX)
        and stat.S_ISREG(info.st_mode)
        and info.st_uid == os.getuid()
        and not (info.st_mode & 0o077)
    )
    return (path, True) if valid else (None, False)


def emit_cycle_result(identity: dict[str, str], status: str, detail: dict[str, Any] | None = None) -> bool:
    path, valid = cycle_result_path()
    if not valid:
        return False
    if path is None:
        return True
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        **identity,
        "status": status,
    }
    if detail:
        if isinstance(detail.get("message_id"), int):
            payload["message_id"] = detail["message_id"]
        if isinstance(detail.get("telegram_date"), int):
            payload["telegram_date"] = detail["telegram_date"]
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except OSError:
        return False


def telegram_credentials() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or ""
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID") or ""
    if not token or not chat_id:
        raise ValueError("telegram_credentials_missing")
    return token, chat_id


def send_request(message: str) -> tuple[str, dict[str, Any]]:
    token, chat_id = telegram_credentials()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message.replace("\\n", "\n")}).encode("utf-8")
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


def finalize_confirmed_delivery(
    identity: dict[str, str],
    provenance: dict[str, Any],
    cycle_status: str,
    detail: dict[str, Any],
) -> bool:
    """Persist cooldown, structured result, then legacy hash in that order."""
    if not prepare_legacy_cooldown(identity, provenance):
        emit_cycle_result(identity, "sent_local_reconcile_failed", detail)
        return False
    if not emit_cycle_result(identity, cycle_status, detail):
        return False
    if not commit_legacy_delivery_hash(identity):
        return False
    return True


def deliver(message: str) -> int:
    try:
        message_identity = parse_message(message)
        _token, chat_id = telegram_credentials()
    except ValueError as exc:
        print(f"[telegram_delivery] BLOCK {exc}", file=sys.stderr)
        return 64

    row = current_cycle_decision(message_identity)
    if row is None:
        print("[telegram_delivery] BLOCK current_cycle_decision_not_durable", file=sys.stderr)
        return 65
    identity = canonical_identity(row)

    key = delivery_key(identity, chat_id)
    state_path, lock_path = state_paths(key)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        prior = read_state(state_path)
        if prior:
            status = str(prior.get("status", ""))
            if status == "sent":
                provenance = runtime_provenance()
                if not finalize_confirmed_delivery(identity, provenance, "reconciled_sent", prior):
                    print("[telegram_delivery] BLOCK sent_but_local_reconcile_failed", file=sys.stderr)
                    return UNKNOWN_OUTCOME_RC
                print(f"[telegram_delivery] RECONCILED sent message_id={prior.get('message_id', '')}", file=sys.stderr)
                return RECONCILED_SENT_RC
            if status in {"intent", "unknown_outcome"}:
                prior["status"] = "unknown_outcome"
                prior["reason"] = prior.get("reason") or "prior_attempt_unconfirmed"
                write_json_durable(state_path, prior)
                emit_cycle_result(identity, "unknown_outcome", prior)
                print("[telegram_delivery] BLOCK unknown_outcome_no_blind_resend", file=sys.stderr)
                return UNKNOWN_OUTCOME_RC

        provenance = runtime_provenance()
        intent = {
            "schema_version": "1.0",
            "status": "intent",
            "identity": identity,
            "chat_id": chat_id,
            "delivery_key": key,
            "pid": os.getpid(),
            **provenance,
        }
        write_json_durable(state_path, intent)

        outcome, detail = send_request(message)
        if outcome == "sent":
            confirmed = {**intent, **detail, "status": "sent"}
            write_json_durable(state_path, confirmed)
            if not finalize_confirmed_delivery(identity, provenance, "sent", detail):
                print("[telegram_delivery] BLOCK sent_but_local_reconcile_failed", file=sys.stderr)
                return UNKNOWN_OUTCOME_RC
            print(f"[telegram_delivery] SENT message_id={confirmed['message_id']}", file=sys.stderr)
            return 0
        if outcome == "definite_failure":
            failed = {**intent, **detail, "status": "definite_failure"}
            write_json_durable(state_path, failed)
            emit_cycle_result(identity, "definite_failure", detail)
            print("[telegram_delivery] FAILED definite_rejection", file=sys.stderr)
            return 1

        unknown = {**intent, **detail, "status": "unknown_outcome", "reason": "no_authoritative_response"}
        write_json_durable(state_path, unknown)
        emit_cycle_result(identity, "unknown_outcome", detail)
        print("[telegram_delivery] UNKNOWN_OUTCOME no_blind_resend", file=sys.stderr)
        return UNKNOWN_OUTCOME_RC


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()
    return deliver(args.message)


if __name__ == "__main__":
    raise SystemExit(main())
