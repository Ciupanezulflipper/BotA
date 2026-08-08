#!/usr/bin/env python3
"""Match deterministic replay events to frozen published BotA outcomes offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_FIELDS = {
    "A": "policy_a_current",
    "B": "policy_b_score70_adx_lt30",
    "C": "policy_c_score70_adx_lt30_no_extreme",
}
SCORE_RE = re.compile(r"\bscore=([0-9]+(?:\.[0-9]+)?)\b")


@dataclass(frozen=True)
class Candidate:
    event_index: int
    entry_diff_pips: float
    time_delta_minutes: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def _finite_number(value: Any, field: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite {field}")
    return number


def _load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"event line {line_number} is not an object")
            events.append(value)
    if not events:
        raise ValueError("replay event ledger is empty")
    return events


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
    published_entry = _finite_number(outcome.get("entry_price"), "entry_price")
    replay_entry = _finite_number(event.get("entry"), "replay entry")
    if published_entry <= 0 or replay_entry <= 0:
        return None

    entry_diff_pips = abs(replay_entry - published_entry) / _pip_size(pair)
    if entry_diff_pips > max_entry_pips:
        return None

    published_time = _parse_utc(str(outcome.get("created_at", "")))
    decision_time = _parse_utc(str(event.get("decision_time", "")))
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
        candidates = [
            candidate
            for index, event in enumerate(events)
            if (
                candidate := _candidate(
                    outcome,
                    event,
                    index,
                    max_time_minutes=max_time_minutes,
                    max_entry_pips=max_entry_pips,
                )
            )
            is not None
        ]
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
            match = filtered[outcome_id][0]
            matches[outcome_id] = match
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
    pips = _finite_number(row.get("result_pips", 0.0), "result_pips")
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
        _finite_number(row["outcome"].get("result_pips", 0.0), "result_pips")
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
    replay_score = _finite_number(event.get("score", 0.0), "replay score")
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

    events_sha256 = _sha256(events_path)
    if expected_events_sha256 and events_sha256 != expected_events_sha256.lower():
        raise ValueError(
            "replay event ledger SHA-256 mismatch: "
            f"{events_sha256}!={expected_events_sha256.lower()}"
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
    outcome_by_id = {str(row["id"]): row for row in outcomes}

    matched_rows = [
        _matched_row(
            outcome_by_id[outcome_id],
            events[candidate.event_index],
            candidate,
        )
        for outcome_id, candidate in matches.items()
    ]
    matched_rows.sort(key=lambda row: str(row["outcome"]["created_at"]))

    unmatched_ids = sorted(
        outcome_id for outcome_id, choices in unresolved.items() if not choices
    )
    ambiguous = {
        outcome_id: [
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
        for outcome_id, choices in sorted(unresolved.items())
        if choices
    }

    expected_count = int(snapshot["expected_count"])
    match_gate = (
        len(outcomes) == expected_count
        and len(matched_rows) == expected_count
        and not unmatched_ids
        and not ambiguous
    )

    replay_counts = {
        policy: sum(bool(event.get(field)) for event in events)
        for policy, field in POLICY_FIELDS.items()
    }
    policy_stats = {
        policy: _policy_stats(matched_rows, field)
        for policy, field in POLICY_FIELDS.items()
    }

    return {
        "schema_version": 1,
        "status": "COMPLETE" if match_gate else "PARTIAL_MATCH",
        "match_gate": "PASS" if match_gate else "FAIL",
        "policy_statistics_complete": match_gate,
        "matching_contract": {
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
        },
        "integrity": {
            "events_path": str(events_path),
            "events_sha256": events_sha256,
            "expected_events_sha256": expected_events_sha256,
            "outcomes_path": str(outcomes_path),
            "outcomes_sha256": _sha256(outcomes_path),
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
            "match_rate_percent": round(
                100.0 * len(matched_rows) / len(outcomes), 2
            )
            if outcomes
            else 0.0,
        },
        "policy_observed_published_outcomes": policy_stats,
        "matched": matched_rows,
        "unmatched_outcome_ids": unmatched_ids,
        "ambiguous": ambiguous,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Offline conservative matcher between deterministic BotA replay "
            "events and a frozen published-outcome snapshot"
        )
    )
    parser.add_argument("--events", required=True)
    parser.add_argument("--outcomes", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-events-sha256")
    parser.add_argument("--max-time-minutes", type=float, default=45.0)
    parser.add_argument("--max-entry-pips", type=float, default=5.0)
    return parser


def _print_console(result: dict[str, Any]) -> None:
    counts = result["counts"]
    print(f"MATCH_GATE={result['match_gate']}")
    print(f"MATCH_STATUS={result['status']}")
    print(f"REPLAY_EVENTS={counts['replay_events']}")
    print(f"PUBLISHED_OUTCOMES={counts['published_outcomes']}")
    print(f"MATCHED_OUTCOMES={counts['matched_outcomes']}")
    print(f"UNMATCHED_OUTCOMES={counts['unmatched_outcomes']}")
    print(f"AMBIGUOUS_OUTCOMES={counts['ambiguous_outcomes']}")
    print(f"MATCH_RATE_PERCENT={counts['match_rate_percent']:.2f}")
    replay_counts = counts["replay_policy_acceptance"]
    for policy in ("A", "B", "C"):
        stats = result["policy_observed_published_outcomes"][policy]
        print(f"POLICY_{policy}_REPLAY_ACCEPTED={replay_counts[policy]}")
        print(f"POLICY_{policy}_MATCHED_OUTCOME_N={stats['matched_n']}")
        print(f"POLICY_{policy}_WINS={stats['wins']}")
        print(f"POLICY_{policy}_LOSSES={stats['losses']}")
        print(f"POLICY_{policy}_CANCELLED={stats['cancelled']}")
        print(f"POLICY_{policy}_TOTAL_PIPS={stats['total_pips']:.2f}")
    if result["match_gate"] == "PASS":
        print("NEXT_ACTION=ROBUSTNESS_AND_FULL_REPLAY_OUTCOME_RESOLUTION")
    else:
        print("NEXT_ACTION=CLASSIFY_MATCH_GAPS_DO_NOT_TUNE_STRATEGY")


def main() -> int:
    args = _parser().parse_args()
    output = Path(args.output).resolve()
    result = compare(
        events_path=Path(args.events).resolve(),
        outcomes_path=Path(args.outcomes).resolve(),
        expected_events_sha256=args.expected_events_sha256,
        max_time_minutes=args.max_time_minutes,
        max_entry_pips=args.max_entry_pips,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _print_console(result)
    print(f"COMPARISON_OUTPUT={output}")
    print("NETWORK_USED=NO")
    print("PRODUCTION_MUTATION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
