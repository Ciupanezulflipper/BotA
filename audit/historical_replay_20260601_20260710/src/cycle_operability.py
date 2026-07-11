from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .runtime_epochs import RuntimeResolution, RuntimeState
from .watcher_freshness import FreshnessDecision


class OperabilityState(str, Enum):
    OPERABLE = "OPERABLE"
    RUNTIME_DOWN = "RUNTIME_DOWN"
    DATA_UNUSABLE = "DATA_UNUSABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CycleOperability:
    state: OperabilityState
    claim_status: str
    scheduled: bool | None
    usable_data: bool | None
    reason: str


def combine_runtime_and_freshness(
    runtime: RuntimeResolution,
    freshness: FreshnessDecision,
) -> CycleOperability:
    """Combine independent runtime and raw-cache freshness evidence.

    Runtime UNKNOWN remains UNKNOWN even when candle data is fresh. Runtime DOWN
    takes precedence because no watcher evaluation can occur. Runtime UP with
    missing or stale data is proven non-operable for evaluation. Only Runtime UP
    plus FRESH data is OPERABLE.
    """
    if not isinstance(runtime, RuntimeResolution):
        raise TypeError("runtime must be RuntimeResolution")
    if not isinstance(freshness, FreshnessDecision):
        raise TypeError("freshness must be FreshnessDecision")
    if runtime.cycle_utc != freshness.decision_time_utc:
        raise ValueError("runtime and freshness must refer to the same cycle instant")

    if runtime.state is RuntimeState.DOWN:
        return CycleOperability(
            state=OperabilityState.RUNTIME_DOWN,
            claim_status="proven",
            scheduled=False,
            usable_data=None,
            reason="preserved runtime evidence proves watcher unavailable",
        )
    if runtime.state is RuntimeState.UNKNOWN:
        return CycleOperability(
            state=OperabilityState.UNKNOWN,
            claim_status="not proven",
            scheduled=None,
            usable_data=freshness.eligible,
            reason="runtime evidence does not prove whether the watcher could execute",
        )
    if not freshness.eligible:
        return CycleOperability(
            state=OperabilityState.DATA_UNUSABLE,
            claim_status="proven",
            scheduled=True,
            usable_data=False,
            reason=f"watcher was available but production freshness gate returned {freshness.status}",
        )
    return CycleOperability(
        state=OperabilityState.OPERABLE,
        claim_status="proven",
        scheduled=True,
        usable_data=True,
        reason="watcher availability and production raw-cache freshness are both proven",
    )
