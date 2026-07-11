from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


class RuntimeState(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RuntimeEpoch:
    start_utc: datetime
    end_utc: datetime
    state: RuntimeState
    evidence_id: str

    def __post_init__(self) -> None:
        start = _utc(self.start_utc, "start_utc")
        end = _utc(self.end_utc, "end_utc")
        if start >= end:
            raise ValueError("runtime epoch requires start_utc < end_utc")
        if not isinstance(self.state, RuntimeState):
            raise TypeError("state must be RuntimeState")
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must be non-empty")
        object.__setattr__(self, "start_utc", start)
        object.__setattr__(self, "end_utc", end)


@dataclass(frozen=True)
class RuntimeResolution:
    cycle_utc: datetime
    state: RuntimeState
    evidence_id: str | None
    claim_status: str
    reason: str

    @property
    def watcher_scheduled(self) -> bool | None:
        if self.state is RuntimeState.UP:
            return True
        if self.state is RuntimeState.DOWN:
            return False
        return None


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def validate_runtime_epochs(epochs: Iterable[RuntimeEpoch]) -> tuple[RuntimeEpoch, ...]:
    rows = tuple(epochs)
    previous_end: datetime | None = None
    for row in rows:
        if not isinstance(row, RuntimeEpoch):
            raise TypeError("runtime epochs must contain RuntimeEpoch values")
        if previous_end is not None and row.start_utc < previous_end:
            raise ValueError("runtime epochs must not overlap")
        previous_end = row.end_utc
    return rows


def resolve_runtime_state(
    cycle_utc: datetime,
    epochs: Iterable[RuntimeEpoch],
) -> RuntimeResolution:
    """Resolve one cycle against explicit half-open runtime evidence.

    Absence of an epoch is UNKNOWN, never silently UP or DOWN. Epochs are
    half-open: start_utc <= cycle_utc < end_utc.
    """
    cycle = _utc(cycle_utc, "cycle_utc")
    rows = validate_runtime_epochs(epochs)
    matches = [row for row in rows if row.start_utc <= cycle < row.end_utc]
    if len(matches) > 1:
        raise ValueError("runtime epoch overlap reached resolution")
    if not matches:
        return RuntimeResolution(
            cycle_utc=cycle,
            state=RuntimeState.UNKNOWN,
            evidence_id=None,
            claim_status="not proven",
            reason="no preserved runtime epoch covers this cycle",
        )
    row = matches[0]
    if row.state is RuntimeState.UNKNOWN:
        return RuntimeResolution(
            cycle_utc=cycle,
            state=row.state,
            evidence_id=row.evidence_id,
            claim_status="not proven",
            reason="preserved evidence marks runtime state unknown",
        )
    return RuntimeResolution(
        cycle_utc=cycle,
        state=row.state,
        evidence_id=row.evidence_id,
        claim_status="proven",
        reason=(
            "preserved runtime evidence proves watcher available"
            if row.state is RuntimeState.UP
            else "preserved runtime evidence proves watcher unavailable"
        ),
    )
