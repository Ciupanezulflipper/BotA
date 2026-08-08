from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools import classify_replay_match_gaps as classifier


class ReplayMatchGapClassifierTests(unittest.TestCase):
    @staticmethod
    def _event(
        *,
        pair: str = "EURUSD",
        direction: str = "SELL",
        decision_time: str = "2026-06-09T16:00:00Z",
        entry: float = 1.15535,
        accepted: bool = False,
        reject_stage: str = "H1_CONFIRM",
    ) -> dict:
        return {
            "pair": pair,
            "direction": direction,
            "decision_time": decision_time,
            "entry": entry,
            "score": 80.0,
            "policy_a_current": accepted,
            "reject_stage": "ACCEPTED" if accepted else reject_stage,
            "filter_rejected": not accepted,
            "adx_raw": 34.0,
            "rsi_raw": 42.0,
            "h1_trend": "H1_trend_neutral" if not accepted else "H1_trend_confirmed",
            "h4_vote": 0,
            "d1_vote": 0,
            "filter_reasons": [],
        }

    @staticmethod
    def _make_outcome(outcome_id: str = "one") -> dict:
        return {
            "id": outcome_id,
            "pair": "EURUSD",
            "direction": "SELL",
            "created_at": "2026-06-09T16:01:00Z",
            "entry_price": 1.15535,
            "status": "CLOSED",
            "result_pips": -13.5,
            "rationale": "BotA score=80 tier=GREEN",
        }

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _write_events(path: Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )

    def _canonical_files(
        self, root: Path, events: list[dict]
    ) -> tuple[Path, Path, Path, str, str]:
        events_path = root / "events.jsonl"
        comparison_path = root / "comparison.json"
        outcomes_path = root / "outcomes.json"
        self._write_events(events_path, events)

        unmatched = ["one", "two", "three", "four"]
        comparison = {
            "match_gate": "FAIL",
            "counts": {
                "published_outcomes": 13,
                "matched_outcomes": 9,
                "unmatched_outcomes": 4,
                "ambiguous_outcomes": 0,
            },
            "matching_contract": {
                "max_abs_time_delta_minutes": 45.0,
                "max_entry_pips": 5.0,
            },
            "unmatched_outcome_ids": unmatched,
            "ambiguous": {},
        }
        self._write_json(comparison_path, comparison)

        outcomes = [
            self._make_outcome("one"),
            {**self._make_outcome("two"), "created_at": "2026-06-10T16:01:00Z"},
            {**self._make_outcome("three"), "created_at": "2026-06-11T16:01:00Z"},
            {**self._make_outcome("four"), "created_at": "2026-06-12T16:01:00Z"},
        ]
        for index in range(9):
            outcomes.append(
                {
                    **self._make_outcome(f"matched-{index}"),
                    "created_at": f"2026-06-{13 + index:02d}T16:01:00Z",
                }
            )
        self._write_json(outcomes_path, {"outcomes": outcomes})

        events_sha = hashlib.sha256(events_path.read_bytes()).hexdigest()
        comparison_sha = hashlib.sha256(comparison_path.read_bytes()).hexdigest()
        return events_path, comparison_path, outcomes_path, events_sha, comparison_sha

    def test_replay_rejection_within_frozen_window_is_classified(self) -> None:
        outcome = self._make_outcome()
        result = classifier._classify_one(outcome, [self._event(accepted=False)])
        self.assertEqual(
            result["classification"],
            "LIVE_PUBLISHED_BUT_REPLAY_NOT_ACCEPTED_WITHIN_45M",
        )
        self.assertEqual(result["same_direction_within_45m"], 1)
        self.assertEqual(result["policy_a_same_direction_within_45m"], 0)
        self.assertEqual(
            result["same_direction_events_within_45m"][0]["reject_stage"],
            "H1_CONFIRM",
        )

    def test_entry_divergence_is_classified(self) -> None:
        outcome = self._make_outcome()
        event = self._event(accepted=True, entry=1.15610)
        result = classifier._classify_one(outcome, [event])
        self.assertEqual(
            result["classification"],
            "REPLAY_ACCEPTED_WITHIN_45M_BUT_ENTRY_DIFF_GT_5P",
        )
        self.assertEqual(result["policy_a_same_direction_within_45m"], 1)
        self.assertGreater(
            result["same_direction_events_within_45m"][0]["entry_diff_pips"],
            5.0,
        )

    def test_no_same_direction_within_frozen_window_is_classified(self) -> None:
        outcome = self._make_outcome()
        event = self._event(decision_time="2026-06-09T18:00:00Z", accepted=True)
        result = classifier._classify_one(outcome, [event])
        self.assertEqual(
            result["classification"], "NO_SAME_DIRECTION_EVENT_WITHIN_45M"
        )
        self.assertEqual(result["same_direction_within_45m"], 0)
        self.assertIsNotNone(result["nearest_same_direction_within_180m"])

    def test_exact_frozen_contract_candidate_fails_closed(self) -> None:
        outcome = self._make_outcome()
        events = [self._event(accepted=True)]
        with self.assertRaisesRegex(ValueError, "matcher inconsistency"):
            classifier._classify_one(outcome, events)

    def test_canonical_comparison_contract_is_enforced(self) -> None:
        valid = {
            "match_gate": "FAIL",
            "counts": {
                "published_outcomes": 13,
                "matched_outcomes": 9,
                "unmatched_outcomes": 4,
                "ambiguous_outcomes": 0,
            },
            "matching_contract": {
                "max_abs_time_delta_minutes": 45.0,
                "max_entry_pips": 5.0,
            },
            "unmatched_outcome_ids": ["one", "two", "three", "four"],
            "ambiguous": {},
        }
        self.assertEqual(len(classifier._validate_comparison(valid)), 4)
        changed = json.loads(json.dumps(valid))
        changed["matching_contract"]["max_entry_pips"] = 6.0
        with self.assertRaisesRegex(ValueError, "entry tolerance changed"):
            classifier._validate_comparison(changed)

    def test_input_hashes_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"
            path.write_text("abc", encoding="utf-8")
            correct = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(classifier._verify_sha(path, correct, "x"), correct)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                classifier._verify_sha(path, "0" * 64, "x")

    def test_full_classification_preserves_four_gap_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            events = [
                self._event(accepted=False),
                self._event(
                    decision_time="2026-06-10T16:00:00Z",
                    accepted=True,
                    entry=1.15610,
                ),
                self._event(
                    decision_time="2026-06-11T18:00:00Z",
                    accepted=True,
                ),
                self._event(
                    decision_time="2026-06-12T16:00:00Z",
                    direction="BUY",
                    accepted=True,
                ),
            ]
            (
                events_path,
                comparison_path,
                outcomes_path,
                events_sha,
                comparison_sha,
            ) = self._canonical_files(root, events)
            result = classifier.classify(
                events_path=events_path,
                comparison_path=comparison_path,
                outcomes_path=outcomes_path,
                expected_events_sha256=events_sha,
                expected_comparison_sha256=comparison_sha,
            )
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["unmatched_count"], 4)
            self.assertFalse(result["frozen_match_contract"]["tolerance_widened"])
            self.assertFalse(result["diagnostic_window_is_matching_tolerance"])


if __name__ == "__main__":
    unittest.main()
