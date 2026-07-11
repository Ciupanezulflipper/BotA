import pytest

from audit.historical_replay_20260601_20260710.src.cycle_classification import (
    ClassifiedCycle,
    CycleEvidence,
    CycleOutcome,
    classify_cycle,
    summarize_outcomes,
)


def test_unscheduled_cycle_is_distinct_from_rejection():
    result = classify_cycle(CycleEvidence(False, False, False, None, False))
    assert result.outcome is CycleOutcome.NOT_SCHEDULED
    assert result.claim_status == "proven"


def test_missing_data_is_not_strategy_rejection():
    result = classify_cycle(CycleEvidence(True, False, False, None, False))
    assert result.outcome is CycleOutcome.NO_USABLE_DATA


def test_missing_decision_record_remains_not_proven():
    result = classify_cycle(CycleEvidence(True, True, False, None, False))
    assert result.outcome is CycleOutcome.PUBLICATION_UNKNOWN
    assert result.claim_status == "not proven"


def test_recorded_rejection_is_proven():
    result = classify_cycle(CycleEvidence(True, True, True, False, False))
    assert result.outcome is CycleOutcome.EVALUATED_REJECTED
    assert result.claim_status == "proven"


def test_eligible_without_publication_evidence_remains_unknown():
    result = classify_cycle(CycleEvidence(True, True, True, True, False, None))
    assert result.outcome is CycleOutcome.PUBLICATION_UNKNOWN


def test_eligible_and_proven_not_delivered_is_separate_outcome():
    result = classify_cycle(CycleEvidence(True, True, True, True, False, False))
    assert result.outcome is CycleOutcome.EVALUATED_ELIGIBLE_NOT_DELIVERED


def test_delivery_record_proves_delivered():
    result = classify_cycle(CycleEvidence(True, True, True, True, True, True))
    assert result.outcome is CycleOutcome.DELIVERED


def test_recorded_decision_requires_boolean_eligibility():
    with pytest.raises(ValueError, match="eligible=True or eligible=False"):
        classify_cycle(CycleEvidence(True, True, True, None, False, False))


def test_summary_counts_each_outcome():
    rows = {
        "a": ClassifiedCycle(CycleOutcome.DELIVERED, "proven", "x"),
        "b": ClassifiedCycle(CycleOutcome.DELIVERED, "proven", "x"),
        "c": ClassifiedCycle(CycleOutcome.EVALUATED_REJECTED, "proven", "x"),
    }
    summary = summarize_outcomes(rows)
    assert summary["DELIVERED"] == 2
    assert summary["EVALUATED_REJECTED"] == 1
