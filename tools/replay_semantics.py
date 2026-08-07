#!/usr/bin/env python3
"""Pure deterministic reconstruction of BotA production signal semantics.

This module is replay-only. It performs no network I/O and writes no runtime
state. Indicator, quality-filter, and S/R math are delegated to the production
Python modules from the same source tree; shell orchestration semantics that
depend on wall-clock/network state are reconstructed with explicit historical
inputs.
"""

from __future__ import annotations

import bisect
import csv
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import build_indicators as indicators
import quality_filter
import sr_score


UTC = timezone.utc
TF_SECONDS = {"M15": 900, "H1": 3600, "H4": 14400, "D1": 86400}

# Frozen source blobs inspected before this replay implementation.
PRODUCTION_SOURCE_BLOBS = {
    "tools/scoring_engine.sh": "09c42362a5c3c679696e86d4131ce5dfabd86608",
    "tools/m15_h1_fusion.sh": "c1de0312ed928f870b9a45df109b730d30888ee7",
    "tools/quality_filter.py": "18b76f908652d483c115c930373972836cea81dc",
    "tools/build_indicators.py": "2abce4a325d6d9da8bb0958b97a651d4288e1792",
    "tools/sr_score.py": "616b996a8ce439a19483762645a2247ca96fd066",
    "tools/market_open.sh": "a73ca97f3a63c3245311585e231e5e69eaffc506",
    "tools/emit_snapshot.py": "425c9adace57956981cf7e3111fd5df504c4f1ca",
}


@dataclass(frozen=True)
class ReplayConfig:
    """Frozen effective production settings needed by replay semantics."""

    filter_score_min: float = 65.0
    h1_trend_min_score: float = 40.0
    h1_veto_override_score: float = 75.0
    h1_veto_override_adx: float = 40.0
    scalp_sl_atr_mult: float = 2.0
    scalp_tp_atr_mult: float = 4.0
    max_sl_pips: float = 30.0
    max_tp_pips: float = 60.0
    macro6: int = 3
    d1_filter_mode: str = "ANY"


@dataclass(frozen=True)
class Candle:
    """Canonical replay candle with provider start timestamp."""

    time: datetime
    open: float
    high: float
    low: float
    close: float

    def as_indicator_dict(self) -> dict[str, float]:
        return {
            "time": float(self.time.timestamp()),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }


