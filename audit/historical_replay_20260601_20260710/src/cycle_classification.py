from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class CycleOutcome(str, Enum):
    NOT_SCHEDULED = "NOT_SCHEDULED"
    NO_USABLE_DATA = "NO_USABLE_DATA"
    EVALUATED_REJECTED = "EVALUATED_REJECTED"
    EVALUATED_ELIGIBLE_NOT_DELIVERED = "EVALUATED_ELIGIBLE_NOT_DELIVERED"
    DELIVERED = "DELIVERED"
    PUBLICATION_UNKNOWN = "PUBLICATION_UNKNOWN"


@dataclass(frozen=True)
class CycleEvidence:
    scheduled: bool
    usable_data: bool
    decision_recorded: bool
    eligible: bool | None
    delivery_recorded: bool
    publication_recorded: bool | None = None


@dataclass(frozen=True)
class ClassifiedCycle:
    outcome: CycleOutcome
    claim_status: str
    reason: str


def classify_cycle(evidence: CycleEvidence) -> ClassifiedCycle:
    """Classify one watcher cycle without inferring missing evidence as success.

    Eligibility, delivery, and publication remain separate dimensions. A missing
    decision record is never silently converted into a strategy rejection.
    """
    if not evidence.scheduled:
        return ClassifiedCycle(
            CycleOutcome.NOT_SCHEDULED,
            "proven",
            "cycle was outside the reconstructed watcher schedule",
        )

    if not evidence.usable_data:
        return ClassifiedCycle(
            CycleOutcome.NO_USABLE_DATA,
            "proven",
            "scheduled cycle lacked a complete point-in-time candle set",
        )

    if not evidence.decision_recorded:
        return ClassifiedCycle(
            CycleOutcome.PUBLICATION_UNKNOWN,
            "not proven",
            "usable data existed but no decision record proves evaluation outcome",
        )

    if evidence.eligible is False:
        return ClassifiedCycle(
            CycleOutcome.EVALUATED_REJECTED,
            "proven",
            "decision record proves the cycle was evaluated and rejected",
        )

    if evidence.eligible is not True:
        raise ValueError("recorded decision requires eligible=True or eligible=False")

    if evidence.delivery_recorded:
        return ClassifiedCycle(
            CycleOutcome.DELIVERED,
            "proven",
            "eligible decision and delivery record are both present",
        )

    if evidence.publication_recorded is None:
        return ClassifiedCycle(
            CycleOutcome.PUBLICATION_UNKNOWN,
            "not proven",
            "eligible decision exists but publication evidence is unavailable",
        )

    return ClassifiedCycle(
        CycleOutcome.EVALUATED_ELIGIBLE_NOT_DELIVERED,
        "proven",
        "eligible decision exists and available publication evidence shows no delivery",
    )


def summarize_outcomes(rows: Mapping[str, ClassifiedCycle]) -> dict[str, int]:
    counts = {outcome.value: 0 for outcome in CycleOutcome}
    for cycle_id, classified in rows.items():
        if not str(cycle_id).strip():
            raise ValueError("cycle id must be non-empty")
        if not isinstance(classified, ClassifiedCycle):
            raise TypeError("summary values must be ClassifiedCycle")
        counts[classified.outcome.value] += 1
    return counts
