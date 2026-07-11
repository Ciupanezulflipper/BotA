from __future__ import annotations

import pytest

from audit.historical_replay_20260601_20260710.src.dukascopy_fixture import parse_dukascopy_csv


def test_parse_dukascopy_csv_accepts_iso_and_epoch_ms():
    raw = (
        b"time,open,high,low,close,volume\n"
        b"2026-06-01T00:00:00Z,1.10,1.11,1.09,1.105,10\n"
        b"1780272900000,1.105,1.12,1.10,1.115,11\n"
    )
    rows = parse_dukascopy_csv(raw)
    assert len(rows) == 2
    assert rows[0].time.isoformat() == "2026-06-01T00:00:00+00:00"
    assert rows[0].close == 1.105


def test_parse_dukascopy_csv_rejects_bad_ohlc():
    raw = b"time,open,high,low,close\n2026-06-01T00:00:00Z,1.10,1.09,1.08,1.105\n"
    with pytest.raises(ValueError, match="invalid OHLC envelope"):
        parse_dukascopy_csv(raw)


def test_parse_dukascopy_csv_rejects_non_increasing_time():
    raw = (
        b"time,open,high,low,close\n"
        b"2026-06-01T00:15:00Z,1.10,1.11,1.09,1.105\n"
        b"2026-06-01T00:00:00Z,1.10,1.11,1.09,1.105\n"
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        parse_dukascopy_csv(raw)
