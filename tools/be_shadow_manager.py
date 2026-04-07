#!/usr/bin/env python3
"""
be_shadow_manager.py
BotA read-only shadow trade manager.

Writes only to shadow_log. Never touches signals table.
Two policy lanes: STATIC_MIRROR (canary) and BE_1.0R (experimental).
Candle anchor: signal created_at only. last_polled_at is never used as replay anchor.
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

BASE_DIR = Path.home() / "BotA"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "shadow_manager.log"
HEARTBEAT_PATH = LOG_DIR / "shadow_manager_heartbeat.txt"

# ---------------------------------------------------------------------------
# ENV LOADER  (first file wins per key)
# ---------------------------------------------------------------------------

def _load_env(path: Path) -> None:
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:]
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass

for _p in [
    BASE_DIR / ".env.runtime",
    BASE_DIR / ".env",
    BASE_DIR / "config" / "strategy.env",
    BASE_DIR / "strategy.env",
]:
    _load_env(_p)

# ---------------------------------------------------------------------------
# CONFIG  (no secret defaults)
# ---------------------------------------------------------------------------

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY") or ""
OANDA_TOKEN: str = os.getenv("OANDA_API_TOKEN") or os.getenv("OANDA_API_KEY") or ""
OANDA_MODE: str = os.getenv("OANDA_MODE", "").strip().upper()

SHADOW_ENABLED: bool = os.getenv("SHADOW_ENABLED", "false").strip().lower() == "true"
BE_R_THRESHOLD: float = float(os.getenv("BE_R_THRESHOLD", "1.0"))
MIRROR_DIV_THRESHOLD: float = float(os.getenv("MIRROR_DIVERGENCE_THRESHOLD_PIPS", "2.0"))
TERMINAL_LOOKBACK_HOURS: int = int(os.getenv("TERMINAL_LOOKBACK_HOURS", "96"))
RECONCILE_COOLDOWN_MIN: int = int(os.getenv("RECONCILE_RETRY_COOLDOWN_MINUTES", "60"))
RECONCILE_MAX_AGE_HRS: int = int(os.getenv("RECONCILE_MAX_AGE_HOURS", "96"))

OPEN_STATUSES: frozenset = frozenset({"ACTIVE", "active"})
POLICIES: Tuple[str, ...] = ("STATIC_MIRROR", "BE_1.0R")

REQUIRED_SHADOW_COLS: Tuple[str, ...] = (
    "id", "signal_id", "policy", "pair", "direction",
    "entry_price", "stop_loss", "take_profit", "risk_pips",
    "signal_created_at", "highest_mfe_pips", "highest_mfe_r",
    "arm_triggered", "arm_triggered_at", "arm_candle_high", "arm_candle_low",
    "shadow_state", "shadow_outcome", "shadow_pips", "shadow_closed_at",
    "actual_outcome", "actual_pips", "actual_closed_at", "delta_pips",
    "last_polled_at", "last_candle_ts_processed", "last_error",
    "poll_count", "candle_source", "logged_at",
)

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("shadow")
UNIQ_CONFLICT_ERR = "no unique or exclusion constraint matching the ON CONFLICT specification"

# ---------------------------------------------------------------------------
# DATA MODEL
# ---------------------------------------------------------------------------

@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    ).astimezone(timezone.utc)

def pip_size(pair: str) -> float:
    return 0.01 if pair.upper().endswith("JPY") else 0.0001

def pips_between(a: float, b: float, pair: str) -> float:
    return round(abs(a - b) / pip_size(pair), 1)

def fav_mfe(c: Candle, entry: float, direction: str, pair: str) -> float:
    ps = pip_size(pair)
    if direction.upper() == "SELL":
        return max(0.0, round((entry - c.low) / ps, 1))
    return max(0.0, round((c.high - entry) / ps, 1))

def oanda_instr(pair: str) -> str:
    clean = pair.upper().replace("/", "").replace("_", "")
    return f"{clean[:3]}_{clean[3:]}" if len(clean) == 6 else pair.upper()

def write_heartbeat(status: str, detail: str = "") -> None:
    with HEARTBEAT_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{to_iso(now_utc())} | {status} | {detail}\n")

def check_heartbeat(max_gap_min: int = 35) -> None:
    if not HEARTBEAT_PATH.exists():
        return
    try:
        last = HEARTBEAT_PATH.read_text(errors="ignore").strip().splitlines()[-1]
        gap = (now_utc() - parse_ts(last.split(" | ")[0])).total_seconds() / 60.0
        if gap > max_gap_min:
            log.warning("MISSED_CYCLE: last heartbeat %.1f min ago (expected <=15)", gap)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# CONFIG + SCHEMA VALIDATION
# ---------------------------------------------------------------------------

def validate_config() -> bool:
    errors: List[str] = []
    if not SUPABASE_URL:
        errors.append("SUPABASE_URL is not set")
    if not SUPABASE_KEY:
        errors.append("SUPABASE_SERVICE_KEY (or SUPABASE_KEY) is not set")
    if not OANDA_TOKEN:
        errors.append("OANDA_API_TOKEN (or OANDA_API_KEY) is not set")
    if OANDA_MODE not in ("PRACTICE", "LIVE"):
        errors.append(
            f"OANDA_MODE must be exactly 'PRACTICE' or 'LIVE' -- got: '{OANDA_MODE}'. "
            "Verify your token type in the OANDA portal before setting this."
        )
    for err in errors:
        log.error("CONFIG ERROR: %s", err)
    return len(errors) == 0

def oanda_base_url() -> str:
    return (
        "https://api-fxpractice.oanda.com"
        if OANDA_MODE == "PRACTICE"
        else "https://api-fxtrade.oanda.com"
    )

def check_schema_compatibility() -> bool:
    """
    Validates shadow_log has all required columns.
    Fetches LIMIT=0 rows -- zero data transferred, column list only.
    """
    select_cols = ",".join(REQUIRED_SHADOW_COLS)
    try:
        sb_get("shadow_log", {"select": select_cols, "limit": "0"})
        log.info("Schema compatibility: PASS (%d required columns verified)", len(REQUIRED_SHADOW_COLS))
        return True
    except Exception as exc:
        log.error(
            "Schema compatibility: FAIL -- %s\n"
            "Most likely missing: last_candle_ts_processed\n"
            "Fix in Supabase SQL Editor:\n"
            "  ALTER TABLE shadow_log ADD COLUMN IF NOT EXISTS last_candle_ts_processed TIMESTAMPTZ;",
            exc,
        )
        return False

# ---------------------------------------------------------------------------
# SUPABASE HELPERS
# ---------------------------------------------------------------------------

def _sb_headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }

def sb_get(table: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_sb_headers(),
        params=params or {},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []

def sb_post(
    table: str,
    payload: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    prefer: str = "return=representation",
) -> List[Dict[str, Any]]:
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_sb_headers(prefer),
        params=params or {},
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []

def sb_patch(
    table: str,
    filters: Dict[str, Any],
    payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=_sb_headers(),
        params=filters,
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []

# ---------------------------------------------------------------------------
# OANDA CANDLE FETCH
# ---------------------------------------------------------------------------

def fetch_m15_candles(pair: str, start_dt: datetime, end_dt: datetime) -> List[Candle]:
    """
    Fetch COMPLETE OANDA M15 midpoint candles in [start_dt, end_dt).
    Returns [] on any error. Callers must treat [] as data-unavailable,
    NOT as evidence the market was flat or the trade stayed open.
    """
    instr = oanda_instr(pair)
    params = {
        "granularity": "M15",
        "price": "M",
        "from": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
        "to": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
    }
    try:
        r = requests.get(
            f"{oanda_base_url()}/v3/instruments/{instr}/candles",
            headers={"Authorization": f"Bearer {OANDA_TOKEN}"},
            params=params,
            timeout=25,
        )
        r.raise_for_status()
        raw = r.json()
    except Exception as exc:
        log.error("OANDA fetch failed %s [%s->%s]: %s", instr, params["from"], params["to"], exc)
        return []

    candles: List[Candle] = []
    for item in raw.get("candles", []):
        if not item.get("complete", False):
            continue
        try:
            m = item["mid"]
            candles.append(Candle(
                time=parse_ts(item["time"]),
                open=float(m["o"]),
                high=float(m["h"]),
                low=float(m["l"]),
                close=float(m["c"]),
            ))
        except Exception:
            continue
    return candles

# ---------------------------------------------------------------------------
# SIGNAL FETCHING (read-only on signals table)
# ---------------------------------------------------------------------------

def fetch_active_signals() -> List[Dict[str, Any]]:
    """Defensive on status casing. Logs unexpected values."""
    try:
        rows = sb_get("signals", {
            "status": "in.(ACTIVE,active)",
            "select": "id,pair,direction,entry_price,stop_loss,take_profit,created_at,status,timeframe",
            "order": "created_at.asc",
        })
    except Exception as exc:
        log.error("fetch_active_signals failed: %s", exc)
        return []
    valid: List[Dict[str, Any]] = []
    for row in rows:
        status = str(row.get("status", ""))
        if status in OPEN_STATUSES:
            valid.append(row)
        else:
            log.warning("Unexpected open-status '%s' on signal %s -- skipping", status, row.get("id"))
    return valid

def fetch_recently_terminal(hours: int = TERMINAL_LOOKBACK_HOURS) -> List[Dict[str, Any]]:
    """
    Fetch production signals that went terminal in the last N hours.
    Includes all fields needed for BOTH backfill and reconciliation replay.
    Called ONCE per cycle in main(); result shared by both consumers.
    """
    since = to_iso(now_utc() - timedelta(hours=hours))
    try:
        return sb_get("signals", {
            "status": "in.(CLOSED,CANCELLED)",
            "closed_at": f"gte.{since}",
            "select": (
                "id,status,result_pips,closed_at,"
                "pair,direction,entry_price,stop_loss,take_profit,created_at"
            ),
            "order": "closed_at.desc",
        })
    except Exception as exc:
        log.error("fetch_recently_terminal failed: %s", exc)
        return []

# ---------------------------------------------------------------------------
# SHADOW LOG OPERATIONS
# ---------------------------------------------------------------------------

def fetch_shadow_rows_by_ids(signal_ids: List[str], policy: str) -> Dict[str, Dict[str, Any]]:
    if not signal_ids:
        return {}
    try:
        rows = sb_get("shadow_log", {
            "signal_id": f"in.({','.join(signal_ids)})",
            "policy": f"eq.{policy}",
            "select": "*",
        })
        return {str(r["signal_id"]): r for r in rows}
    except Exception as exc:
        log.error("fetch_shadow_rows_by_ids policy=%s: %s", policy, exc)
        return {}

def fetch_open_shadow_rows(policy: str) -> List[Dict[str, Any]]:
    """Fetch shadow_log rows still in TRACKING or ARMED. Used by reconciliation."""
    try:
        rows = sb_get("shadow_log", {
            "policy": f"eq.{policy}",
            "shadow_state": "in.(TRACKING,ARMED)",
            "select": "*",
        })
        return rows if isinstance(rows, list) else []
    except Exception as exc:
        log.error("fetch_open_shadow_rows policy=%s: %s", policy, exc)
        return []

def ensure_shadow_row(sig: Dict[str, Any], policy: str, poll_ts: str) -> Dict[str, Any]:
    """
    Insert initial shadow row if absent. ON CONFLICT DO NOTHING -- fully idempotent.
    last_polled_at is set for heartbeat purposes ONLY.
    It is NEVER used as a candle replay anchor.
    """
    entry = float(sig["entry_price"])
    sl = float(sig["stop_loss"])
    pair = str(sig["pair"])
    payload = {
        "signal_id": sig["id"],
        "policy": policy,
        "pair": pair,
        "direction": str(sig["direction"]).upper(),
        "entry_price": entry,
        "stop_loss": sl,
        "take_profit": float(sig["take_profit"]),
        "risk_pips": pips_between(entry, sl, pair),
        "signal_created_at": sig["created_at"],
        "highest_mfe_pips": 0.0,
        "highest_mfe_r": 0.0,
        "arm_triggered": False,
        "shadow_state": "TRACKING",
        "poll_count": 0,
        "last_polled_at": poll_ts,
        "last_candle_ts_processed": None,
        "candle_source": "OANDA",
    }
    try:
        sb_post(
            "shadow_log",
            payload,
            params={"on_conflict": "signal_id,policy"},
            prefer="resolution=ignore-duplicates,return=representation",
        )
    except Exception as exc:
        msg = str(exc)
        if UNIQ_CONFLICT_ERR in msg:
            raise RuntimeError(
                "uniqueness contract not enforced for shadow_log(signal_id, policy). "
                "Action: ALTER TABLE shadow_log ADD CONSTRAINT "
                "shadow_log_signal_policy_uniq UNIQUE (signal_id, policy);"
            ) from exc
        log.error("ensure_shadow_row insert %s/%s: %s", sig["id"], policy, exc)
    rows = sb_get("shadow_log", {
        "signal_id": f"eq.{sig['id']}",
        "policy": f"eq.{policy}",
        "select": "*",
    })
    return rows[0] if rows else {}

def update_shadow_row(signal_id: str, policy: str, updates: Dict[str, Any]) -> None:
    try:
        sb_patch(
            "shadow_log",
            {"signal_id": f"eq.{signal_id}", "policy": f"eq.{policy}"},
            updates,
        )
    except Exception as exc:
        log.error("update_shadow_row %s/%s: %s", signal_id, policy, exc)

# ---------------------------------------------------------------------------
# POLICY EVALUATION
# ---------------------------------------------------------------------------

def eval_static_mirror(
    c: Candle, entry: float, sl: float, tp: float, direction: str, pair: str
) -> Dict[str, Any]:
    """
    TP-first same-candle rule -- exact mirror of production static closer.
    Returns {outcome, pips}. outcome is None if trade still open.
    """
    if direction.upper() == "SELL":
        if c.low <= tp:
            return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair)}
        if c.high >= sl:
            return {"outcome": "CLOSED_SL", "pips": -pips_between(entry, sl, pair)}
    else:
        if c.high >= tp:
            return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair)}
        if c.low <= sl:
            return {"outcome": "CLOSED_SL", "pips": -pips_between(entry, sl, pair)}
    return {"outcome": None, "pips": None}

def eval_be_1r(
    c: Candle,
    entry: float,
    sl: float,
    tp: float,
    direction: str,
    pair: str,
    risk_pips: float,
    already_armed: bool,
) -> Dict[str, Any]:
    """
    BE_1.0R same-candle adjudication -- audit-specified exact rules.
    Returns {outcome, pips, newly_armed}.
    outcome is None if trade still open or just armed (continue loop).

    SELL pre-arm priority order:
      arm_price = entry - risk_pips * BE_R_THRESHOLD * pip_size
      be_stop   = entry
      1. arm_hit AND tp_hit                    -> CLOSED_TP         [TP-first]
      2. arm_hit AND sl_hit                    -> CLOSED_BE 0.0     [arm-first]
      3. arm_hit AND high >= be_stop (entry)   -> CLOSED_BE 0.0     [returned to entry same candle]
      4. arm_hit only                          -> ARMED
      5. tp_hit only                           -> CLOSED_TP
      6. sl_hit only                           -> CLOSED_SL
      7. none                                  -> None

    SELL armed (be_stop = entry):
      1. low <= tp                             -> CLOSED_TP         [TP-first]
      2. high >= be_stop                       -> CLOSED_BE 0.0
      3. neither                               -> None

    BUY mirrors symmetrically (high/low swapped).
    """
    ps = pip_size(pair)
    one_r = risk_pips * BE_R_THRESHOLD * ps

    if direction.upper() == "SELL":
        arm_price = entry - one_r
        be_stop = entry

        if already_armed:
            if c.low <= tp:
                return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair), "newly_armed": False}
            if c.high >= be_stop:
                return {"outcome": "CLOSED_BE", "pips": 0.0, "newly_armed": False}
            return {"outcome": None, "pips": None, "newly_armed": False}

        arm_hit = c.low <= arm_price
        tp_hit = c.low <= tp
        sl_hit = c.high >= sl
        returned_to_entry = c.high >= be_stop

        if arm_hit and tp_hit:
            return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair), "newly_armed": True}
        if arm_hit and sl_hit:
            return {"outcome": "CLOSED_BE", "pips": 0.0, "newly_armed": True}
        if arm_hit and returned_to_entry:
            return {"outcome": "CLOSED_BE", "pips": 0.0, "newly_armed": True}
        if arm_hit:
            return {"outcome": "ARMED", "pips": None, "newly_armed": True}
        if tp_hit:
            return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair), "newly_armed": False}
        if sl_hit:
            return {"outcome": "CLOSED_SL", "pips": -pips_between(entry, sl, pair), "newly_armed": False}
        return {"outcome": None, "pips": None, "newly_armed": False}

    # BUY
    arm_price = entry + one_r
    be_stop = entry

    if already_armed:
        if c.high >= tp:
            return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair), "newly_armed": False}
        if c.low <= be_stop:
            return {"outcome": "CLOSED_BE", "pips": 0.0, "newly_armed": False}
        return {"outcome": None, "pips": None, "newly_armed": False}

    arm_hit = c.high >= arm_price
    tp_hit = c.high >= tp
    sl_hit = c.low <= sl
    returned_to_entry = c.low <= be_stop

    if arm_hit and tp_hit:
        return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair), "newly_armed": True}
    if arm_hit and sl_hit:
        return {"outcome": "CLOSED_BE", "pips": 0.0, "newly_armed": True}
    if arm_hit and returned_to_entry:
        return {"outcome": "CLOSED_BE", "pips": 0.0, "newly_armed": True}
    if arm_hit:
        return {"outcome": "ARMED", "pips": None, "newly_armed": True}
    if tp_hit:
        return {"outcome": "CLOSED_TP", "pips": +pips_between(entry, tp, pair), "newly_armed": False}
    if sl_hit:
        return {"outcome": "CLOSED_SL", "pips": -pips_between(entry, sl, pair), "newly_armed": False}
    return {"outcome": None, "pips": None, "newly_armed": False}

# ---------------------------------------------------------------------------
# CANDLE REPLAY ENGINE
# ---------------------------------------------------------------------------

def replay_candles(
    candles: List[Candle],
    policy: str,
    entry: float,
    sl: float,
    tp: float,
    direction: str,
    pair: str,
    risk_pips: float,
    already_armed: bool,
    highest_mfe_pips: float,
    highest_mfe_r: float,
) -> Dict[str, Any]:
    """
    Replay a pre-fetched candle list under one policy.
    Only callable after confirming candles is non-empty.
    replay variable in callers is ONLY assigned after a non-empty candles guard.
    """
    arm_triggered_this_run: bool = False
    arm_triggered_at: Optional[str] = None
    arm_candle_high: Optional[float] = None
    arm_candle_low: Optional[float] = None
    terminal_outcome: Optional[str] = None
    terminal_pips: Optional[float] = None
    terminal_ts: Optional[str] = None
    last_candle_ts: Optional[str] = None

    for candle in candles:
        last_candle_ts = to_iso(candle.time)
        mfe = fav_mfe(candle, entry, direction, pair)
        if mfe > highest_mfe_pips:
            highest_mfe_pips = mfe
            highest_mfe_r = round(mfe / risk_pips, 3) if risk_pips > 0 else 0.0

        if policy == "STATIC_MIRROR":
            result = eval_static_mirror(candle, entry, sl, tp, direction, pair)
        else:
            result = eval_be_1r(candle, entry, sl, tp, direction, pair, risk_pips, already_armed)

        newly_armed = result.get("newly_armed", False)
        if newly_armed and not already_armed and not arm_triggered_this_run:
            arm_triggered_this_run = True
            already_armed = True
            arm_triggered_at = to_iso(candle.time)
            arm_candle_high = candle.high
            arm_candle_low = candle.low

        if result["outcome"] == "ARMED":
            continue

        if result["outcome"] is not None:
            terminal_outcome = str(result["outcome"])
            terminal_pips = float(result["pips"])
            terminal_ts = to_iso(candle.time)
            break

    return {
        "terminal_outcome": terminal_outcome,
        "terminal_pips": terminal_pips,
        "terminal_ts": terminal_ts,
        "arm_triggered_this_run": arm_triggered_this_run,
        "arm_triggered_at": arm_triggered_at,
        "arm_candle_high": arm_candle_high,
        "arm_candle_low": arm_candle_low,
        "highest_mfe_pips": highest_mfe_pips,
        "highest_mfe_r": highest_mfe_r,
        "last_candle_ts": last_candle_ts,
    }

# ---------------------------------------------------------------------------
# ACTIVE SIGNAL PROCESSING
# ---------------------------------------------------------------------------

def process_active_signal(
    sig: Dict[str, Any],
    shadow_row: Dict[str, Any],
    policy: str,
    poll_now: datetime,
    poll_now_iso: str,
) -> None:
    """
    Process one ACTIVE production signal under one shadow policy.

    Candle fetch window:
      If last_candle_ts_processed is set: fetch_from = last_candle_ts + 15min
      If null (first run):                fetch_from = signal created_at

    CRITICAL: last_polled_at is NEVER used as fetch_from.
    ensure_shadow_row() sets last_polled_at immediately on row creation,
    so using it as replay anchor on first run would skip all candles
    from created_at to now.
    """
    signal_id = str(sig["id"])
    pair = str(sig["pair"])
    direction = str(sig["direction"]).upper()
    entry = float(sig["entry_price"])
    sl = float(sig["stop_loss"])
    tp = float(sig["take_profit"])
    created_at = parse_ts(sig["created_at"])
    risk_pips = float(shadow_row.get("risk_pips") or pips_between(entry, sl, pair))

    if str(shadow_row.get("shadow_state")) == "CLOSED":
        return

    horizon = created_at + timedelta(hours=24)

    # Candle fetch boundary -- last_candle_ts_processed is the ONLY valid anchor
    last_candle_raw = shadow_row.get("last_candle_ts_processed")
    if last_candle_raw:
        fetch_from = parse_ts(last_candle_raw) + timedelta(minutes=15)
    else:
        # First run: start from signal creation time.
        # last_polled_at is NOT used here.
        fetch_from = created_at

    fetch_to = min(poll_now, horizon)

    if fetch_from >= fetch_to:
        update_shadow_row(signal_id, policy, {
            "last_polled_at": poll_now_iso,
            "poll_count": int(shadow_row.get("poll_count") or 0) + 1,
            "last_error": None,
        })
        return

    candles = fetch_m15_candles(pair, fetch_from, fetch_to)
    if not candles:
        update_shadow_row(signal_id, policy, {
            "last_polled_at": poll_now_iso,
            "poll_count": int(shadow_row.get("poll_count") or 0) + 1,
            "last_error": f"no_candles {to_iso(fetch_from)}->{to_iso(fetch_to)}",
        })
        return

    # replay only assigned here -- after confirmed non-empty candles
    replay = replay_candles(
        candles=candles,
        policy=policy,
        entry=entry,
        sl=sl,
        tp=tp,
        direction=direction,
        pair=pair,
        risk_pips=risk_pips,
        already_armed=bool(shadow_row.get("arm_triggered") or False),
        highest_mfe_pips=float(shadow_row.get("highest_mfe_pips") or 0.0),
        highest_mfe_r=float(shadow_row.get("highest_mfe_r") or 0.0),
    )

    terminal_outcome = replay["terminal_outcome"]
    terminal_pips = replay["terminal_pips"]
    terminal_ts = replay["terminal_ts"]

    # 24h expiry applied here, not inside replay engine
    if terminal_outcome is None and poll_now >= horizon:
        terminal_outcome = "CANCELLED"
        terminal_pips = 0.0
        terminal_ts = to_iso(horizon)

    updates: Dict[str, Any] = {
        "last_polled_at": poll_now_iso,
        "poll_count": int(shadow_row.get("poll_count") or 0) + 1,
        "highest_mfe_pips": replay["highest_mfe_pips"],
        "highest_mfe_r": replay["highest_mfe_r"],
        "last_error": None,
    }

    if replay["last_candle_ts"]:
        updates["last_candle_ts_processed"] = replay["last_candle_ts"]

    if replay["arm_triggered_this_run"]:
        updates.update({
            "arm_triggered": True,
            "arm_triggered_at": replay["arm_triggered_at"],
            "arm_candle_high": replay["arm_candle_high"],
            "arm_candle_low": replay["arm_candle_low"],
            "shadow_state": "ARMED",
        })

    if terminal_outcome is not None:
        updates.update({
            "shadow_state": "CLOSED",
            "shadow_outcome": terminal_outcome,
            "shadow_pips": terminal_pips,
            "shadow_closed_at": terminal_ts,
        })
        log.info("[CLOSE] %s policy=%-14s outcome=%-12s pips=%s",
                 signal_id[:8], policy, terminal_outcome, terminal_pips)

    update_shadow_row(signal_id, policy, updates)

# ---------------------------------------------------------------------------
# RECONCILIATION PASS
# ---------------------------------------------------------------------------

def reconcile_orphaned_shadow_rows(
    policy: str,
    terminal_map: Dict[str, Dict[str, Any]],
    poll_now: datetime,
    poll_now_iso: str,
) -> None:
    """
    Finds shadow rows still in TRACKING or ARMED whose production signal
    is already terminal. Replays OANDA candles only up to production closed_at.

    FIRST-RUN ANCHOR FIX:
      fetch_from = last_candle_ts_processed + 15min  if set
      fetch_from = prod["created_at"]                 if null
      last_polled_at is NEVER used as replay anchor here.

    COOLDOWN: rows with last_error starting "reconcile_unresolved" are skipped
    if last_polled_at is within RECONCILE_COOLDOWN_MIN.

    MAX-AGE: rows older than RECONCILE_MAX_AGE_HRS are permanently abandoned.

    UNRESOLVED CASES (A/B/C):
      Leave shadow_state open. Set last_error. Backfill actual_*.
      replay is only referenced after confirmed non-empty candles list.
    """
    open_rows = fetch_open_shadow_rows(policy)
    if not open_rows:
        return

    reconcilable = [r for r in open_rows if str(r["signal_id"]) in terminal_map]
    if not reconcilable:
        return

    log.info("[RECONCILE] policy=%s: %d candidate rows", policy, len(reconcilable))
    skipped_cooldown = 0
    processed = 0

    for shadow_row in reconcilable:
        signal_id = str(shadow_row["signal_id"])
        prod = terminal_map[signal_id]

        # Max-age check -- abandon permanently if signal is too old
        signal_created_raw = prod.get("created_at") or shadow_row.get("signal_created_at")
        if signal_created_raw:
            try:
                age_hours = (poll_now - parse_ts(signal_created_raw)).total_seconds() / 3600.0
                if age_hours > RECONCILE_MAX_AGE_HRS:
                    update_shadow_row(signal_id, policy, {
                        "shadow_state": "CLOSED",
                        "actual_outcome": prod.get("status"),
                        "actual_pips": prod.get("result_pips"),
                        "actual_closed_at": prod.get("closed_at"),
                        "last_error": (
                            f"reconcile_abandoned: signal age {age_hours:.0f}h "
                            f"> RECONCILE_MAX_AGE_HRS={RECONCILE_MAX_AGE_HRS}h"
                        ),
                        "last_polled_at": poll_now_iso,
                    })
                    log.warning("[RECONCILE] %s abandoned: age %.0fh > max %dh",
                                signal_id[:8], age_hours, RECONCILE_MAX_AGE_HRS)
                    continue
            except Exception:
                pass

        # Cooldown check -- skip recently-failed unresolved rows
        last_error = shadow_row.get("last_error") or ""
        if last_error.startswith("reconcile_unresolved"):
            last_polled_raw = shadow_row.get("last_polled_at")
            if last_polled_raw:
                try:
                    minutes_since = (poll_now - parse_ts(last_polled_raw)).total_seconds() / 60.0
                    if minutes_since < RECONCILE_COOLDOWN_MIN:
                        skipped_cooldown += 1
                        log.debug("[RECONCILE] %s cooldown: %.0f min remaining",
                                  signal_id[:8], RECONCILE_COOLDOWN_MIN - minutes_since)
                        continue
                except Exception:
                    pass

        prod_closed_at_raw = prod.get("closed_at")
        if not prod_closed_at_raw:
            log.warning("[RECONCILE] %s no closed_at on prod -- skipping", signal_id[:8])
            continue
        try:
            prod_closed_at = parse_ts(prod_closed_at_raw)
        except Exception:
            log.warning("[RECONCILE] %s unparseable closed_at -- skipping", signal_id[:8])
            continue

        actual_base: Dict[str, Any] = {
            "actual_outcome": prod.get("status"),
            "actual_pips": prod.get("result_pips"),
            "actual_closed_at": prod_closed_at_raw,
            "last_polled_at": poll_now_iso,
        }

        pair = str(prod["pair"])
        direction = str(prod["direction"]).upper()
        entry = float(prod["entry_price"])
        sl = float(prod["stop_loss"])
        tp = float(prod["take_profit"])
        risk_pips = float(shadow_row.get("risk_pips") or pips_between(entry, sl, pair))

        # Candle fetch boundary -- created_at is the ONLY first-run anchor
        last_candle_raw = shadow_row.get("last_candle_ts_processed")
        if last_candle_raw:
            fetch_from = parse_ts(last_candle_raw) + timedelta(minutes=15)
        else:
            # last_polled_at is NOT used -- it reflects a wall-clock poll timestamp,
            # not a candle boundary.
            fetch_from = parse_ts(prod["created_at"])

        fetch_to = prod_closed_at

        # Case A: window too small -- no fetch attempt
        if fetch_from >= fetch_to:
            update_shadow_row(signal_id, policy, {
                **actual_base,
                "last_error": (
                    f"reconcile_unresolved: candle window empty "
                    f"({to_iso(fetch_from)} >= {to_iso(fetch_to)})"
                ),
            })
            log.warning("[RECONCILE] %s policy=%s UNRESOLVED-A: empty window",
                        signal_id[:8], policy)
            processed += 1
            continue

        # Case B: OANDA returned no candles
        candles = fetch_m15_candles(pair, fetch_from, fetch_to)
        if not candles:
            update_shadow_row(signal_id, policy, {
                **actual_base,
                "last_error": (
                    f"reconcile_unresolved: no OANDA candles "
                    f"[{to_iso(fetch_from)}->{to_iso(fetch_to)}]"
                ),
            })
            log.warning("[RECONCILE] %s policy=%s UNRESOLVED-B: no candles",
                        signal_id[:8], policy)
            processed += 1
            continue

        # replay only reached after confirmed non-empty candles
        replay = replay_candles(
            candles=candles,
            policy=policy,
            entry=entry,
            sl=sl,
            tp=tp,
            direction=direction,
            pair=pair,
            risk_pips=risk_pips,
            already_armed=bool(shadow_row.get("arm_triggered") or False),
            highest_mfe_pips=float(shadow_row.get("highest_mfe_pips") or 0.0),
            highest_mfe_r=float(shadow_row.get("highest_mfe_r") or 0.0),
        )

        mfe_arm_updates: Dict[str, Any] = {
            "highest_mfe_pips": replay["highest_mfe_pips"],
            "highest_mfe_r": replay["highest_mfe_r"],
        }
        if replay["last_candle_ts"]:
            mfe_arm_updates["last_candle_ts_processed"] = replay["last_candle_ts"]
        if replay["arm_triggered_this_run"]:
            mfe_arm_updates.update({
                "arm_triggered": True,
                "arm_triggered_at": replay["arm_triggered_at"],
                "arm_candle_high": replay["arm_candle_high"],
                "arm_candle_low": replay["arm_candle_low"],
                "shadow_state": "ARMED",
            })

        # Case C: candles exhausted, no terminal event in window
        if replay["terminal_outcome"] is None:
            update_shadow_row(signal_id, policy, {
                **actual_base,
                **mfe_arm_updates,
                "last_error": (
                    "reconcile_unresolved: candles exhausted without terminal "
                    "event before production closed_at"
                ),
            })
            log.warning("[RECONCILE] %s policy=%s UNRESOLVED-C: no terminal in window",
                        signal_id[:8], policy)
            processed += 1
            continue

        # Terminal found -- close shadow row
        terminal_outcome = replay["terminal_outcome"]
        terminal_pips = float(replay["terminal_pips"])
        actual_pips = prod.get("result_pips")
        delta: Optional[float] = None
        try:
            if actual_pips is not None:
                delta = round(terminal_pips - float(actual_pips), 1)
        except Exception:
            delta = None

        update_shadow_row(signal_id, policy, {
            **actual_base,
            **mfe_arm_updates,
            "shadow_state": "CLOSED",
            "shadow_outcome": terminal_outcome,
            "shadow_pips": terminal_pips,
            "shadow_closed_at": replay["terminal_ts"],
            "delta_pips": delta,
            "last_error": None,
        })
        log.info("[RECONCILE] %s policy=%-14s outcome=%-12s shadow=%.1f actual=%s delta=%s",
                 signal_id[:8], policy, terminal_outcome, terminal_pips, actual_pips, delta)
        processed += 1

    if skipped_cooldown:
        log.info("[RECONCILE] policy=%s: %d processed, %d skipped(cooldown)",
                 policy, processed, skipped_cooldown)

# ---------------------------------------------------------------------------
# BACKFILL ACTUAL OUTCOMES  (with STATIC_MIRROR divergence alarm)
# ---------------------------------------------------------------------------

def backfill_actual_outcomes(terminal_map: Dict[str, Dict[str, Any]]) -> None:
    """
    For shadow rows already CLOSED but missing actual_outcome,
    backfills from terminal_map (pre-fetched in main -- no extra Supabase call).

    STATIC_MIRROR divergence alarm:
    If STATIC_MIRROR shadow_pips diverges from actual_pips by more than
    MIRROR_DIV_THRESHOLD, logs WARNING. This is the canary for OANDA vs
    production data mismatch. If triggered, BE_1.0R results are unreliable
    until the divergence source is identified.
    """
    if not terminal_map:
        return
    ids_csv = ",".join(terminal_map.keys())
    try:
        rows = sb_get("shadow_log", {
            "signal_id": f"in.({ids_csv})",
            "actual_outcome": "is.null",
            "shadow_state": "eq.CLOSED",
            "select": "signal_id,policy,shadow_pips",
        })
    except Exception as exc:
        log.error("backfill_actual_outcomes query failed: %s", exc)
        return

    for row in rows:
        signal_id = str(row["signal_id"])
        actual = terminal_map.get(signal_id)
        if not actual:
            continue
        actual_pips = actual.get("result_pips")
        shadow_pips = row.get("shadow_pips")
        policy = str(row["policy"])
        delta: Optional[float] = None
        try:
            if shadow_pips is not None and actual_pips is not None:
                delta = round(float(shadow_pips) - float(actual_pips), 1)
        except Exception:
            delta = None

        # STATIC_MIRROR canary alarm
        if policy == "STATIC_MIRROR" and delta is not None:
            divergence = abs(delta)
            if divergence > MIRROR_DIV_THRESHOLD:
                log.warning(
                    "MIRROR_DIVERGENCE signal=%s shadow=%.1fpips actual=%.1fpips "
                    "divergence=%.1fpips (threshold=%.1f) -- "
                    "OANDA vs production data mismatch; "
                    "BE_1.0R results unreliable until resolved.",
                    signal_id[:8], float(shadow_pips), float(actual_pips),
                    divergence, MIRROR_DIV_THRESHOLD,
                )

        update_shadow_row(signal_id, policy, {
            "actual_outcome": actual.get("status"),
            "actual_pips": actual_pips,
            "actual_closed_at": actual.get("closed_at"),
            "delta_pips": delta,
        })

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    check_heartbeat()

    if not SHADOW_ENABLED:
        log.info("SHADOW_ENABLED=false -> exiting")
        write_heartbeat("DISABLED", "shadow disabled")
        return

    if not validate_config():
        write_heartbeat("ERROR", "config validation failed -- see shadow_manager.log")
        sys.exit(1)

    if not check_schema_compatibility():
        write_heartbeat("ERROR", "schema compatibility check failed -- see shadow_manager.log")
        sys.exit(1)

    started = now_utc()
    started_iso = to_iso(started)

    log.info("=" * 60)
    log.info(
        "Shadow Manager v4.0 | OANDA_MODE=%s | BE_R=%s | "
        "MIRROR_THRESHOLD=%.1fpips | RECONCILE_COOLDOWN=%dmin | MAX_AGE=%dh",
        OANDA_MODE, BE_R_THRESHOLD, MIRROR_DIV_THRESHOLD,
        RECONCILE_COOLDOWN_MIN, RECONCILE_MAX_AGE_HRS,
    )
    log.info("=" * 60)

    # Single terminal fetch -- shared by backfill AND reconciliation
    recently_terminal = fetch_recently_terminal()
    terminal_map: Dict[str, Dict[str, Any]] = {
        str(r["id"]): r for r in recently_terminal
    }
    log.info("Terminal signals in lookback window: %d", len(terminal_map))

    # Backfill actual outcomes on already-closed shadow rows
    backfill_actual_outcomes(terminal_map)

    # Reconcile orphaned shadow rows (open in shadow, terminal in prod)
    for policy in POLICIES:
        try:
            reconcile_orphaned_shadow_rows(policy, terminal_map, started, started_iso)
        except Exception:
            log.exception("reconcile_orphaned_shadow_rows failed policy=%s", policy)

    # Process currently active production signals
    active = fetch_active_signals()
    log.info("Active production signals: %d", len(active))

    if not active:
        write_heartbeat("OK", "0 active signals")
        log.info("Shadow Manager done | 0 active signals")
        return

    signal_ids = [str(sig["id"]) for sig in active]

    for policy in POLICIES:
        existing = fetch_shadow_rows_by_ids(signal_ids, policy)
        log.info("--- Policy: %s ---", policy)

        for sig in active:
            signal_id = str(sig["id"])
            shadow_row = existing.get(signal_id)

            if shadow_row is None:
                try:
                    shadow_row = ensure_shadow_row(sig, policy, started_iso)
                except RuntimeError as exc:
                    log.error("UNIQUE CONTRACT ERROR: %s", exc)
                    write_heartbeat("ERROR", "uniqueness contract check failed -- see shadow_manager.log")
                    sys.exit(1)

            if not shadow_row:
                log.error("Could not ensure shadow row %s/%s", signal_id, policy)
                continue

            if str(shadow_row.get("shadow_state")) == "CLOSED":
                continue

            try:
                process_active_signal(sig, shadow_row, policy, started, started_iso)
            except Exception:
                log.exception("process_active_signal failed %s/%s", signal_id, policy)
                update_shadow_row(signal_id, policy, {
                    "last_polled_at": started_iso,
                    "last_error": "exception in process_active_signal -- see log",
                    "poll_count": int(shadow_row.get("poll_count") or 0) + 1,
                })

    elapsed = (now_utc() - started).total_seconds()
    write_heartbeat("OK", f"{len(active)} active | {elapsed:.1f}s")
    log.info("Shadow Manager done | %.1fs", elapsed)


if __name__ == "__main__":
    main()
