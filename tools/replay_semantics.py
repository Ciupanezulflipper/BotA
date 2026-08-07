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
            candles.append(
                Candle(
                    time=_parse_csv_time(row["time"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                )
            )
    if not candles:
        raise ValueError(f"no candles in {path}")
    if any(left.time >= right.time for left, right in zip(candles, candles[1:])):
        raise ValueError(f"timestamps are not strictly increasing: {path}")
    return candles


def candle_completion(candle: Candle, timeframe: str) -> datetime:
    """Historical completion instant used to prevent replay look-ahead."""
    return candle.time + timedelta(seconds=TF_SECONDS[timeframe])


class HistoricalSeries:
    """Indexed candle stream exposing only candles complete by decision time."""

    def __init__(self, pair: str, timeframe: str, candles: Sequence[Candle]) -> None:
        if timeframe not in TF_SECONDS:
            raise ValueError(f"unsupported timeframe: {timeframe}")
        self.pair = pair
        self.timeframe = timeframe
        self.candles = list(candles)
        self._complete_epochs = [
            candle_completion(candle, timeframe).timestamp()
            for candle in self.candles
        ]
        self._bundle_cache: dict[int, dict[str, Any]] = {}
        self._levels_cache: dict[int, tuple[list[float], list[float]]] = {}

    def completed_count(self, decision_time: datetime) -> int:
        return bisect.bisect_right(
            self._complete_epochs, decision_time.timestamp()
        )

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
                candle.as_indicator_dict()
                for candle in self.candles[start:count]
            ]
            self._bundle_cache[count] = indicators.build_bundle(
                self.pair, self.timeframe, raw
            )
        return dict(self._bundle_cache[count])

    def sr_levels(
        self, decision_time: datetime
    ) -> tuple[list[float], list[float]]:
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
        resistances, supports = self._levels_cache[count]
        return list(resistances), list(supports)


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


def _sign_vote(positive: bool, negative: bool) -> int:
    if positive:
        return 1
    if negative:
        return -1
    return 0


def snapshot_vote(bundle: Mapping[str, Any]) -> int:
    """Reproduce emit_snapshot.py vote formula using historical bundle values."""
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 50.0) or 50.0)
    macd_hist = float(bundle.get("macd_hist", 0.0) or 0.0)
    ema_vote = _sign_vote(ema9 > ema21, ema9 < ema21)
    rsi_vote = _sign_vote(rsi > 55, rsi < 45)
    macd_vote = _sign_vote(macd_hist > 0, macd_hist < 0)
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
    normalized = mode.upper()
    if normalized == "ANY":
        return "ANY"
    if normalized == "EMA":
        return h4_direction(bundle)
    raise ValueError(f"unsupported d1_filter_mode: {mode}")


def _buy_pullback(
    *,
    ema9: float,
    ema21: float,
    rsi: float,
    atr: float,
    low: float,
    close: float,
    pb_buffer: float,
) -> bool:
    return (
        ema9 > ema21
        and rsi > 50
        and low <= ema21 + pb_buffer
        and close > ema21 - atr * 0.3
        and rsi > 45
    )


def _sell_pullback(
    *,
    ema9: float,
    ema21: float,
    rsi: float,
    atr: float,
    high: float,
    close: float,
    pb_buffer: float,
) -> bool:
    return (
        ema9 < ema21
        and rsi < 50
        and high >= ema21 - pb_buffer
        and close < ema21 + atr * 0.3
        and rsi < 55
    )


def _apply_d1_direction(direction: str, d1_trend: str) -> str:
    if d1_trend == "ANY":
        return direction
    opposite = (
        (direction == "BUY" and d1_trend == "SELL")
        or (direction == "SELL" and d1_trend == "BUY")
    )
    return "HOLD" if opposite else direction


