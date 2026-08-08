#!/usr/bin/env python3
"""Classify unmatched published outcomes against the deterministic replay ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_MATCH_TIME_MINUTES = 45.0
EXPECTED_MATCH_ENTRY_PIPS = 5.0
DIAGNOSTIC_WINDOW_MINUTES = 180.0
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _verify_sha(path: Path, expected: str, label: str) -> str:
    normalized = expected.strip().lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{label} expected SHA-256 must be 64 lowercase hex digits")
    actual = _sha256(path)
    if actual != normalized:
        raise ValueError(f"{label} SHA-256 mismatch: {actual}!={normalized}")
    return actual


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _finite(value: Any, field: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite {field}")
    return number


def _pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def _load_events(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"event line {line_number} is not an object")
            rows.append(value)
    if not rows:
        raise ValueError("replay event ledger is empty")
    return rows


def _load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _validate_comparison(comparison: dict[str, Any]) -> list[str]:
    if comparison.get("match_gate") != "FAIL":
        raise ValueError("canonical comparison must have MATCH_GATE=FAIL")
    counts = comparison.get("counts")
    if not isinstance(counts, dict):
        raise ValueError("canonical comparison counts missing")
    expected_counts = {
        "published_outcomes": 13,
        "matched_outcomes": 9,
        "unmatched_outcomes": 4,
        "ambiguous_outcomes": 0,
    }
    for key, expected in expected_counts.items():
        if int(counts.get(key, -1)) != expected:
            raise ValueError(
                f"canonical comparison {key} mismatch: {counts.get(key)}!={expected}"
            )
    contract = comparison.get("matching_contract")
    if not isinstance(contract, dict):
        raise ValueError("canonical comparison matching contract missing")
    if float(contract.get("max_abs_time_delta_minutes", -1)) != EXPECTED_MATCH_TIME_MINUTES:
        raise ValueError("canonical comparison time tolerance changed")
    if float(contract.get("max_entry_pips", -1)) != EXPECTED_MATCH_ENTRY_PIPS:
        raise ValueError("canonical comparison entry tolerance changed")
    unmatched = comparison.get("unmatched_outcome_ids")
    if not isinstance(unmatched, list) or len(unmatched) != 4:
        raise ValueError("canonical comparison unmatched outcome ids invalid")
    if comparison.get("ambiguous") not in ({}, None):
        raise ValueError("canonical comparison contains ambiguous outcomes")
    ids = [str(value) for value in unmatched]
    if len(set(ids)) != len(ids) or "" in ids:
        raise ValueError("canonical comparison unmatched outcome ids must be unique")
    return ids


def _load_outcomes(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    outcomes = snapshot.get("outcomes")
    if not isinstance(outcomes, list):
        raise ValueError("outcome snapshot outcomes list missing")
    by_id: dict[str, dict[str, Any]] = {}
    for row in outcomes:
        if not isinstance(row, dict):
            raise ValueError("outcome snapshot contains non-object row")
        outcome_id = str(row.get("id", ""))
        if not outcome_id or outcome_id in by_id:
            raise ValueError("outcome ids must be present and unique")
        by_id[outcome_id] = row
    if len(by_id) != 13:
        raise ValueError(f"expected 13 frozen outcomes, got {len(by_id)}")
    return by_id


def _event_metrics(outcome: dict[str, Any], event: dict[str, Any]) -> tuple[float, float]:
    published_time = _parse_utc(str(outcome.get("created_at", "")))
    decision_time = _parse_utc(str(event.get("decision_time", "")))
    time_minutes = abs((published_time - decision_time).total_seconds()) / 60.0
    pair = str(outcome.get("pair", ""))
    published_entry = _finite(outcome.get("entry_price"), "outcome entry_price")
    replay_entry = _finite(event.get("entry", 0.0), "replay entry")
    if published_entry <= 0 or replay_entry <= 0:
        entry_pips = math.inf
    else:
        entry_pips = abs(published_entry - replay_entry) / _pip_size(pair)
    return time_minutes, entry_pips


def _same_pair_direction(outcome: dict[str, Any], event: dict[str, Any]) -> bool:
    return (
        str(event.get("pair", "")) == str(outcome.get("pair", ""))
        and str(event.get("direction", "")) == str(outcome.get("direction", ""))
    )


def _event_summary(
    outcome: dict[str, Any], event: dict[str, Any], index: int
) -> dict[str, Any]:
    time_minutes, entry_pips = _event_metrics(outcome, event)
    return {
        "event_index": index,
        "decision_time": event.get("decision_time"),
        "direction": event.get("direction"),
        "policy_a_current": bool(event.get("policy_a_current")),
        "reject_stage": event.get("reject_stage"),
        "filter_rejected": bool(event.get("filter_rejected", False)),
        "score": event.get("score"),
        "entry": event.get("entry"),
        "adx_raw": event.get("adx_raw"),
        "rsi_raw": event.get("rsi_raw"),
        "h1_trend": event.get("h1_trend"),
        "h4_vote": event.get("h4_vote"),
        "d1_vote": event.get("d1_vote"),
        "filter_reasons": event.get("filter_reasons", []),
        "time_delta_minutes": round(time_minutes, 4),
        "entry_diff_pips": None if math.isinf(entry_pips) else round(entry_pips, 4),
    }


def _classify_one(
    outcome: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    candidates: list[tuple[int, dict[str, Any], float, float]] = []
    for index, event in enumerate(events):
        if not _same_pair_direction(outcome, event):
            continue
        time_minutes, entry_pips = _event_metrics(outcome, event)
        candidates.append((index, event, time_minutes, entry_pips))

    within_45 = [item for item in candidates if item[2] <= EXPECTED_MATCH_TIME_MINUTES]
    accepted_45 = [item for item in within_45 if bool(item[1].get("policy_a_current"))]
    exact_candidate = [
        item
        for item in accepted_45
        if item[3] <= EXPECTED_MATCH_ENTRY_PIPS
    ]
    if exact_candidate:
        raise ValueError(
            f"matcher inconsistency: unmatched outcome {outcome['id']} has a frozen-contract candidate"
        )

    diagnostic = [item for item in candidates if item[2] <= DIAGNOSTIC_WINDOW_MINUTES]
    accepted_diagnostic = [
        item for item in diagnostic if bool(item[1].get("policy_a_current"))
    ]

    if not within_45:
        classification = "NO_SAME_DIRECTION_EVENT_WITHIN_45M"
    elif not accepted_45:
        classification = "LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M"
    else:
        classification = "REPLAY_ACCEPTED_WITHIN_45M_BUT_ENTRY_DIFF_GT_5P"

    nearest_same_direction = min(
        diagnostic,
        key=lambda item: (item[2], item[3], item[0]),
        default=None,
    )
    nearest_accepted_time = min(
        accepted_diagnostic,
        key=lambda item: (item[2], item[3], item[0]),
        default=None,
    )
    nearest_accepted_entry = min(
        accepted_diagnostic,
        key=lambda item: (item[3], item[2], item[0]),
        default=None,
    )

    def summarize(
        item: tuple[int, dict[str, Any], float, float] | None,
    ) -> dict[str, Any] | None:
        if item is None:
            return None
        return _event_summary(outcome, item[1], item[0])

    within_45_summaries = [
        _event_summary(outcome, item[1], item[0])
        for item in sorted(within_45, key=lambda row: (row[2], row[3], row[0]))[:8]
    ]

    return {
        "outcome_id": outcome["id"],
        "pair": outcome.get("pair"),
        "direction": outcome.get("direction"),
        "created_at": outcome.get("created_at"),
        "entry_price": outcome.get("entry_price"),
        "status": outcome.get("status"),
        "result_pips": outcome.get("result_pips"),
        "rationale": outcome.get("rationale"),
        "classification": classification,
        "same_direction_within_45m": len(within_45),
        "policy_a_same_direction_within_45m": len(accepted_45),
        "policy_a_frozen_contract_candidates": 0,
        "same_direction_within_180m": len(diagnostic),
        "policy_a_same_direction_within_180m": len(accepted_diagnostic),
        "nearest_same_direction_within_180m": summarize(nearest_same_direction),
        "nearest_policy_a_by_time_within_180m": summarize(nearest_accepted_time),
        "nearest_policy_a_by_entry_within_180m": summarize(nearest_accepted_entry),
        "same_direction_events_within_45m": within_45_summaries,
    }


def classify(
    *,
    events_path: Path,
    comparison_path: Path,
    outcomes_path: Path,
    expected_events_sha256: str,
    expected_comparison_sha256: str,
) -> dict[str, Any]:
    events_sha = _verify_sha(events_path, expected_events_sha256, "events")
    comparison_sha = _verify_sha(
        comparison_path, expected_comparison_sha256, "comparison"
    )
    comparison = _load_object(comparison_path, "comparison")
    unmatched_ids = _validate_comparison(comparison)
    snapshot = _load_object(outcomes_path, "outcomes snapshot")
    outcomes = _load_outcomes(snapshot)
    missing_ids = sorted(set(unmatched_ids) - set(outcomes))
    if missing_ids:
        raise ValueError(f"unmatched outcome ids missing from frozen snapshot: {missing_ids}")
    events = _load_events(events_path)
    classifications = [
        _classify_one(outcomes[outcome_id], events)
        for outcome_id in sorted(unmatched_ids)
    ]
    class_counts: dict[str, int] = {}
    for row in classifications:
        key = str(row["classification"])
        class_counts[key] = class_counts.get(key, 0) + 1
    return {
        "schema_version": 1,
        "status": "COMPLETE",
        "purpose": "classify_frozen_match_gaps_without_tolerance_widening",
        "integrity": {
            "events_sha256": events_sha,
            "comparison_sha256": comparison_sha,
            "outcomes_sha256": _sha256(outcomes_path),
        },
        "frozen_match_contract": {
            "max_abs_time_delta_minutes": EXPECTED_MATCH_TIME_MINUTES,
            "max_entry_pips": EXPECTED_MATCH_ENTRY_PIPS,
            "tolerance_widened": False,
        },
        "diagnostic_window_minutes": DIAGNOSTIC_WINDOW_MINUTES,
        "diagnostic_window_is_matching_tolerance": False,
        "unmatched_count": len(unmatched_ids),
        "classification_counts": dict(sorted(class_counts.items())),
        "unmatched": classifications,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify canonical BotA replay-to-published-outcome match gaps"
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--expected-events-sha256", required=True)
    parser.add_argument("--expected-comparison-sha256", required=True)
    return parser


def _print_summary(result: dict[str, Any]) -> None:
    print(f"GAP_CLASSIFIER_STATUS={result['status']}", file=sys.stderr)
    print(f"UNMATCHED_COUNT={result['unmatched_count']}", file=sys.stderr)
    for row in result["unmatched"]:
        print(
            "GAP="
            f"{row['outcome_id']}|{row['pair']}|{row['direction']}|"
            f"{row['classification']}|"
            f"same_dir_45={row['same_direction_within_45m']}|"
            f"accepted_45={row['policy_a_same_direction_within_45m']}",
            file=sys.stderr,
        )
    print("TOLERANCE_WIDENED=NO", file=sys.stderr)
    print("NETWORK_USED=NO", file=sys.stderr)
    print("PRODUCTION_MUTATION=NO", file=sys.stderr)


def main() -> int:
    args = _parser().parse_args()
    result = classify(
        events_path=Path(args.events).resolve(),
        comparison_path=Path(args.comparison).resolve(),
        outcomes_path=Path(args.outcomes).resolve(),
        expected_events_sha256=args.expected_events_sha256,
        expected_comparison_sha256=args.expected_comparison_sha256,
    )
    _print_summary(result)
    sys.stdout.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
