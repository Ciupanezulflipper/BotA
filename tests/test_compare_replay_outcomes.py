from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools import compare_replay_outcomes as matcher


class CompareReplayOutcomesTests(unittest.TestCase):
    @staticmethod
    def _write_events(root: Path, rows: list[dict]) -> Path:
        path = root / "events.jsonl"
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _write_outcomes(root: Path, rows: list[dict]) -> Path:
        path = root / "outcomes.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source": "test",
                    "project_ref": "test-project",
                    "query_window": {},
                    "expected_count": len(rows),
                    "outcomes": rows,
                }
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _event(
        *,
        pair: str,
        direction: str,
        decision_time: str,
        entry: float,
        score: float,
        policy_b: bool,
        policy_c: bool,
    ) -> dict:
        return {
            "pair": pair,
            "direction": direction,
            "decision_time": decision_time,
            "entry": entry,
            "score": score,
            "policy_a_current": True,
            "policy_b_score70_adx_lt30": policy_b,
            "policy_c_score70_adx_lt30_no_extreme": policy_c,
        }

    @staticmethod
    def _make_outcome(
        *,
        outcome_id: str,
        pair: str,
        direction: str,
        created_at: str,
        entry_price: float,
        result_pips: float,
        status: str = "CLOSED",
        live_score: int = 77,
    ) -> dict:
        return {
            "id": outcome_id,
            "pair": pair,
            "direction": direction,
            "created_at": created_at,
            "entry_price": entry_price,
            "result_pips": result_pips,
            "status": status,
            "rationale": f"BotA score={live_score} tier=GREEN",
        }

    def test_unique_matching_and_policy_counterfactual(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            events = [
                self._event(
                    pair="EURUSD",
                    direction="SELL",
                    decision_time="2026-06-09T16:00:00Z",
                    entry=1.15534,
                    score=80.2,
                    policy_b=True,
                    policy_c=True,
                ),
                self._event(
                    pair="GBPUSD",
                    direction="BUY",
                    decision_time="2026-07-14T14:00:00Z",
                    entry=1.34141,
                    score=77.1,
                    policy_b=False,
                    policy_c=False,
                ),
                self._event(
                    pair="EURUSD",
                    direction="BUY",
                    decision_time="2026-06-09T16:00:00Z",
                    entry=1.15534,
                    score=90.0,
                    policy_b=True,
                    policy_c=True,
                ),
            ]
            outcomes = [
                self._make_outcome(
                    outcome_id="one",
                    pair="EURUSD",
                    direction="SELL",
                    created_at="2026-06-09T16:01:30Z",
                    entry_price=1.15535,
                    result_pips=20.0,
                    live_score=80,
                ),
                self._make_outcome(
                    outcome_id="two",
                    pair="GBPUSD",
                    direction="BUY",
                    created_at="2026-07-14T14:01:00Z",
                    entry_price=1.34140,
                    result_pips=-10.0,
                    live_score=77,
                ),
            ]
            events_path = self._write_events(root, events)
            outcomes_path = self._write_outcomes(root, outcomes)

            result = matcher.compare(
                events_path=events_path,
                outcomes_path=outcomes_path,
                expected_events_sha256=None,
                max_time_minutes=45.0,
                max_entry_pips=5.0,
            )

            self.assertEqual(result["match_gate"], "PASS")
            self.assertEqual(result["counts"]["matched_outcomes"], 2)
            self.assertEqual(
                result["policy_observed_published_outcomes"]["A"]["total_pips"],
                10.0,
            )
            self.assertEqual(
                result["policy_observed_published_outcomes"]["B"]["matched_n"],
                1,
            )
            self.assertEqual(
                result["policy_observed_published_outcomes"]["B"]["total_pips"],
                20.0,
            )
            self.assertEqual(
                result["policy_observed_published_outcomes"]["C"]["wins"], 1
            )

    def test_ambiguous_candidates_are_not_forced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            events = [
                self._event(
                    pair="EURUSD",
                    direction="SELL",
                    decision_time="2026-06-09T16:00:00Z",
                    entry=1.15534,
                    score=80.0,
                    policy_b=True,
                    policy_c=True,
                ),
                self._event(
                    pair="EURUSD",
                    direction="SELL",
                    decision_time="2026-06-09T16:15:00Z",
                    entry=1.15536,
                    score=79.0,
                    policy_b=True,
                    policy_c=False,
                ),
            ]
            outcomes = [
                self._make_outcome(
                    outcome_id="ambiguous",
                    pair="EURUSD",
                    direction="SELL",
                    created_at="2026-06-09T16:10:00Z",
                    entry_price=1.15535,
                    result_pips=-13.5,
                )
            ]
            events_path = self._write_events(root, events)
            outcomes_path = self._write_outcomes(root, outcomes)

            result = matcher.compare(
                events_path=events_path,
                outcomes_path=outcomes_path,
                expected_events_sha256=None,
                max_time_minutes=45.0,
                max_entry_pips=5.0,
            )

            self.assertEqual(result["match_gate"], "FAIL")
            self.assertEqual(result["counts"]["matched_outcomes"], 0)
            self.assertEqual(result["counts"]["ambiguous_outcomes"], 1)
            self.assertIn("ambiguous", result["ambiguous"])

    def test_expected_event_hash_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            events_path = self._write_events(
                root,
                [
                    self._event(
                        pair="EURUSD",
                        direction="SELL",
                        decision_time="2026-06-09T16:00:00Z",
                        entry=1.15535,
                        score=80.0,
                        policy_b=True,
                        policy_c=True,
                    )
                ],
            )
            outcomes_path = self._write_outcomes(root, [])

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                matcher.compare(
                    events_path=events_path,
                    outcomes_path=outcomes_path,
                    expected_events_sha256="0" * 64,
                    max_time_minutes=45.0,
                    max_entry_pips=5.0,
                )

    def test_output_cannot_overwrite_input(self) -> None:
        events = Path("/tmp/events.jsonl")
        outcomes = Path("/tmp/outcomes.json")
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            matcher._validate_output_path(events, events, outcomes)
        with self.assertRaisesRegex(ValueError, "must not overwrite"):
            matcher._validate_output_path(outcomes, events, outcomes)
        matcher._validate_output_path(Path("/tmp/result.json"), events, outcomes)

    def test_frozen_supabase_fixture_totals(self) -> None:
        fixture = (
            Path(__file__).resolve().parents[1]
            / "audits"
            / "fixtures"
            / "supabase_bota_m15_20260601_20260801.json"
        )
        data = json.loads(fixture.read_text(encoding="utf-8"))
        outcomes = data["outcomes"]
        self.assertEqual(data["expected_count"], 13)
        self.assertEqual(len(outcomes), 13)
        self.assertEqual(
            round(sum(float(row["result_pips"]) for row in outcomes), 2),
            -71.40,
        )
        classes = [matcher._outcome_class(row) for row in outcomes]
        self.assertEqual(classes.count("win"), 3)
        self.assertEqual(classes.count("loss"), 9)
        self.assertEqual(classes.count("cancelled"), 1)
        digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
