from datetime import datetime, timezone
from types import SimpleNamespace

from audit.historical_replay_20260601_20260710.src.canonical_candle import normalize_provider_rows
from audit.historical_replay_20260601_20260710.src.point_in_time import visible_candles


UTC = timezone.utc


def test_normalized_d1_candle_is_hidden_until_provider_aligned_close():
    source = SimpleNamespace(
        time=datetime(2026, 7, 1, 21, 0, tzinfo=UTC),
        complete=True,
        open=1.17,
        high=1.18,
        low=1.16,
        close=1.175,
        volume=100,
    )
    candle = normalize_provider_rows(
        [source],
        provider="oanda",
        instrument="EUR_USD",
        granularity="D",
        default_complete=False,
    )[0]

    before = visible_candles(
        [candle],
        "D1",
        datetime(2026, 7, 2, 20, 59, 59, tzinfo=UTC),
    )
    boundary = visible_candles(
        [candle],
        "D1",
        datetime(2026, 7, 2, 21, 0, 0, tzinfo=UTC),
    )

    assert before.rows == ()
    assert boundary.rows == (candle,)
    assert boundary.latest_available_at_utc == datetime(2026, 7, 2, 21, 0, 0, tzinfo=UTC)
