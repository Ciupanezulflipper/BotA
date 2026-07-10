import json

import pytest

from audit.historical_replay_20260601_20260710.src.oanda_payload import parse_oanda_mid_payload


def test_parse_midpoint_payload() -> None:
    raw = json.dumps({
        "candles": [{
            "time": "2026-06-01T07:00:00.000000000Z",
            "complete": True,
            "volume": 10,
            "mid": {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"}
        }]
    }).encode()
    rows = parse_oanda_mid_payload(raw)
    assert len(rows) == 1
    assert rows[0].complete is True
    assert rows[0].high == 1.101


def test_rejects_non_midpoint_payload() -> None:
    raw = json.dumps({
        "candles": [{
            "time": "2026-06-01T07:00:00Z",
            "complete": True,
            "bid": {"o": "1", "h": "1", "l": "1", "c": "1"}
        }]
    }).encode()
    with pytest.raises(ValueError, match="mid"):
        parse_oanda_mid_payload(raw)