def parse_utc(value: str) -> datetime:
    """Parse ISO timestamp and normalize to UTC."""
    parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def iso_z(value: datetime) -> str:
    """Render canonical UTC Z timestamp."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_csv_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def load_candle_csv(path: Path) -> list[Candle]:
    """Load the five-column immutable replay candle format."""
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["time", "open", "high", "low", "close"]:
            raise ValueError(f"unexpected replay CSV header: {path}")
        for row in reader:
            candle = Candle(
                time=_parse_csv_time(row["time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
            )
            candles.append(candle)
    if not candles:
        raise ValueError(f"no candles in {path}")
    if any(left.time >= right.time for left, right in zip(candles, candles[1:])):
        raise ValueError(f"timestamps are not strictly increasing: {path}")
    return candles


def candle_completion(candle: Candle, timeframe: str) -> datetime:
    """Historical completion instant used to prevent replay look-ahead."""
    return candle.time + timedelta(seconds=TF_SECONDS[timeframe])


class HistoricalSeries:
    """Indexed candle stream that returns only candles complete by decision time."""

    def __init__(self, pair: str, timeframe: str, candles: Sequence[Candle]) -> None:
        if timeframe not in TF_SECONDS:
            raise ValueError(f"unsupported timeframe: {timeframe}")
        self.pair = pair
        self.timeframe = timeframe
        self.candles = list(candles)
        self._complete_epochs = [
            candle_completion(candle, timeframe).timestamp() for candle in self.candles
        ]
        self._bundle_cache: dict[int, dict[str, Any]] = {}
        self._levels_cache: dict[int, tuple[list[float], list[float]]] = {}

    def completed_count(self, decision_time: datetime) -> int:
        return bisect.bisect_right(self._complete_epochs, decision_time.timestamp())

    def completed_candles(
        self, decision_time: datetime, *, limit: int | None = None
    ) -> list[Candle]:
        count = self.completed_count(decision_time)
        start = max(0, count - limit) if limit else 0
        return self.candles[start:count]

    def indicator_bundle(self, decision_time: datetime) -> dict[str, Any]:
        count = self.completed_count(decision_time)
        if count <= 0:
            return indicators.build_bundle(self.pair, self.timeframe, [])
        if count not in self._bundle_cache:
            start = max(0, count - 500)
            raw = [
                candle.as_indicator_dict() for candle in self.candles[start:count]
            ]
            self._bundle_cache[count] = indicators.build_bundle(
                self.pair, self.timeframe, raw
            )
        return dict(self._bundle_cache[count])

    def sr_levels(self, decision_time: datetime) -> tuple[list[float], list[float]]:
        count = self.completed_count(decision_time)
        if count not in self._levels_cache:
            recent = self.candles[max(0, count - 100):count]
            records = [
                {"h": candle.high, "l": candle.low, "c": candle.close}
                for candle in recent
            ]
            resistances, supports = sr_score.detect_swing_levels(
                records, lookback=100, window=3
            )
            pip = 0.01 if "JPY" in self.pair else 0.0001
            self._levels_cache[count] = (
                sr_score.merge_levels(resistances, merge_pips=10 * pip),
                sr_score.merge_levels(supports, merge_pips=10 * pip),
            )
        resistance, support = self._levels_cache[count]
        return list(resistance), list(support)


def market_open_at(decision_time: datetime) -> bool:
    """Reproduce market_open.sh with SKIP_SESSION_FILTER=0."""
    stamp = decision_time.astimezone(UTC)
    if stamp.isoweekday() >= 6:
        return False
    minute = stamp.hour * 60 + stamp.minute
    return 7 * 60 <= minute < 20 * 60


def scoring_session(decision_time: datetime) -> tuple[float, str]:
    """Reproduce scoring_engine.sh session component from historical UTC."""
    stamp = decision_time.astimezone(UTC)
    hour = stamp.hour + stamp.minute / 60.0
    if 12.0 <= hour < 16.0:
        return 5.0, "session_overlap"
    if 7.0 <= hour < 12.0:
        return 2.0, "session_london"
    if 16.0 <= hour < 20.0:
        return 2.0, "session_ny"
    return 0.0, "session_edge"


def snapshot_vote(bundle: Mapping[str, Any]) -> int:
    """Reproduce emit_snapshot.py vote formula using historical bundle values."""
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 50.0) or 50.0)
    macd_hist = float(bundle.get("macd_hist", 0.0) or 0.0)
    ema_vote = 1 if ema9 > ema21 else -1 if ema9 < ema21 else 0
    rsi_vote = 1 if rsi > 55 else -1 if rsi < 45 else 0
    macd_vote = 1 if macd_hist > 0 else -1 if macd_hist < 0 else 0
    return ema_vote + rsi_vote + macd_vote


def h4_direction(bundle: Mapping[str, Any]) -> str:
    """Reproduce fusion's cached H4 EMA-only direction."""
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    if ema9 < ema21:
        return "SELL"
    if ema9 > ema21:
        return "BUY"
    return "HOLD"


def _volatility_bucket(atr: float, price: float) -> str:
    if atr <= 0.0 or price <= 0.0:
        return "unknown"
    atr_pct = atr / price * 100.0
    if atr_pct < 0.05:
        return "low"
    if atr_pct < 0.15:
        return "normal"
    if atr_pct < 0.30:
        return "high"
    return "extreme"


def _d1_trend(bundle: Mapping[str, Any], mode: str) -> str:
    """Resolve deterministic D1 filter mode.

    ANY reproduces scoring_engine fail-open behavior when no runtime d1_trend
    cache is available. EMA is an explicit sensitivity mode, not baseline.
    """
    if mode.upper() == "ANY":
        return "ANY"
    if mode.upper() != "EMA":
        raise ValueError(f"unsupported d1_filter_mode: {mode}")
    return h4_direction(bundle)


