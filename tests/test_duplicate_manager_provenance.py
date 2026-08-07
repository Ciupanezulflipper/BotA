from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import duplicate_manager_provenance as provenance


class DuplicateManagerProvenanceTests(unittest.TestCase):
    def test_watchdog_jsonl_proves_native_watchdog_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "native_service_daemon_watchdog.jsonl"
            log.write_text(
                json.dumps(
                    {
                        "event": "topology_healthy",
                        "manager_pid": 31140,
                        "native_manager_started": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = provenance.infer_attribution(31140, log, [log])

            self.assertEqual(result["status"], "PROVEN")
            self.assertEqual(
                result["creator_class"], "native_service_daemon_watchdog"
            )

    def test_migration_result_proves_migration_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "missing-watchdog.jsonl"
            result_file = root / "native_manager_migration_result.json"
            result_file.write_text(
                json.dumps(
                    {
                        "source_state": "detached_manager",
                        "old_manager_pid": 16360,
                        "new_manager_pid": 31140,
                        "final": {"manager_pid": 31140},
                    }
                ),
                encoding="utf-8",
            )

            result = provenance.infer_attribution(31140, log, [result_file])

            self.assertEqual(result["status"], "PROVEN")
            self.assertEqual(
                result["creator_class"], "native_service_daemon_migration"
            )

    def test_finalizer_result_proves_finalizer_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "missing-watchdog.jsonl"
            result_file = root / "native_watchdog_finalizer_result.json"
            result_file.write_text(
                json.dumps({"manager_pid": 31140}),
                encoding="utf-8",
            )

            result = provenance.infer_attribution(31140, log, [result_file])

            self.assertEqual(result["status"], "PROVEN")
            self.assertEqual(
                result["creator_class"], "native_service_daemon_finalizer"
            )

    def test_unstructured_pid_hit_is_partial_not_proven(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "missing-watchdog.jsonl"
            text_file = root / "shell-history.txt"
            text_file.write_text(
                "echo manager 31140 was observed\n",
                encoding="utf-8",
            )

            result = provenance.infer_attribution(31140, log, [text_file])

            self.assertEqual(result["status"], "PARTIAL")
            self.assertEqual(result["creator_class"], "UNRESOLVED")

    def test_no_direct_evidence_remains_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "missing-watchdog.jsonl"
            text_file = root / "unrelated.txt"
            text_file.write_text("nothing relevant\n", encoding="utf-8")

            result = provenance.infer_attribution(31140, log, [text_file])

            self.assertEqual(result["status"], "UNKNOWN")
            self.assertEqual(result["creator_class"], "UNRESOLVED")
            self.assertEqual(result["evidence"], [])

    def test_relevant_lines_is_bounded_to_matching_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "boot.sh"
            path.write_text(
                "echo harmless\nservice-daemon start\necho done\n",
                encoding="utf-8",
            )

            result = provenance.relevant_lines(path)

            self.assertTrue(result["exists"])
            self.assertEqual(len(result["matching_lines"]), 1)
            self.assertEqual(result["matching_lines"][0]["line"], 2)
            self.assertEqual(
                result["matching_lines"][0]["text"], "service-daemon start"
            )


if __name__ == "__main__":
    unittest.main()
