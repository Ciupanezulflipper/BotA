from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Iterable, Mapping, Sequence

from .cycle_classification import CycleEvidence, classify_cycle, summarize_outcomes
from .cycle_generator import ExpectedCycle, generate_expected_cycles
from .point_in_time import build_multitimeframe_view

UTC = timezone.utc


@dataclass(frozen=True)
class RuntimeEpoch:
    epoch_id: str
    start_utc: datetime
    end_utc: datetime
    scheduled: bool
    claim_status: str


@dataclass(frozen=True)
class ReplayEvidence:
    decision_recorded: bool
    eligible: bool | None
    delivery_recorded: bool
    publication_recorded: bool | None = None


@dataclass(frozen=True)
class ReplayRow:
    cycle_id: str
    decision_time_utc: str
    pair: str
    timeframe: str
    runtime_epoch: str
    runtime_epoch_claim_status: str
    usable_data: bool
    visible_counts: dict[str, int]
    outcome: str
    claim_status: str
    reason: str


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _cycle_id(cycle: ExpectedCycle) -> str:
    stamp = _utc(cycle.decision_time_utc, "decision_time_utc").isoformat().replace("+00:00", "Z")
    return f"{stamp}|{cycle.pair}|{cycle.timeframe}"


def _validate_epochs(epochs: Sequence[RuntimeEpoch]) -> tuple[RuntimeEpoch, ...]:
    ordered = sorted(epochs, key=lambda item: _utc(item.start_utc, "epoch start"))
    previous_end: datetime | None = None
    seen: set[str] = set()
    for epoch in ordered:
        if not epoch.epoch_id.strip() or epoch.epoch_id in seen:
            raise ValueError("runtime epoch ids must be non-empty and unique")
        seen.add(epoch.epoch_id)
        start = _utc(epoch.start_utc, "epoch start")
        end = _utc(epoch.end_utc, "epoch end")
        if end <= start:
            raise ValueError("runtime epoch end must be after start")
        if previous_end is not None and start < previous_end:
            raise ValueError("runtime epochs must not overlap")
        if epoch.claim_status not in {"proven", "inferred", "suspected", "not proven"}:
            raise ValueError("invalid runtime epoch claim_status")
        previous_end = end
    return tuple(ordered)


def _epoch_for(decision_time: datetime, epochs: Sequence[RuntimeEpoch]) -> RuntimeEpoch:
    decision = _utc(decision_time, "decision_time")
    matches = [
        epoch
        for epoch in epochs
        if _utc(epoch.start_utc, "epoch start") <= decision < _utc(epoch.end_utc, "epoch end")
    ]
    if len(matches) != 1:
        raise ValueError("each expected cycle must map to exactly one runtime epoch")
    return matches[0]


def _pair_candles(
    candles_by_pair: Mapping[str, Mapping[str, Iterable[object]]], pair: str
) -> Mapping[str, Iterable[object]]:
    normalized = {str(key).upper(): value for key, value in candles_by_pair.items()}
    if pair not in normalized:
        raise ValueError(f"missing candle set for pair: {pair}")
    return normalized[pair]


def build_cycle_replay_report(
    *,
    start_utc: datetime,
    end_utc: datetime,
    candles_by_pair: Mapping[str, Mapping[str, Iterable[object]]],
    runtime_epochs: Sequence[RuntimeEpoch],
    evidence_by_cycle: Mapping[str, ReplayEvidence] | None = None,
    pairs: Iterable[str] = ("EURUSD", "GBPUSD"),
) -> dict:
    """Build a deterministic forensic cycle report without invoking production code."""
    epochs = _validate_epochs(runtime_epochs)
    evidence_map = dict(evidence_by_cycle or {})
    cycles = generate_expected_cycles(start_utc, end_utc, pairs)
    rows: list[ReplayRow] = []
    classified = {}

    for cycle in cycles:
        cycle_id = _cycle_id(cycle)
        epoch = _epoch_for(cycle.decision_time_utc, epochs)
        views = build_multitimeframe_view(
            _pair_candles(candles_by_pair, cycle.pair), cycle.decision_time_utc
        )
        visible_counts = {timeframe: len(view.rows) for timeframe, view in views.items()}
        usable_data = all(count > 0 for count in visible_counts.values())
        recorded = evidence_map.get(
            cycle_id,
            ReplayEvidence(False, None, False, None),
        )
        result = classify_cycle(
            CycleEvidence(
                scheduled=epoch.scheduled,
                usable_data=usable_data,
                decision_recorded=recorded.decision_recorded,
                eligible=recorded.eligible,
                delivery_recorded=recorded.delivery_recorded,
                publication_recorded=recorded.publication_recorded,
            )
        )
        classified[cycle_id] = result
        rows.append(
            ReplayRow(
                cycle_id=cycle_id,
                decision_time_utc=_utc(cycle.decision_time_utc, "decision_time_utc")
                .isoformat()
                .replace("+00:00", "Z"),
                pair=cycle.pair,
                timeframe=cycle.timeframe,
                runtime_epoch=epoch.epoch_id,
                runtime_epoch_claim_status=epoch.claim_status,
                usable_data=usable_data,
                visible_counts=visible_counts,
                outcome=result.outcome.value,
                claim_status=result.claim_status,
                reason=result.reason,
            )
        )

    payload = {
        "schema_version": 1,
        "interval": {
            "semantics": "half_open",
            "start_utc": _utc(start_utc, "start_utc").isoformat().replace("+00:00", "Z"),
            "end_utc": _utc(end_utc, "end_utc").isoformat().replace("+00:00", "Z"),
        },
        "cycle_count": len(rows),
        "summary": summarize_outcomes(classified),
        "rows": [asdict(row) for row in rows],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["report_sha256"] = sha256(canonical).hexdigest()
    return payload
