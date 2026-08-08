#!/usr/bin/env python3
"""Apply BotA's final production quality and pair-risk policy.

This layer runs only after the existing M15/H1/H4/D1 fusion decision. It keeps
historical fusion semantics intact and adds the frozen Policy-B quality guard:

    current acceptance AND score >= 70 AND ADX < 30

It also corrects JPY-pair risk distances to use a 0.01 pip. The legacy scoring
engine uses a 0.0001 cap for every pair; that is harmless for EURUSD/GBPUSD but
would produce malformed USDJPY SL/TP distances.

The program is stdin/stdout strict JSON only. It performs no network I/O and no
file writes. Invalid policy, JSON, or JPY risk inputs fail closed for otherwise
accepted M15 trades.
"""

from __future__ import annotations

import json
import math
import os
import re
import signal
import sys
from typing import Any, Mapping

ADX_RE = re.compile(r"(?:^|[|,\s])adx\s*=\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE)


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _env_float(name: str, default: float) -> float:
    value = _finite(os.environ.get(name, default))
    if value is None:
        return default
    return value


def _enabled(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _extract_adx(data: Mapping[str, Any]) -> float | None:
    for key in ("adx_raw", "adx"):
        value = _finite(data.get(key))
        if value is not None and value >= 0.0:
            return value
    match = ADX_RE.search(str(data.get("reasons", "")))
    if not match:
        return None
    value = _finite(match.group(1))
    return value if value is not None and value >= 0.0 else None


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _filter_reasons(data: Mapping[str, Any]) -> list[str]:
    reasons = data.get("filter_reasons", [])
    if isinstance(reasons, list):
        return [str(item) for item in reasons]
    if reasons in (None, ""):
        return []
    return [str(reasons)]


def _risk_ratio(direction: str, entry: float, sl: float, tp: float) -> float:
    if direction == "BUY":
        risk = entry - sl
        reward = tp - entry
    else:
        risk = sl - entry
        reward = entry - tp
    if risk <= 0.0 or reward <= 0.0:
        return 0.0
    return reward / risk


def _normalize_jpy_risk(data: dict[str, Any]) -> bool:
    pair = str(data.get("pair", "")).upper()
    tf = str(data.get("tf", data.get("timeframe", ""))).upper()
    direction = str(data.get("direction", "")).upper()
    if "JPY" not in pair or tf != "M15" or direction not in {"BUY", "SELL"}:
        return True

    entry = _finite(data.get("entry"))
    atr = _finite(data.get("atr"))
    if entry is None or atr is None or entry <= 0.0 or atr <= 0.0:
        return False

    sl_mult = max(0.0, _env_float("SCALP_SL_ATR_MULT", 2.0))
    tp_mult = max(0.0, _env_float("SCALP_TP_ATR_MULT", 4.0))
    max_sl_pips = max(0.0, _env_float("MAX_SL_PIPS", 30.0))
    max_tp_pips = max(0.0, _env_float("MAX_TP_PIPS", 60.0))
    pip = 0.01

    sl_distance = min(atr * sl_mult, max_sl_pips * pip)
    tp_distance = min(atr * tp_mult, max_tp_pips * pip)
    if sl_distance <= 0.0 or tp_distance <= 0.0:
        return False

    if direction == "BUY":
        sl = entry - sl_distance
        tp = entry + tp_distance
    else:
        sl = entry + sl_distance
        tp = entry - tp_distance

    data["sl"] = round(sl, 5)
    data["tp"] = round(tp, 5)
    data["filter_rr"] = round(_risk_ratio(direction, entry, sl, tp), 3)
    data["risk_pip_size"] = pip
    data["risk_pair_aware"] = True
    return True


def _apply_policy_b(data: dict[str, Any], reasons: list[str], rejected: bool) -> bool:
    score_min = _env_float("POLICY_B_SCORE_MIN", 70.0)
    adx_max = _env_float("POLICY_B_ADX_MAX", 30.0)
    score = _finite(data.get("score"))
    adx = _extract_adx(data)

    if score is None:
        _append_unique(reasons, "policy_b_score_missing")
        rejected = True
    elif score < score_min:
        _append_unique(reasons, f"policy_b_score<{score_min:g}")
        rejected = True

    if adx is None:
        _append_unique(reasons, "policy_b_adx_missing")
        rejected = True
    elif adx >= adx_max:
        _append_unique(reasons, f"policy_b_adx>={adx_max:g}")
        rejected = True

    data["policy_b_enforced"] = True
    data["policy_b_score_min"] = score_min
    data["policy_b_adx_max"] = adx_max
    data["policy_b_adx"] = adx
    data["policy_b_pass"] = not rejected
    return rejected


def apply_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copied payload after final production policy enforcement."""
    data = dict(payload)
    direction = str(data.get("direction", "HOLD")).upper()
    tf = str(data.get("tf", data.get("timeframe", ""))).upper()

    if bool(data.get("filter_rejected", False)) or direction not in {"BUY", "SELL"}:
        return data
    if tf != "M15":
        return data

    reasons = _filter_reasons(data)
    rejected = not _normalize_jpy_risk(data)
    if rejected:
        _append_unique(reasons, "policy_jpy_risk_invalid")

    if _enabled("POLICY_B_ENABLED", True):
        rejected = _apply_policy_b(data, reasons, rejected)
    else:
        data["policy_b_enforced"] = False

    data["filter_reasons"] = reasons
    if rejected:
        data["filter_rejected"] = True
    return data


def _fallback(reason: str) -> dict[str, Any]:
    return {
        "pair": "UNKNOWN",
        "tf": "M15",
        "direction": "HOLD",
        "entry": 0.0,
        "sl": 0.0,
        "tp": 0.0,
        "score": 0.0,
        "confidence": 0.0,
        "provider": "production_signal_policy",
        "filter_rejected": True,
        "filter_reasons": ["fail_closed", reason],
        "reasons": reason,
    }


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _decode(raw: str) -> dict[str, Any]:
    value = json.loads(raw, parse_constant=_reject_json_constant)
    if not isinstance(value, dict):
        raise ValueError("payload is not an object")
    return value


def _encode(output: Mapping[str, Any]) -> str:
    return json.dumps(dict(output), separators=(",", ":"), allow_nan=False)


def _safe_encode(output: Mapping[str, Any]) -> str:
    try:
        return _encode(output)
    except (TypeError, ValueError):
        return _encode(_fallback("production_policy_error_serialization"))


def _emit(text: str) -> None:
    try:
        sys.stdout.write(text)
    except BrokenPipeError:
        pass


def main() -> None:
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except Exception:
        pass

    raw = sys.stdin.read()
    try:
        output = apply_policy(_decode(raw))
    except Exception as exc:
        output = _fallback(f"production_policy_error_{type(exc).__name__}")
    _emit(_safe_encode(output))


if __name__ == "__main__":
    main()
