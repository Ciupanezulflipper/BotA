from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "verify_replay_dataset.py"
SPEC = importlib.util.spec_from_file_location("verify_replay_dataset", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load verify_replay_dataset")
v = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v
SPEC.loader.exec_module(v)


class ReplayDatasetVerifierTests(unittest.TestCase):
    @staticmethod
    def _make_dataset(root: Path) -> tuple[Path, Path]:
        dataset = root / "data" / "replay" / "unit-replay"
        csv_path = dataset / "candles" / "EURUSD_M15.csv"
        csv_path.parent.mkdir(parents=True)
        csv_path.write_text(
            "time,open,high,low,close\n"
            "2026-06-01 00:00:00,1.10000000,1.10100000,1.09900000,1.10050000\n"
            "2026-06-01 00:15:00,1.10050000,1.10150000,1.10000000,1.10100000\n"
            "2026-06-01 00:30:00,1.10100000,1.10200000,1.10050000,1.10150000\n"
            "2026-06-01 00:45:00,1.10150000,1.10250000,1.10100000,1.10200000\n",
            encoding="utf-8",
        )
        raw = csv_path.read_bytes()
        manifest = {
            "schema_version": 1,
            "dataset_id": "unit-replay",
            "status": "COMPLETE",
            "provider": "oanda",
            "price_component": "M",
            "production_cache_touched": False,
            "range": {
                "start_utc": "2026-06-01T00:00:00Z",
                "end_utc_exclusive": "2026-06-01T01:00:00Z",
            },
            "pairs": ["EURUSD"],
            "timeframes": ["M15"],
            "streams": [
                {
                    "pair": "EURUSD",
                    "timeframe": "M15",
                    "request_count": 1,
                    "http_attempts": 1,
                    "rows": 4,
                    "first_time": "2026-06-01T00:00:00Z",
                    "last_time": "2026-06-01T00:45:00Z",
                    "provider_leading_overlaps_observed": 0,
                    "csv": "candles/EURUSD_M15.csv",
                }
            ],
            "artifacts": [
                {
                    "path": "candles/EURUSD_M15.csv",
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            ],
        }
        (dataset / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return dataset, csv_path

    @staticmethod
    def _verification_kwargs(dataset: Path, *, min_warmup_bars: int) -> dict[str, object]:
        return {
            "dataset_root": dataset,
            "expected_dataset_id": "unit-replay",
            "raw_start": v.parse_utc("2026-06-01T00:00:00Z"),
            "raw_end": v.parse_utc("2026-06-01T01:00:00Z"),
            "evaluation_start": v.parse_utc("2026-06-01T00:30:00Z"),
            "pairs": ["EURUSD"],
            "timeframes": ["M15"],
            "min_warmup_bars": min_warmup_bars,
        }

    def test_complete_dataset_passes_hash_csv_and_warmup_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, _ = self._make_dataset(Path(tmp))
            kwargs = self._verification_kwargs(dataset, min_warmup_bars=2)
            result = v.verify_dataset(**kwargs)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["artifact_hash_failures"], 0)
            self.assertEqual(result["stream_count"], 1)
            self.assertEqual(result["streams"][0]["pre_evaluation_rows"], 2)
            self.assertEqual(result["streams"][0]["evaluation_rows"], 2)

    def test_checksum_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, csv_path = self._make_dataset(Path(tmp))
            csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            kwargs = self._verification_kwargs(dataset, min_warmup_bars=2)
            with self.assertRaisesRegex(ValueError, "artifact .* mismatch"):
                v.verify_dataset(**kwargs)

    def test_failed_marker_makes_dataset_ineligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, _ = self._make_dataset(Path(tmp))
            (dataset / "FAILED.json").write_text('{"status":"FAILED"}\n', encoding="utf-8")
            kwargs = self._verification_kwargs(dataset, min_warmup_bars=2)
            with self.assertRaisesRegex(ValueError, "FAILED.json"):
                v.verify_dataset(**kwargs)

    def test_insufficient_warmup_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, _ = self._make_dataset(Path(tmp))
            kwargs = self._verification_kwargs(dataset, min_warmup_bars=3)
            with self.assertRaisesRegex(ValueError, "insufficient warm-up candles"):
                v.verify_dataset(**kwargs)


if __name__ == "__main__":
    unittest.main()
