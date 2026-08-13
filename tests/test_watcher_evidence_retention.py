from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "watcher_evidence_retention",
    HERE / "tools" / "watcher_evidence_retention.py",
)
retention = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(retention)


class WatcherEvidenceRetentionTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.state = Path(td.name)
        self.now_ns = 2_000_000_000_000

    def _file(self, name: str, *, age_seconds: int) -> Path:
        path = self.state / name
        path.write_text(name, encoding="utf-8")
        mtime_ns = self.now_ns - age_seconds * 1_000_000_000
        os.utime(path, ns=(mtime_ns, mtime_ns))
        return path

    def test_prunes_only_old_files_beyond_keep_count(self):
        newest = self._file("watcher_cycle.new.log", age_seconds=10)
        middle = self._file("watcher_cycle.middle.log", age_seconds=20)
        oldest = self._file("watcher_cycle.old.log", age_seconds=30)
        result = retention.prune(
            self.state,
            keep_per_kind=2,
            hard_cap_per_kind=4,
            grace_seconds=0,
            now_ns=self.now_ns,
        )
        self.assertEqual(result["removed"], 1)
        self.assertTrue(newest.exists())
        self.assertTrue(middle.exists())
        self.assertFalse(oldest.exists())

    def test_grace_window_preserves_recent_excess(self):
        for i in range(5):
            self._file(f"watcher_telegram.{i}.jsonl", age_seconds=30 + i)
        result = retention.prune(
            self.state,
            keep_per_kind=2,
            hard_cap_per_kind=5,
            grace_seconds=3600,
            now_ns=self.now_ns,
        )
        self.assertEqual(result["removed"], 0)
        self.assertEqual(len(list(self.state.glob("watcher_telegram.*.jsonl"))), 5)

    def test_hard_cap_fails_closed_when_recent_files_cannot_be_pruned(self):
        for i in range(5):
            self._file(f"watcher_supabase.{i}.jsonl", age_seconds=10)
        with self.assertRaises(RuntimeError):
            retention.prune(
                self.state,
                keep_per_kind=2,
                hard_cap_per_kind=4,
                grace_seconds=3600,
                now_ns=self.now_ns,
            )

    def test_symlink_is_never_deleted_or_followed(self):
        target = self.state / "outside.txt"
        target.write_text("keep", encoding="utf-8")
        link = self.state / "watcher_cycle.link.log"
        link.symlink_to(target)
        retention.prune(
            self.state,
            keep_per_kind=1,
            hard_cap_per_kind=2,
            grace_seconds=0,
            now_ns=self.now_ns,
        )
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_unrelated_files_are_untouched(self):
        other = self._file("pipeline_progress.json", age_seconds=10_000)
        retention.prune(
            self.state,
            keep_per_kind=1,
            hard_cap_per_kind=2,
            grace_seconds=0,
            now_ns=self.now_ns,
        )
        self.assertTrue(other.exists())


if __name__ == "__main__":
    unittest.main()