def _pullback_direction(bundle: Mapping[str, Any], d1_trend: str) -> tuple[str, str]:
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 0.0) or 0.0)
    atr = float(bundle.get("atr", 0.0) or 0.0)
    low = float(bundle.get("low", 0.0) or 0.0)
    high = float(bundle.get("high", 0.0) or 0.0)
    close = float(bundle.get("close", 0.0) or 0.0)
    bullish = ema9 > ema21 and rsi > 50
    bearish = ema9 < ema21 and rsi < 50
    pb_buffer = atr * 1.0 if atr > 0 else 0.0012
    buy = (
        bullish
        and low <= ema21 + pb_buffer
        and close > ema21 - atr * 0.3
        and rsi > 45
    )
    sell = (
        bearish
        and high >= ema21 - pb_buffer
        and close < ema21 + atr * 0.3
        and rsi < 55
    )
    direction = "BUY" if buy else "SELL" if sell else "HOLD"
    if d1_trend != "ANY":
        if direction == "BUY" and d1_trend == "SELL":
            direction = "HOLD"
        elif direction == "SELL" and d1_trend == "BUY":
            direction = "HOLD"
    tag = "pullback_entry" if direction != "HOLD" else "no_pullback"
    return direction, tag


def _component_scores(
    bundle: Mapping[str, Any],
    direction: str,
    decision_time: datetime,
    sr_comp: float,
) -> dict[str, Any]:
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 0.0) or 0.0)
    macd_hist = float(bundle.get("macd_hist", 0.0) or 0.0)
    adx = float(bundle.get("adx", 0.0) or 0.0)
    price = float(bundle.get("price", 0.0) or 0.0)

    ema_delta_pct = abs(ema9 - ema21) / ema21 * 100.0 if ema21 else 0.0
    ema_bps = ema_delta_pct * 100.0
    ema_comp = min(20.0, ema_bps)
    rsi_comp = min(15.0, abs(rsi - 50.0) * 0.6)

    if direction == "BUY":
        macd_comp = min(15.0, max(0.0, macd_hist * 100000.0)) if macd_hist > 0 else 0.0
    else:
        macd_comp = min(15.0, max(0.0, -macd_hist * 100000.0)) if macd_hist < 0 else 0.0

    if adx < 15.0:
        adx_comp = 0.0
    elif adx < 20.0:
        adx_comp = 3.0
    elif adx < 25.0:
        adx_comp = 6.0
    elif adx < 30.0:
        adx_comp = 8.0
    else:
        adx_comp = 10.0

    upper = float(bundle.get("bb_upper", 0.0) or 0.0)
    middle = float(bundle.get("bb_middle", 0.0) or 0.0)
    lower = float(bundle.get("bb_lower", 0.0) or 0.0)
    squeeze = bool(bundle.get("bb_squeeze", False))
    bb_comp = 0.0
    bb_tag = "bb_neutral"
    if upper > 0 and lower > 0 and middle > 0:
        if squeeze:
            bb_comp, bb_tag = -3.0, "bb_squeeze"
        elif direction == "SELL" and price >= upper * 0.9998:
            bb_comp, bb_tag = 8.0, "bb_upper_sell"
        elif direction == "BUY" and price <= lower * 1.0002:
            bb_comp, bb_tag = 8.0, "bb_lower_buy"
        elif direction == "SELL" and price > middle:
            bb_comp, bb_tag = 3.0, "bb_above_mid_sell"
        elif direction == "BUY" and price < middle:
            bb_comp, bb_tag = 3.0, "bb_below_mid_buy"
        else:
            bb_comp, bb_tag = -5.0, "bb_counter"

    session_comp, session_tag = scoring_session(decision_time)
    return {
        "ema_bps": ema_bps,
        "ema_comp": ema_comp,
        "rsi_comp": rsi_comp,
        "macd_comp": macd_comp,
        "adx_comp": adx_comp,
        "bb_comp": bb_comp,
        "bb_tag": bb_tag,
        "session_comp": session_comp,
        "session_tag": session_tag,
        "vol_comp": 0.0,
        "vol_tag": "vol_normal",
        "sr_comp": float(sr_comp),
    }


