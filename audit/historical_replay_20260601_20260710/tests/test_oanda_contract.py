import pytest

from audit.historical_replay_20260601_20260710.src.oanda_contract import (
    CandleRequest,
    OandaContractError,
    request_params,
)


def valid_request() -> CandleRequest:
    return CandleRequest(
        instrument="EUR_USD",
        granularity="M15",
        price="M",
        start_utc="2026-06-01T00:00:00Z",
        end_utc="2026-06-02T00:00:00Z",
    )


def test_builds_explicit_range_without_count() -> None:
    params = request_params(valid_request())
    assert params["price"] == "M"
    assert "count" not in params


def test_rejects_non_mid_price() -> None:
    req = CandleRequest(**{**valid_request().__dict__, "price": "BA"})
    with pytest.raises(OandaContractError):
        request_params(req)


def test_rejects_count_with_explicit_range() -> None:
    req = CandleRequest(**{**valid_request().__dict__, "count": 5000})
    with pytest.raises(OandaContractError):
        request_params(req)