def _pullback_direction(
    bundle: Mapping[str, Any], d1_trend: str
) -> tuple[str, str]:
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 0.0) or 0.0)
    atr = float(bundle.get("atr", 0.0) or 0.0)
    low = float(bundle.get("low", 0.0) or 0.0)
    high = float(bundle.get("high", 0.0) or 0.0)
    close = float(bundle.get("close", 0.0) or 0.0)
    pb_buffer = atr if atr > 0 else 0.0012

    direction = "HOLD"
    if _buy_pullback(
        ema9=ema9,
        ema21=ema21,
        rsi=rsi,
        atr=atr,
        low=low,
        close=close,
        pb_buffer=pb_buffer,
    ):
        direction = "BUY"
    elif _sell_pullback(
        ema9=ema9,
        ema21=ema21,
        rsi=rsi,
        atr=atr,
        high=high,
        close=close,
        pb_buffer=pb_buffer,
    ):
        direction = "SELL"

    direction = _apply_d1_direction(direction, d1_trend)
    tag = "pullback_entry" if direction != "HOLD" else "no_pullback"
    return direction, tag


def _ema_component(ema9: float, ema21: float) -> tuple[float, float]:
    if ema21 == 0:
        return 0.0, 0.0
    ema_delta_pct = abs(ema9 - ema21) / ema21 * 100.0
    ema_bps = ema_delta_pct * 100.0
    return ema_bps, min(20.0, ema_bps)


def _macd_component(direction: str, macd_hist: float) -> float:
    if direction == "BUY":
        aligned = macd_hist
    else:
        aligned = -macd_hist
    return min(15.0, max(0.0, aligned * 100000.0))


def _adx_component(adx: float) -> float:
    if adx < 15.0:
        return 0.0
    if adx < 20.0:
        return 3.0
    if adx < 25.0:
        return 6.0
    if adx < 30.0:
        return 8.0
    return 10.0