def _stop_target(
    pair: str,
    direction: str,
    price: float,
    atr: float,
    config: ReplayConfig,
) -> tuple[float, float]:
    if direction not in {"BUY", "SELL"} or price <= 0 or atr <= 0:
        return 0.0, 0.0
    pip = 0.01 if "JPY" in pair else 0.0001
    sl_dist = min(atr * config.scalp_sl_atr_mult, config.max_sl_pips * pip)
    tp_dist = min(atr * config.scalp_tp_atr_mult, config.max_tp_pips * pip)
    if direction == "BUY":
        return round(price - sl_dist, 5), round(price + tp_dist, 5)
    return round(price + sl_dist, 5), round(price - tp_dist, 5)


def score_bundle(
    pair: str,
    timeframe: str,
    bundle: Mapping[str, Any],
    *,
    decision_time: datetime,
    sr_comp: float,
    d1_bundle: Mapping[str, Any],
    config: ReplayConfig,
) -> dict[str, Any]:
    """Replay scoring_engine.sh without wall-clock/network/filesystem side effects."""
    price = float(bundle.get("price", 0.0) or 0.0)
    atr = float(bundle.get("atr", 0.0) or 0.0)
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 0.0) or 0.0)
    macd_hist = float(bundle.get("macd_hist", 0.0) or 0.0)
    adx = float(bundle.get("adx", 0.0) or 0.0)
    vol = _volatility_bucket(atr, price)

    if bundle.get("tf_ok", True) is False or bundle.get("error") == "tf_mismatch":
        return _hold(pair, timeframe, "tf_mismatch_detected", price=0.0, atr=0.0)

    missing = []
    if ema9 <= 0:
        missing.append("ema9_missing")
    if ema21 <= 0:
        missing.append("ema21_missing")
    if rsi <= 0:
        missing.append("rsi_missing")
    if price <= 0:
        missing.append("price_missing")
    if missing:
        return _hold(
            pair,
            timeframe,
            ",".join(["indicators_missing", *missing]),
            price=0.0,
            atr=atr,
        )

    d1_trend = _d1_trend(d1_bundle, config.d1_filter_mode)
    direction, pullback_tag = _pullback_direction(bundle, d1_trend)
    if direction == "HOLD":
        return _hold(
            pair,
            timeframe,
            "no_signal|phase=Open",
            price=price,
            atr=atr,
            volatility=vol,
            extra={"d1_trend": d1_trend},
        )

    comps = _component_scores(bundle, direction, decision_time, sr_comp)
    if adx < 20.0:
        return _hold(
            pair,
            timeframe,
            f"adx_regime_block|adx={adx:.1f}|ranging_market",
            price=0.0,
            atr=0.0,
            volatility=0.0,
            filter_reasons=["adx_regime"],
            extra={
                "adx_raw": adx,
                "rsi_raw": rsi,
                "macd_hist_raw": macd_hist,
                **comps,
                "d1_trend": d1_trend,
            },
        )

    score = (
        40.0
        + comps["ema_comp"]
        + comps["rsi_comp"]
        + comps["macd_comp"]
        + comps["adx_comp"]
        + comps["bb_comp"]
        + comps["session_comp"]
        + comps["vol_comp"]
        + comps["sr_comp"]
    )
    score = max(0.0, min(100.0, score))
    sl, tp = _stop_target(pair, direction, price, atr, config)
    reasons = "|".join(
        [
            "ok",
            f"ema_bps={comps['ema_bps']:.1f}",
            f"rsi={rsi:.1f}",
            f"macd_hist={macd_hist:.6f}",
            f"adx={adx:.1f}",
            f"ema_comp={comps['ema_comp']:.1f}",
            f"rsi_comp={comps['rsi_comp']:.1f}",
            f"macd_comp={comps['macd_comp']:.1f}",
            f"adx_comp={comps['adx_comp']:.1f}",
            f"bb_comp={comps['bb_comp']:.1f}",
            f"bb={comps['bb_tag']}",
            f"session_comp={comps['session_comp']:.1f}",
            f"session={comps['session_tag']}",
            f"vol_comp={comps['vol_comp']:.1f}",
            f"vol={comps['vol_tag']}",
            f"sr_comp={comps['sr_comp']:.1f}",
            "phase=Open",
            pullback_tag,
            f"d1_filter={d1_trend}",
        ]
    )
    return {
        "pair": pair,
        "tf": timeframe,
        "direction": direction,
        "entry": float(price),
        "sl": sl,
        "tp": tp,
        "volatility": vol,
        "score": round(score, 1),
        "confidence": round(score, 1),
        "reasons": reasons,
        "price": float(price),
        "provider": "engine_A3_replay",
        "atr": float(atr),
        "filter_rr": 0.0,
        "filter_atr": 0.0,
        "filter_rejected": False,
        "filter_reasons": [],
        "pattern_delta": 0,
        "adx_raw": adx,
        "rsi_raw": rsi,
        "macd_hist_raw": macd_hist,
        **comps,
        "d1_trend": d1_trend,
    }


