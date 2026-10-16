#!/usr/bin/env python3
"""Match deterministic replay events to frozen published BotA outcomes offline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__:
    from tools import bota_common as common
else:  # direct execution or file-based module loading
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import bota_common as common

POLICY_FIELDS = {
    "A": "policy_a_current",
    "B": "policy_b_score70_adx_lt30",
    "C": "policy_c_score70_adx_lt30_no_extreme",
}
SCORE_RE = re.compile(r"\bscore=(\d+(?:\.\d+)?)\b")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Candidate:
    event_index: int
    entry_diff_pips: float
    time_delta_minutes: float


def _load_events(path: Path) -> list[dict[str, Any]]:
    return common.read_jsonl_objects(path, label="replay event ledger")


def _load_outcomes(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise ValueError("outcome snapshot is not an object")
    outcomes = snapshot.get("outcomes")
    if not isinstance(outcomes, list):
        raise ValueError("outcome snapshot has no outcomes list")
    expected_count = int(snapshot.get("expected_count", -1))
    if expected_count != len(outcomes):
        raise ValueError(
            f"outcome count mismatch: expected {expected_count}, got {len(outcomes)}"
        )
    ids = [str(row.get("id", "")) for row in outcomes if isinstance(row, dict)]
    if len(ids) != len(outcomes) or len(set(ids)) != len(ids) or "" in ids:
        raise ValueError("outcome ids must be present and unique")
    return snapshot, outcomes


def _live_score(outcome: dict[str, Any]) -> float | None:
    match = SCORE_RE.search(str(outcome.get("rationale", "")))
    return float(match.group(1)) if match else None


def _eligible_event(event: dict[str, Any]) -> bool:
    return bool(event.get("policy_a_current")) and str(
        event.get("direction", "")
    ) in {"BUY", "SELL"}


def _candidate(
    outcome: dict[str, Any],
    event: dict[str, Any],
    event_index: int,
    *,
    max_time_minutes: float,
    max_entry_pips: float,
) -> Candidate | None:
    if not _eligible_event(event):
        return None
    if str(event.get("pair", "")) != str(outcome.get("pair", "")):
        return None
    if str(event.get("direction", "")) != str(outcome.get("direction", "")):
        return None

    pair = str(outcome["pair"])
    published_entry = common.finite(outcome.get("entry_price"), "entry_price")
    replay_entry = common.finite(event.get("entry"), "replay entry")
    if published_entry <= 0 or replay_entry <= 0:
        return None

    entry_diff_pips = abs(replay_entry - published_entry) / common.pip_size(pair)
    if entry_diff_pips > max_entry_pips:
        return None

    published_time = common.parse_utc_assume_utc(str(outcome.get("created_at", "")))
    decision_time = common.parse_utc_assume_utc(str(event.get("decision_time", "")))
    time_delta_minutes = abs((published_time - decision_time).total_seconds()) / 60.0
    if time_delta_minutes > max_time_minutes:
        return None

    return Candidate(
        event_index=event_index,
        entry_diff_pips=entry_diff_pips,
        time_delta_minutes=time_delta_minutes,
    )


def _build_candidates(
    outcomes: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    max_time_minutes: float,
    max_entry_pips: float,
) -> dict[str, list[Candidate]]:
    result: dict[str, list[Candidate]] = {}
    for outcome in outcomes:
        candidates: list[Candidate] = []
        for index, event in enumerate(events):
            candidate = _candidate(
                outcome,
                event,
                index,
                max_time_minutes=max_time_minutes,
                max_entry_pips=max_entry_pips,
            )
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(
            key=lambda item: (
                round(item.entry_diff_pips, 9),
                round(item.time_delta_minutes, 9),
                item.event_index,
            )
        )
        result[str(outcome["id"])] = candidates
    return result


def _resolve_unique_matches(
    candidates: dict[str, list[Candidate]],
) -> tuple[dict[str, Candidate], dict[str, list[Candidate]]]:
    matches: dict[str, Candidate] = {}
    used_events: set[int] = set()
    pending = dict(candidates)

    while True:
        filtered = {
            outcome_id: [
                candidate
                for candidate in choices
                if candidate.event_index not in used_events
            ]
            for outcome_id, choices in pending.items()
            if outcome_id not in matches
        }
        singleton_claims: dict[int, list[str]] = defaultdict(list)
        for outcome_id, choices in filtered.items():
            if len(choices) == 1:
                singleton_claims[choices[0].event_index].append(outcome_id)

        progress = False
        for event_index, outcome_ids in sorted(singleton_claims.items()):
            if len(outcome_ids) != 1:
                continue
            outcome_id = outcome_ids[0]
            matches[outcome_id] = filtered[outcome_id][0]
            used_events.add(event_index)
            progress = True
        pending = filtered
        if not progress:
            break

    unresolved = {
        outcome_id: [
            candidate
            for candidate in choices
            if candidate.event_index not in used_events
        ]
        for outcome_id, choices in pending.items()
        if outcome_id not in matches
    }
    return matches, unresolved


def _outcome_class(row: dict[str, Any]) -> str:
    status = str(row.get("status", "")).upper()
    pips = common.finite(row.get("result_pips", 0.0), "result_pips")
    if status == "CANCELLED":
        return "cancelled"
    if pips > 0:
        return "win"
    if pips < 0:
        return "loss"
    return "breakeven"


def _policy_stats(
    matched_rows: list[dict[str, Any]], policy_field: str
) -> dict[str, Any]:
    selected = [row for row in matched_rows if bool(row["event"].get(policy_field))]
    classes = Counter(_outcome_class(row["outcome"]) for row in selected)
    total_pips = sum(
        common.finite(row["outcome"].get("result_pips", 0.0), "result_pips")
        for row in selected
    )
    resolved = classes["win"] + classes["loss"] + classes["breakeven"]
    return {
        "matched_n": len(selected),
        "wins": classes["win"],
        "losses": classes["loss"],
        "cancelled": classes["cancelled"],
        "breakeven": classes["breakeven"],
        "total_pips": round(total_pips, 2),
        "win_rate_resolved_percent": (
            round(100.0 * classes["win"] / resolved, 2) if resolved else None
        ),
    }


def _matched_row(
    outcome: dict[str, Any], event: dict[str, Any], candidate: Candidate
) -> dict[str, Any]:
    live_score = _live_score(outcome)
    replay_score = common.finite(event.get("score", 0.0), "replay score")
    return {
        "outcome": outcome,
        "event": event,
        "diagnostics": {
            "entry_diff_pips": round(candidate.entry_diff_pips, 4),
            "time_delta_minutes": round(candidate.time_delta_minutes, 4),
            "live_score": live_score,
            "replay_score": replay_score,
            "score_diff": (
                round(abs(replay_score - live_score), 4)
                if live_score is not None
                else None
            ),
        },
    }


def _build_matched_rows(
    outcomes: list[dict[str, Any]],
    events: list[dict[str, Any]],
    matches: dict[str, Candidate],
) -> list[dict[str, Any]]:
    outcome_by_id = {str(row["id"]): row for row in outcomes}
    rows = [
        _matched_row(
            outcome_by_id[outcome_id],
            events[candidate.event_index],
            candidate,
        )
        for outcome_id, candidate in matches.items()
    ]
    rows.sort(key=lambda row: str(row["outcome"]["created_at"]))
    return rows


def _unresolved_payload(
    events: list[dict[str, Any]],
    unresolved: dict[str, list[Candidate]],
) -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
    unmatched_ids = sorted(
        outcome_id for outcome_id, choices in unresolved.items() if not choices
    )
    ambiguous: dict[str, list[dict[str, Any]]] = {}
    for outcome_id, choices in sorted(unresolved.items()):
        if not choices:
            continue
        ambiguous[outcome_id] = [
            {
                "event_index": candidate.event_index,
                "decision_time": events[candidate.event_index].get("decision_time"),
                "entry": events[candidate.event_index].get("entry"),
                "score": events[candidate.event_index].get("score"),
                "entry_diff_pips": round(candidate.entry_diff_pips, 4),
                "time_delta_minutes": round(candidate.time_delta_minutes, 4),
            }
            for candidate in choices
        ]
    return unmatched_ids, ambiguous


def _validate_expected_sha256(expected: str | None, actual: str) -> str | None:
    if expected is None:
        return None
    normalized = expected.strip().lower()
    if not SHA256_RE.fullmatch(normalized):
        raise ValueError("expected replay event SHA-256 must be 64 hex digits")
    if actual != normalized:
        raise ValueError(
            f"replay event ledger SHA-256 mismatch: {actual}!={normalized}"
        )
    return normalized


def _replay_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        policy: sum(bool(event.get(field)) for event in events)
        for policy, field in POLICY_FIELDS.items()
    }


def _match_gate(
    expected_count: int,
    outcomes: list[dict[str, Any]],
    matched_rows: list[dict[str, Any]],
    unmatched_ids: list[str],
    ambiguous: dict[str, list[dict[str, Any]]],
) -> bool:
    return (
        len(outcomes) == expected_count
        and len(matched_rows) == expected_count
        and not unmatched_ids
        and not ambiguous
    )


def _matching_contract(max_time_minutes: float, max_entry_pips: float) -> dict[str, Any]:
    return {
        "pair_match": "required",
        "direction_match": "required",
        "policy_a_acceptance": "required_candidate_pool",
        "entry_price_consistency": "required",
        "max_entry_pips": max_entry_pips,
        "bounded_temporal_consistency": "required",
        "max_abs_time_delta_minutes": max_time_minutes,
        "created_at_as_sole_key": "forbidden",
        "ambiguous_match": "report_not_force",
        "one_replay_event_per_published_signal": "required",
    }


def _comparison_result(
    *,
    events: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    snapshot: dict[str, Any],
    matched_rows: list[dict[str, Any]],
    unmatched_ids: list[str],
    ambiguous: dict[str, list[dict[str, Any]]],
    events_path: Path,
    outcomes_path: Path,
    events_sha256: str,
    expected_events_sha256: str | None,
    max_time_minutes: float,
    max_entry_pips: float,
) -> dict[str, Any]:
    expected_count = int(snapshot["expected_count"])
    gate = _match_gate(
        expected_count,
        outcomes,
        matched_rows,
        unmatched_ids,
        ambiguous,
    )
    replay_counts = _replay_counts(events)
    policy_stats = {
        policy: _policy_stats(matched_rows, field)
        for policy, field in POLICY_FIELDS.items()
    }
    match_rate = 100.0 * len(matched_rows) / len(outcomes) if outcomes else 0.0
    return {
        "schema_version": 1,
        "status": "COMPLETE" if gate else "PARTIAL_MATCH",
        "match_gate": "PASS" if gate else "FAIL",
        "policy_statistics_complete": gate,
        "matching_contract": _matching_contract(max_time_minutes, max_entry_pips),
        "integrity": {
            "events_path": str(events_path),
            "events_sha256": events_sha256,
            "expected_events_sha256": expected_events_sha256,
            "outcomes_path": str(outcomes_path),
            "outcomes_sha256": common.sha256_file(outcomes_path),
            "outcome_source": snapshot.get("source"),
            "outcome_project_ref": snapshot.get("project_ref"),
            "outcome_query_window": snapshot.get("query_window"),
        },
        "counts": {
            "replay_events": len(events),
            "replay_policy_acceptance": replay_counts,
            "published_outcomes": len(outcomes),
            "matched_outcomes": len(matched_rows),
            "unmatched_outcomes": len(unmatched_ids),
            "ambiguous_outcomes": len(ambiguous),
            "match_rate_percent": round(match_rate, 2),
        },
        "policy_observed_published_outcomes": policy_stats,
        "matched": matched_rows,
        "unmatched_outcome_ids": unmatched_ids,
        "ambiguous": ambiguous,
    }


def compare(
    *,
    events_path: Path,
    outcomes_path: Path,
    expected_events_sha256: str | None,
    max_time_minutes: float,
    max_entry_pips: float,
) -> dict[str, Any]:
    if max_time_minutes <= 0 or max_entry_pips <= 0:
        raise ValueError("matching tolerances must be positive")

    events_sha256 = common.sha256_file(events_path)
    normalized_expected = _validate_expected_sha256(
        expected_events_sha256,
        events_sha256,
    )
    events = _load_events(events_path)
    snapshot, outcomes = _load_outcomes(outcomes_path)
    candidates = _build_candidates(
        outcomes,
        events,
        max_time_minutes=max_time_minutes,
        max_entry_pips=max_entry_pips,
    )
    matches, unresolved = _resolve_unique_matches(candidates)
    matched_rows = _build_matched_rows(outcomes, events, matches)
    unmatched_ids, ambiguous = _unresolved_payload(events, unresolved)
    return _comparison_result(
        events=events,
        outcomes=outcomes,
        snapshot=snapshot,
        matched_rows=matched_rows,
        unmatched_ids=unmatched_ids,
        ambiguous=ambiguous,
        events_path=events_path,
        outcomes_path=outcomes_path,
        events_sha256=events_sha256,
        expected_events_sha256=normalized_expected,
        max_time_minutes=max_time_minutes,
        max_entry_pips=max_entry_pips,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only conservative matcher between deterministic BotA replay "
            "events and a frozen published-outcome snapshot"
        )
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--expected-events-sha256")
    parser.add_argument("--max-time-minutes", type=float, default=45.0)
    parser.add_argument("--max-entry-pips", type=float, default=5.0)
    return parser


def _print_console(result: dict[str, Any]) -> None:
    counts = result["counts"]
    print(f"MATCH_GATE={result['match_gate']}", file=sys.stderr)
    print(f"MATCH_STATUS={result['status']}", file=sys.stderr)
    print(f"REPLAY_EVENTS={counts['replay_events']}", file=sys.stderr)
    print(f"PUBLISHED_OUTCOMES={counts['published_outcomes']}", file=sys.stderr)
    print(f"MATCHED_OUTCOMES={counts['matched_outcomes']}", file=sys.stderr)
    print(f"UNMATCHED_OUTCOMES={counts['unmatched_outcomes']}", file=sys.stderr)
    print(f"AMBIGUOUS_OUTCOMES={counts['ambiguous_outcomes']}", file=sys.stderr)
    print(
        f"MATCH_RATE_PERCENT={counts['match_rate_percent']:.2f}",
        file=sys.stderr,
    )
    replay_counts = counts["replay_policy_acceptance"]
    for policy in ("A", "B", "C"):
        stats = result["policy_observed_published_outcomes"][policy]
        print(
            f"POLICY_{policy}_REPLAY_ACCEPTED={replay_counts[policy]}",
            file=sys.stderr,
        )
        print(
            f"POLICY_{policy}_MATCHED_OUTCOME_N={stats['matched_n']}",
            file=sys.stderr,
        )
        print(f"POLICY_{policy}_WINS={stats['wins']}", file=sys.stderr)
        print(f"POLICY_{policy}_LOSSES={stats['losses']}", file=sys.stderr)
        print(
            f"POLICY_{policy}_CANCELLED={stats['cancelled']}",
            file=sys.stderr,
        )
        print(
            f"POLICY_{policy}_TOTAL_PIPS={stats['total_pips']:.2f}",
            file=sys.stderr,
        )
    if result["match_gate"] == "PASS":
        print(
            "NEXT_ACTION=ROBUSTNESS_AND_FULL_REPLAY_OUTCOME_RESOLUTION",
            file=sys.stderr,
        )
    else:
        print(
            "NEXT_ACTION=CLASSIFY_MATCH_GAPS_DO_NOT_TUNE_STRATEGY",
            file=sys.stderr,
        )


def main() -> int:
    args = _parser().parse_args()
    result = compare(
        events_path=Path(args.events).resolve(),
        outcomes_path=Path(args.outcomes).resolve(),
        expected_events_sha256=args.expected_events_sha256,
        max_time_minutes=args.max_time_minutes,
        max_entry_pips=args.max_entry_pips,
    )
    _print_console(result)
    print("NETWORK_USED=NO", file=sys.stderr)
    print("PRODUCTION_MUTATION=NO", file=sys.stderr)
    sys.stdout.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