def _bb_component(
    bundle: Mapping[str, Any], direction: str, price: float
) -> tuple[float, str]:
    upper = float(bundle.get("bb_upper", 0.0) or 0.0)
    middle = float(bundle.get("bb_middle", 0.0) or 0.0)
    lower = float(bundle.get("bb_lower", 0.0) or 0.0)
    if upper <= 0 or lower <= 0 or middle <= 0:
        return 0.0, "bb_neutral"
    if bool(bundle.get("bb_squeeze", False)):
        return -3.0, "bb_squeeze"
    if direction == "SELL" and price >= upper * 0.9998:
        return 8.0, "bb_upper_sell"
    if direction == "BUY" and price <= lower * 1.0002:
        return 8.0, "bb_lower_buy"
    if direction == "SELL" and price > middle:
        return 3.0, "bb_above_mid_sell"
    if direction == "BUY" and price < middle:
        return 3.0, "bb_below_mid_buy"
    return -5.0, "bb_counter"


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

    ema_bps, ema_comp = _ema_component(ema9, ema21)
    bb_comp, bb_tag = _bb_component(bundle, direction, price)
    session_comp, session_tag = scoring_session(decision_time)
    return {
        "ema_bps": ema_bps,
        "ema_comp": ema_comp,
        "rsi_comp": min(15.0, abs(rsi - 50.0) * 0.6),
        "macd_comp": _macd_component(direction, macd_hist),
        "adx_comp": _adx_component(adx),
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
    sl_dist = min(
        atr * config.scalp_sl_atr_mult, config.max_sl_pips * pip
    )
    tp_dist = min(
        atr * config.scalp_tp_atr_mult, config.max_tp_pips * pip
    )
    if direction == "BUY":
        return round(price - sl_dist, 5), round(price + tp_dist, 5)
    return round(price + sl_dist, 5), round(price - tp_dist, 5)


def _missing_indicators(
    *, ema9: float, ema21: float, rsi: float, price: float
) -> list[str]:
    values = (
        ("ema9_missing", ema9),
        ("ema21_missing", ema21),
        ("rsi_missing", rsi),
        ("price_missing", price),
    )
    return [name for name, value in values if value <= 0]


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


def _score_total(comps: Mapping[str, Any]) -> float:
    score = 40.0
    for key in (
        "ema_comp",
        "rsi_comp",
        "macd_comp",
        "adx_comp",
        "bb_comp",
        "session_comp",
        "vol_comp",
        "sr_comp",
    ):
        score += float(comps[key])
    return max(0.0, min(100.0, score))


def _score_reasons(
    *,
    rsi: float,
    macd_hist: float,
    adx: float,
    comps: Mapping[str, Any],
    pullback_tag: str,
    d1_trend: str,
) -> str:
    return "|".join(
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


def _trade_signal(
    *,
    pair: str,
    timeframe: str,
    direction: str,
    price: float,
    atr: float,
    rsi: float,
    macd_hist: float,
    adx: float,
    vol: str,
    pullback_tag: str,
    d1_trend: str,
    comps: Mapping[str, Any],
    config: ReplayConfig,
) -> dict[str, Any]:
    score = _score_total(comps)
    sl, tp = _stop_target(pair, direction, price, atr, config)
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
        "reasons": _score_reasons(
            rsi=rsi,
            macd_hist=macd_hist,
            adx=adx,
            comps=comps,
            pullback_tag=pullback_tag,
            d1_trend=d1_trend,
        ),
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
    """Replay scoring_engine.sh without wall-clock/network/filesystem effects."""
    price = float(bundle.get("price", 0.0) or 0.0)
    atr = float(bundle.get("atr", 0.0) or 0.0)
    ema9 = float(bundle.get("ema9", 0.0) or 0.0)
    ema21 = float(bundle.get("ema21", 0.0) or 0.0)
    rsi = float(bundle.get("rsi", 0.0) or 0.0)
    macd_hist = float(bundle.get("macd_hist", 0.0) or 0.0)
    adx = float(bundle.get("adx", 0.0) or 0.0)
    vol = _volatility_bucket(atr, price)

    if bundle.get("tf_ok", True) is False or bundle.get("error") == "tf_mismatch":
        return _hold(
            pair, timeframe, "tf_mismatch_detected", price=0.0, atr=0.0
        )

    missing = _missing_indicators(
        ema9=ema9, ema21=ema21, rsi=rsi, price=price
    )
    if missing:
        reason = ",".join(["indicators_missing", *missing])
        return _hold(pair, timeframe, reason, price=0.0, atr=atr)

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

    return _trade_signal(
        pair=pair,
        timeframe=timeframe,
        direction=direction,
        price=price,
        atr=atr,
        rsi=rsi,
        macd_hist=macd_hist,
        adx=adx,
        vol=vol,
        pullback_tag=pullback_tag,
        d1_trend=d1_trend,
        comps=comps,
        config=config,
    )


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


def quality_apply(
    signal: Mapping[str, Any], config: ReplayConfig
) -> dict[str, Any]:
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


def _effective_h4_opposition(
    m15: Mapping[str, Any], h4_bundle: Mapping[str, Any]
) -> bool:
    m15_direction = str(m15.get("direction", "HOLD"))
    h4_opposing = _h4_opposes(m15_direction, h4_direction(h4_bundle))
    if not h4_opposing:
        return False
    overridden = _h4_break_override(
        str(m15.get("pair", "")),
        m15_direction,
        float(m15.get("score", 0.0) or 0.0),
        float(m15.get("price", 0.0) or 0.0),
        h4_bundle,
    )
    return not overridden


def _neutral_h1_decision(
    m15_score: float, h4_opposing: bool, config: ReplayConfig
) -> tuple[str, bool]:
    high_score = int(m15_score) >= int(config.h1_veto_override_score)
    if high_score and not h4_opposing:
        return "H1_trend_neutral_overridden", False
    return "H1_trend_neutral", True


def _tradeable_h1_decision(
    m15: Mapping[str, Any],
    h1: Mapping[str, Any],
    config: ReplayConfig,
) -> tuple[str, bool]:
    m15_direction = str(m15.get("direction", "HOLD"))
    h1_direction = str(h1.get("direction", "HOLD"))
    h1_score = float(h1.get("score", 0.0) or 0.0)

    if int(h1_score) < int(config.h1_trend_min_score):
        return "H1_trend_weak", False
    if h1_direction == m15_direction:
        return "H1_trend_confirmed", False

    # Production fusion reads `.adx // 0`. Current scoring JSON has no top-level
    # `adx`, so this remains zero unless a future production contract adds it.
    top_level_adx = float(m15.get("adx", 0.0) or 0.0)
    score_ok = int(float(m15.get("score", 0.0) or 0.0)) >= int(
        config.h1_veto_override_score
    )
    adx_ok = int(top_level_adx) >= int(config.h1_veto_override_adx)
    if score_ok and adx_ok:
        return "H1_trend_opposite_overridden", False
    return "H1_trend_opposite", True


def _h1_fusion_decision(
    m15: Mapping[str, Any],
    h1: Mapping[str, Any],
    h4_bundle: Mapping[str, Any],
    config: ReplayConfig,
) -> tuple[str, bool]:
    m15_score = float(m15.get("score", 0.0) or 0.0)
    h4_opposing = _effective_h4_opposition(m15, h4_bundle)
    if bool(h1.get("filter_rejected", False)):
        return _neutral_h1_decision(m15_score, h4_opposing, config)

    h1_direction = str(h1.get("direction", "HOLD"))
    if h1_direction in {"BUY", "SELL"}:
        return _tradeable_h1_decision(m15, h1, config)

    return _neutral_h1_decision(m15_score, h4_opposing, config)


def _extreme_rsi(direction: str, rsi: float) -> bool:
    if direction == "SELL":
        return rsi <= 30.0
    if direction == "BUY":
        return rsi >= 70.0
    return False


def policy_flags(signal: Mapping[str, Any]) -> dict[str, bool]:
    """Frozen A/B/C candidate policies selected before June-July replay."""
    direction = str(signal.get("direction", "HOLD"))
    accepted = (
        direction in {"BUY", "SELL"}
        and not bool(signal.get("filter_rejected", True))
    )
    score = float(signal.get("score", 0.0) or 0.0)
    adx = float(signal.get("adx_raw", 0.0) or 0.0)
    rsi = float(signal.get("rsi_raw", 50.0) or 50.0)
    extreme = _extreme_rsi(direction, rsi)
    policy_b = accepted and score >= 70.0 and adx < 30.0
    return {
        "policy_a_current": accepted,
        "policy_b_score70_adx_lt30": policy_b,
        "policy_c_score70_adx_lt30_no_extreme": policy_b and not extreme,
        "extreme_rsi": extreme,
    }


def _score_timeframe(
    *,
    pair: str,
    timeframe: str,
    bundle: Mapping[str, Any],
    d1_bundle: Mapping[str, Any],
    h1_series: HistoricalSeries,
    decision_time: datetime,
    config: ReplayConfig,
) -> dict[str, Any]:
    prelim = preliminary_direction(bundle)
    sr_comp = sr_component(
        h1_series,
        decision_time,
        prelim,
        float(bundle.get("price", 0.0) or 0.0),
        float(bundle.get("atr", 0.0) or 0.0),
    )
    scored = score_bundle(
        pair,
        timeframe,
        bundle,
        decision_time=decision_time,
        sr_comp=sr_comp,
        d1_bundle=d1_bundle,
        config=config,
    )
    filtered = quality_apply(scored, config)
    filtered["sr_comp"] = sr_comp
    return filtered


def _base_event(
    pair: str, m15_candle: Candle, decision_time: datetime
) -> dict[str, Any]:
    return {
        "pair": pair,
        "m15_candle_time": iso_z(m15_candle.time),
        "decision_time": iso_z(decision_time),
        "market_open": market_open_at(decision_time),
    }


def _closed_event(base: Mapping[str, Any]) -> dict[str, Any]:
    event = {
        **base,
        "direction": "HOLD",
        "score": 0.0,
        "filter_rejected": True,
        "filter_reasons": ["market_phase_Closed"],
        "reject_stage": "MARKET_ALLOWED",
    }
    event.update(policy_flags(event))
    return event


def _m15_event(
    *,
    base: Mapping[str, Any],
    m15_filtered: Mapping[str, Any],
    h4_bundle: Mapping[str, Any],
    d1_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **base,
        **m15_filtered,
        "h1_trend": "not_evaluated",
        "h4_direction": h4_direction(h4_bundle),
        "h4_vote": snapshot_vote(h4_bundle),
        "d1_vote": snapshot_vote(d1_bundle),
        "reject_stage": "",
    }


def _m15_is_rejected(event: Mapping[str, Any]) -> bool:
    return bool(event.get("filter_rejected", False)) or str(
        event.get("direction", "HOLD")
    ) not in {"BUY", "SELL"}


def _reject_event(
    event: dict[str, Any], stage: str, reason: str | None = None
) -> dict[str, Any]:
    event["filter_rejected"] = True
    event["reject_stage"] = stage
    if reason:
        event.setdefault("filter_reasons", []).append(reason)
    event.update(policy_flags(event))
    return event


def _mtf_opposes(direction: str, h4_vote: int, d1_vote: int) -> bool:
    if direction == "BUY":
        return h4_vote < 0 and d1_vote < 0
    if direction == "SELL":
        return h4_vote > 0 and d1_vote > 0
    return False


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
    base = _base_event(pair, m15_candle, decision_time)
    if not bool(base["market_open"]):
        return _closed_event(base)

    m15_bundle = m15_series.indicator_bundle(decision_time)
    h1_bundle = h1_series.indicator_bundle(decision_time)
    h4_bundle = h4_series.indicator_bundle(decision_time)
    d1_bundle = d1_series.indicator_bundle(decision_time)

    m15_filtered = _score_timeframe(
        pair=pair,
        timeframe="M15",
        bundle=m15_bundle,
        d1_bundle=d1_bundle,
        h1_series=h1_series,
        decision_time=decision_time,
        config=config,
    )
    m15_filtered["macro6"] = config.macro6
    m15_filtered.setdefault("filter_reasons", []).append(
        f"macro6={config.macro6}"
    )
    event = _m15_event(
        base=base,
        m15_filtered=m15_filtered,
        h4_bundle=h4_bundle,
        d1_bundle=d1_bundle,
    )
    if _m15_is_rejected(event):
        event["reject_stage"] = "M15_SETUP_OR_SCORE"
        event.update(policy_flags(event))
        return event

    h1_filtered = _score_timeframe(
        pair=pair,
        timeframe="H1",
        bundle=h1_bundle,
        d1_bundle=d1_bundle,
        h1_series=h1_series,
        decision_time=decision_time,
        config=config,
    )
    trend_tag, veto = _h1_fusion_decision(
        m15_filtered, h1_filtered, h4_bundle, config
    )
    event["h1_trend"] = trend_tag
    event["h1_direction"] = h1_filtered.get("direction", "HOLD")
    event["h1_score"] = h1_filtered.get("score", 0.0)
    event["h1_filter_rejected"] = h1_filtered.get(
        "filter_rejected", True
    )
    if veto:
        return _reject_event(event, "H1_CONFIRM", trend_tag)

    direction = str(event.get("direction", "HOLD"))
    if _mtf_opposes(
        direction, int(event["h4_vote"]), int(event["d1_vote"])
    ):
        return _reject_event(event, "H4_D1_CONFIRM", "H4_D1_oppose")

    event.setdefault("filter_reasons", []).append(trend_tag)
    event["reject_stage"] = "ACCEPTED"
    event.update(policy_flags(event))
    return event