def _hold(
    pair: str,
    timeframe: str,
    reasons: str,
    *,
    price: float,
    atr: float,
    volatility: Any = "unknown",
    filter_reasons: Sequence[str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "pair": pair,
        "tf": timeframe,
        "direction": "HOLD",
        "entry": 0.0,
        "sl": 0.0,
        "tp": 0.0,
        "volatility": volatility,
        "score": 0.0,
        "confidence": 40.0,
        "reasons": reasons,
        "price": float(price),
        "provider": "engine_A3_replay",
        "atr": float(atr),
        "filter_rr": 0.0,
        "filter_atr": 0.0,
        "filter_rejected": True,
        "filter_reasons": list(filter_reasons or ["no_signal"]),
        "pattern_delta": 0,
    }
    if extra:
        out.update(extra)
    return out


@contextmanager
def _quality_environment(config: ReplayConfig) -> Iterator[None]:
    keys = {
        "FILTER_SCORE_MIN_ALL": str(config.filter_score_min),
        "SCALP_SL_ATR_MULT": str(config.scalp_sl_atr_mult),
        "SCALP_TP_ATR_MULT": str(config.scalp_tp_atr_mult),
        "FILTER_RR_MIN": "1.66",
        "EXTENDED_MOVE_ATR_MULT": "0",
        "EXTENDED_MOVE_HARD_REJECT": "0",
        "TREND_OPPOSITE_PENALTY": "0.85",
    }
    prior = {key: os.environ.get(key) for key in keys}
    os.environ.update(keys)
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def quality_apply(signal: Mapping[str, Any], config: ReplayConfig) -> dict[str, Any]:
    with _quality_environment(config):
        return quality_filter.apply_filters(dict(signal))


def sr_component(
    h1_series: HistoricalSeries,
    decision_time: datetime,
    direction: str,
    price: float,
    atr: float,
) -> int:
    if direction not in {"BUY", "SELL"}:
        return 0
    resistances, supports = h1_series.sr_levels(decision_time)
    return sr_score.score_sr_proximity(
        price, direction, atr, resistances, supports
    )


def preliminary_direction(bundle: Mapping[str, Any]) -> str:
    """Direction used by scoring_engine.sh before calling sr_score.py."""
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 50.0) or 50.0)
    if ema9 > ema21 and rsi > 50:
        return "BUY"
    if ema9 < ema21 and rsi < 50:
        return "SELL"
    return "HOLD"


def _h4_opposes(m15_direction: str, h4_dir: str) -> bool:
    return (
        (m15_direction == "BUY" and h4_dir == "SELL")
        or (m15_direction == "SELL" and h4_dir == "BUY")
    )


