from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from audit.historical_replay_20260601_20260710.src.canonical_candle import normalize_provider_rows


def row(stamp, *, complete=True, open_=1.1, high=1.2, low=1.0, close=1.15, volume=10, available_at=None):
    return SimpleNamespace(
        time=stamp,
        complete=complete,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        available_at=available_at,
    )


def test_normalizes_oanda_and_maps_d_to_d1_with_explicit_availability():
    stamp = datetime(2026, 6, 1, 21, tzinfo=timezone.utc)
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
    assert candle.available_at == stamp + timedelta(days=1)
    assert candle.to_json()["time"] == "2026-06-01T21:00:00Z"
    assert candle.to_json()["available_at"] == "2026-06-02T21:00:00Z"


def test_preserves_provider_supplied_available_at():
    stamp = datetime(2026, 6, 1, 21, tzinfo=timezone.utc)
    explicit = datetime(2026, 6, 2, 22, tzinfo=timezone.utc)
    candle = normalize_provider_rows(
        [row(stamp, available_at=explicit)],
        provider="oanda",
        instrument="EURUSD",
        granularity="D1",
        default_complete=True,
    )[0]
    assert candle.available_at == explicit


def test_rejects_d1_alignment_change_inside_range():
    first = datetime(2026, 6, 1, 21, tzinfo=timezone.utc)
    second = datetime(2026, 6, 2, 22, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="alignment changed"):
        normalize_provider_rows(
            [row(first), row(second)],
            provider="oanda",
            instrument="EURUSD",
            granularity="D1",
            default_complete=True,
        )


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
    assert candle.available_at is None


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


def test_rejects_invalid_explicit_available_at():
    stamp = datetime(2026, 6, 1, 21, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="after candle start"):
        normalize_provider_rows(
            [row(stamp, available_at=stamp)],
            provider="oanda",
            instrument="EURUSD",
            granularity="D1",
            default_complete=True,
        )
