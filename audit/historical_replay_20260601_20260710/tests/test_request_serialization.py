from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

from audit.historical_replay_20260601_20260710.src.request_serialization import (
    serialize_chunk_request,
)


def test_serializes_explicit_half_open_request_without_count():
    result = serialize_chunk_request(
        instrument="EUR_USD",
        granularity="M15",
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )
    query = parse_qs(urlsplit(result["url"]).query)
    assert result["method"] == "GET"
    assert query["price"] == ["M"]
    assert query["granularity"] == ["M15"]
    assert "count" not in query
    assert query["from"] == ["2026-06-01T00:00:00Z"]
    assert query["to"] == ["2026-06-02T00:00:00Z"]


def test_rejects_non_midpoint_price():
    with pytest.raises(ValueError):
        serialize_chunk_request(
            instrument="EUR_USD",
            granularity="M15",
            start=datetime(2026, 6, 1, tzinfo=timezone.utc),
            end=datetime(2026, 6, 2, tzinfo=timezone.utc),
            price="B",
        )


def test_rejects_naive_timestamp():
    with pytest.raises(ValueError):
        serialize_chunk_request(
            instrument="GBP_USD",
            granularity="H1",
            start=datetime(2026, 6, 1),
            end=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