def _h4_break_override(
    pair: str,
    m15_direction: str,
    m15_score: float,
    m15_price: float,
    h4_bundle: Mapping[str, Any],
) -> bool:
    if int(m15_score) < 90:
        return False
    ema21 = float(h4_bundle.get("ema21", 0.0) or 0.0)
    if ema21 <= 0 or m15_price <= 0:
        return False
    pip = 0.01 if "JPY" in pair else 0.0001
    if m15_direction == "BUY":
        return m15_price - ema21 >= 10 * pip
    if m15_direction == "SELL":
        return ema21 - m15_price >= 10 * pip
    return False


def _h1_fusion_decision(
    m15: Mapping[str, Any],
    h1: Mapping[str, Any],
    h4_bundle: Mapping[str, Any],
    config: ReplayConfig,
) -> tuple[str, bool]:
    m15_direction = str(m15.get("direction", "HOLD"))
    m15_score = float(m15.get("score", 0.0) or 0.0)
    h1_direction = str(h1.get("direction", "HOLD"))
    h1_score = float(h1.get("score", 0.0) or 0.0)
    h1_rejected = bool(h1.get("filter_rejected", False))
    h4_dir = h4_direction(h4_bundle)
    h4_opposing = _h4_opposes(m15_direction, h4_dir)
    if h4_opposing and _h4_break_override(
        str(m15.get("pair", "")),
        m15_direction,
        m15_score,
        float(m15.get("price", 0.0) or 0.0),
        h4_bundle,
    ):
        h4_opposing = False

    m15_score_int = int(m15_score)
    if h1_rejected:
        if (
            m15_score_int >= int(config.h1_veto_override_score)
            and not h4_opposing
        ):
            return "H1_trend_neutral_overridden", False
        return "H1_trend_neutral", True

    if h1_direction in {"BUY", "SELL"}:
        if int(h1_score) < int(config.h1_trend_min_score):
            return "H1_trend_weak", False
        if h1_direction == m15_direction:
            return "H1_trend_confirmed", False

        # Production fusion reads `.adx // 0` from scoring-engine JSON. The
        # current scoring-engine output has no top-level `adx`, so this value is
        # zero. Reproduce that behavior rather than substituting adx_raw.
        m15_adx_top_level = float(m15.get("adx", 0.0) or 0.0)
        if (
            m15_score_int >= int(config.h1_veto_override_score)
            and int(m15_adx_top_level) >= int(config.h1_veto_override_adx)
        ):
            return "H1_trend_opposite_overridden", False
        return "H1_trend_opposite", True

    if (
        m15_score_int >= int(config.h1_veto_override_score)
        and not h4_opposing
    ):
        return "H1_trend_neutral_overridden", False
    return "H1_trend_neutral", True


def policy_flags(signal: Mapping[str, Any]) -> dict[str, bool]:
    """Frozen A/B/C candidate policies selected before June-July replay."""
    accepted = (
        str(signal.get("direction", "HOLD")) in {"BUY", "SELL"}
        and not bool(signal.get("filter_rejected", True))
    )
    score = float(signal.get("score", 0.0) or 0.0)
    adx = float(signal.get("adx_raw", 0.0) or 0.0)
    rsi = float(signal.get("rsi_raw", 50.0) or 50.0)
    direction = str(signal.get("direction", "HOLD"))
    extreme = (
        (direction == "SELL" and rsi <= 30.0)
        or (direction == "BUY" and rsi >= 70.0)
    )
    return {
        "policy_a_current": accepted,
        "policy_b_score70_adx_lt30": accepted and score >= 70.0 and adx < 30.0,
        "policy_c_score70_adx_lt30_no_extreme": (
            accepted and score >= 70.0 and adx < 30.0 and not extreme
        ),
        "extreme_rsi": extreme,
    }


