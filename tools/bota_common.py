#!/usr/bin/env python3
"""Shared side-effect-free helpers used by several BotA tools.

This module exists to remove copy-pasted helpers (UTC time handling, value
coercion, pip sizing, SHA-256 hashing and JSONL reading) from the
individual tools. Importing it must never touch the filesystem, the network or
the environment, so it stays safe for both production entrypoints and tests.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

UTC = timezone.utc

TRUTHY_TOKENS = frozenset({"1", "true", "yes", "y", "on"})

FX_PIP_SIZE = 0.0001
JPY_PIP_SIZE = 0.01
GOLD_PIP_SIZE = 0.1
SILVER_PIP_SIZE = 0.01

GOLD_SYMBOLS = frozenset({"XAUUSD", "XAU/USD"})
SILVER_SYMBOLS = frozenset({"XAGUSD", "XAG/USD"})

# Watcher alert CSV schemas shared by the delivery and persistence tools.
LEGACY_ALERT_FIELDS = (
    "timestamp", "pair", "tf", "direction", "score", "confidence", "entry", "sl", "tp",
    "provider", "rejected", "filter_str", "reasons",
)
CURRENT_ALERT_FIELDS = (
    "ts", "pair", "tf", "direction", "score", "confidence", "entry", "sl", "tp", "provider",
    "filter_rejected", "filter_reasons", "reasons", "ema_comp", "rsi_comp", "macd_comp",
    "adx_comp", "adx_raw", "rsi_raw", "macd_hist_raw", "macro6", "h1_trend", "tier", "session",
    "adx_regime",
)


# ---------------------------------------------------------------- time helpers
def utc_now() -> datetime:
    """Return the current aware UTC timestamp."""
    return datetime.now(UTC)


def iso_z(value: datetime) -> str:
    """Render an aware datetime in canonical UTC ``Z`` form."""
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp that must carry an offset, normalized to UTC."""
    text = str(value).strip()
    if not text:
        raise ValueError("timestamp is empty")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def parse_utc_assume_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp, treating a missing offset as UTC."""
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_utc_or_none(value: Any) -> Optional[datetime]:
    """Parse an offset-carrying ISO-8601 timestamp, or return ``None``."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return parse_utc(text)
    except Exception:
        return None


# ----------------------------------------------------------- value coercion
def truthy(value: Any) -> bool:
    """Interpret env/CSV style flags as booleans."""
    return str(value or "").strip().lower() in TRUTHY_TOKENS


def safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce any value to a finite float, falling back to ``default``."""
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def finite(value: Any, field: str) -> float:
    """Coerce to float and reject NaN/infinite values."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite {field}")
    return number


# ------------------------------------------------------------------ instruments
def fx_pip_size(pair: str) -> float:
    """Return the pip size for one FX pair, ignoring metals."""
    return JPY_PIP_SIZE if "JPY" in str(pair or "").upper() else FX_PIP_SIZE


def pip_size(pair: str) -> float:
    """Return the pip size for one traded symbol, including metals."""
    symbol = str(pair or "").upper().strip()
    if "JPY" in symbol:
        return JPY_PIP_SIZE
    if symbol in GOLD_SYMBOLS:
        return GOLD_PIP_SIZE
    if symbol in SILVER_SYMBOLS:
        return SILVER_PIP_SIZE
    return FX_PIP_SIZE


# --------------------------------------------------------------------- hashing
def sha256_file(path: Path) -> str:
    """Return the SHA-256 of one file, streamed in 1 MiB blocks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------- json io
def read_jsonl_objects(path: Path, *, label: str = "ledger") -> list[dict[str, Any]]:
    """Read a non-empty JSONL file of objects, rejecting malformed lines."""
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"event line {line_number} is not an object")
            rows.append(value)
    if not rows:
        raise ValueError(f"{label} is empty")
    return rows
