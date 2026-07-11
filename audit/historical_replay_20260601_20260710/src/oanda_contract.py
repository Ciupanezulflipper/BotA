from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class OandaContractError(ValueError):
    pass


@dataclass(frozen=True)
class CandleRequest:
    instrument: str
    granularity: str
    price: str
    start_utc: str
    end_utc: str
    count: int | None = None
    include_first: bool | None = None


def _parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise OandaContractError(f"timestamp must be UTC Z form: {value}")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def validate_request(request: CandleRequest) -> None:
    if request.instrument not in {"EUR_USD", "GBP_USD"}:
        raise OandaContractError(f"unsupported instrument: {request.instrument}")
    if request.granularity not in {"M15", "H1", "H4", "D"}:
        raise OandaContractError(f"unsupported granularity: {request.granularity}")
    if request.price != "M":
        raise OandaContractError("historical production-faithful replay requires price=M")
    start = _parse_utc(request.start_utc)
    end = _parse_utc(request.end_utc)
    if end <= start:
        raise OandaContractError("end must be after start")
    if request.count is not None:
        raise OandaContractError("count must not be combined with explicit from/to range")


def request_params(request: CandleRequest) -> dict[str, str]:
    validate_request(request)
    params = {
        "granularity": request.granularity,
        "price": request.price,
        "from": request.start_utc,
        "to": request.end_utc,
    }
    if request.include_first is not None:
        params["includeFirst"] = "true" if request.include_first else "false"
    return params