def replay_decision(
    *,
    pair: str,
    m15_candle: Candle,
    m15_series: HistoricalSeries,
    h1_series: HistoricalSeries,
    h4_series: HistoricalSeries,
    d1_series: HistoricalSeries,
    config: ReplayConfig,
) -> dict[str, Any]:
    """Replay one M15 decision at the close of the supplied candle."""
    decision_time = candle_completion(m15_candle, "M15")
    base = {
        "pair": pair,
        "m15_candle_time": iso_z(m15_candle.time),
        "decision_time": iso_z(decision_time),
        "market_open": market_open_at(decision_time),
    }
    if not market_open_at(decision_time):
        return {
            **base,
            "direction": "HOLD",
            "score": 0.0,
            "filter_rejected": True,
            "filter_reasons": ["market_phase_Closed"],
            "reject_stage": "MARKET_ALLOWED",
            **policy_flags({}),
        }

    m15_bundle = m15_series.indicator_bundle(decision_time)
    h1_bundle = h1_series.indicator_bundle(decision_time)
    h4_bundle = h4_series.indicator_bundle(decision_time)
    d1_bundle = d1_series.indicator_bundle(decision_time)

    prelim = preliminary_direction(m15_bundle)
    sr_comp = sr_component(
        h1_series,
        decision_time,
        prelim,
        float(m15_bundle.get("price", 0.0) or 0.0),
        float(m15_bundle.get("atr", 0.0) or 0.0),
    )
    m15_scored = score_bundle(
        pair,
        "M15",
        m15_bundle,
        decision_time=decision_time,
        sr_comp=sr_comp,
        d1_bundle=d1_bundle,
        config=config,
    )
    m15_filtered = quality_apply(m15_scored, config)
    m15_filtered["macro6"] = config.macro6
    m15_filtered.setdefault("filter_reasons", []).append(f"macro6={config.macro6}")

    event = {
        **base,
        **m15_filtered,
        "sr_comp": sr_comp,
        "h1_trend": "not_evaluated",
        "h4_direction": h4_direction(h4_bundle),
        "h4_vote": snapshot_vote(h4_bundle),
        "d1_vote": snapshot_vote(d1_bundle),
        "reject_stage": "",
    }

    if (
        bool(m15_filtered.get("filter_rejected", False))
        or m15_filtered.get("direction") not in {"BUY", "SELL"}
    ):
        event["reject_stage"] = "M15_SETUP_OR_SCORE"
        event.update(policy_flags(event))
        return event

    h1_prelim = preliminary_direction(h1_bundle)
    h1_sr = sr_component(
        h1_series,
        decision_time,
        h1_prelim,
        float(h1_bundle.get("price", 0.0) or 0.0),
        float(h1_bundle.get("atr", 0.0) or 0.0),
    )
    h1_scored = score_bundle(
        pair,
        "H1",
        h1_bundle,
        decision_time=decision_time,
        sr_comp=h1_sr,
        d1_bundle=d1_bundle,
        config=config,
    )
    h1_filtered = quality_apply(h1_scored, config)

    trend_tag, veto = _h1_fusion_decision(
        m15_filtered, h1_filtered, h4_bundle, config
    )
    event["h1_trend"] = trend_tag
    event["h1_direction"] = h1_filtered.get("direction", "HOLD")
    event["h1_score"] = h1_filtered.get("score", 0.0)
    event["h1_filter_rejected"] = h1_filtered.get("filter_rejected", True)

    if veto:
        event["filter_rejected"] = True
        event.setdefault("filter_reasons", []).append(trend_tag)
        event["reject_stage"] = "H1_CONFIRM"
        event.update(policy_flags(event))
        return event

    direction = str(event.get("direction", "HOLD"))
    h4_vote = int(event["h4_vote"])
    d1_vote = int(event["d1_vote"])
    mtf_veto = (
        (direction == "BUY" and h4_vote < 0 and d1_vote < 0)
        or (direction == "SELL" and h4_vote > 0 and d1_vote > 0)
    )
    if mtf_veto:
        event["filter_rejected"] = True
        event.setdefault("filter_reasons", []).append("H4_D1_oppose")
        event["reject_stage"] = "H4_D1_CONFIRM"
    else:
        event.setdefault("filter_reasons", []).append(trend_tag)
        event["reject_stage"] = "ACCEPTED"

    event.update(policy_flags(event))
    return event
