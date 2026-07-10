from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from audit.historical_replay_20260601_20260710.src.canonical_candle import normalize_provider_rows


def row(stamp, *, complete=True, open_=1.1, high=1.2, low=1.0, close=1.15, volume=10):
    return SimpleNamespace(
        time=stamp,
        complete=complete,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def test_normalizes_oanda_and_maps_d_to_d1():
    stamp = datetime(2026, 6, 1, tzinfo=timezone.utc)
    candles = normalize_provider_rows(
        [row(stamp)],
        provider="OANDA",
        instrument="EUR_USD",
        granularity="D",
        default_complete=False,
    )
    candle = candles[0]
    assert candle.provider == "oanda"
    assert candle.instrument == "EURUSD"
    assert candle.granularity == "D1"
    assert candle.complete is True
    assert candle.to_json()["time"] == "2026-06-01T00:00:00Z"


def test_uses_default_complete_when_provider_row_has_no_flag():
    stamp = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = SimpleNamespace(time=stamp, open=1.1, high=1.2, low=1.0, close=1.15, volume=5)
    candle = normalize_provider_rows(
        [source],
        provider="dukascopy",
        instrument="GBPUSD",
        granularity="M15",
        default_complete=True,
    )[0]
    assert candle.complete is True


def test_rejects_nonmonotonic_or_invalid_prices():
    stamp = datetime(2026, 6, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="strictly increasing"):
        normalize_provider_rows(
            [row(stamp), row(stamp)],
            provider="oanda",
            instrument="EURUSD",
            granularity="M15",
            default_complete=True,
        )
    with pytest.raises(ValueError, match="finite and positive"):
        normalize_provider_rows(
            [row(stamp, open_=0)],
            provider="oanda",
            instrument="EURUSD",
            granularity="M15",
            default_complete=True,
        )
