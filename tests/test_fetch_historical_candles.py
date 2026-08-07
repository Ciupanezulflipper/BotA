from __future__ import annotations

import hashlib
import importlib.util
import json
import ssl
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "fetch_historical_candles.py"
SPEC = importlib.util.spec_from_file_location("fetch_historical_candles", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load fetch_historical_candles")
h = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = h
SPEC.loader.exec_module(h)


def z(text: str) -> datetime:
    return h.parse_utc(text)


def oanda_body(times: list[str], *, incomplete_last: bool = False, shift: float = 0.0, index_offset: int = 0) -> bytes:
    candles = []
    for index, stamp in enumerate(times):
        base = 1.1000 + index * 0.001 + shift
        candles.append(
            {
                "complete": not (incomplete_last and index == len(times) - 1),
                "volume": 10 + index + index_offset,
                "time": stamp,
                "mid": {
                    "o": f"{base:.5f}",
                    "h": f"{base + 0.0008:.5f}",
                    "l": f"{base - 0.0008:.5f}",
                    "c": f"{base + 0.0002:.5f}",
                },
            }
        )
    return json.dumps({"candles": candles}).encode("utf-8")


class HistoricalCandlesTests(unittest.TestCase):
    def test_pair_timeframe_and_request_contract(self):
        self.assertEqual(h.normalize_pair("eur/usd"), "EURUSD")
        self.assertEqual(h.normalize_tf("1d"), "D1")
        path = h.request_path("EURUSD", "D1", z("2026-06-01T00:00:00Z"), z("2026-06-02T00:00:00Z"))
        parsed = urlsplit(path)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/v3/instruments/EUR_USD/candles")
        self.assertEqual(query["granularity"], ["D"])
        self.assertEqual(query["price"], ["M"])
        self.assertNotIn("count", query)

    def test_chunk_plan_stays_bounded_and_contiguous(self):
        windows = h.plan_windows(
            z("2026-06-01T00:00:00Z"),
            z("2026-06-01T01:00:00Z"),
            "M15",
            max_candles_per_request=3,
        )
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0][1], windows[1][0])
        self.assertEqual(windows[-1][1], z("2026-06-01T01:00:00Z"))

    def test_parser_excludes_incomplete_candle(self):
        body = oanda_body(
            ["2026-06-01T00:00:00.000000000Z", "2026-06-01T00:15:00.000000000Z"],
            incomplete_last=True,
        )
        candles = h.parse_oanda_payload(body)
        self.assertEqual(len(candles), 1)
        self.assertEqual(h.iso_z(candles[0].time), "2026-06-01T00:00:00Z")

    def test_reconciliation_deduplicates_identical_boundary_and_rejects_conflict(self):
        first = h.parse_oanda_payload(oanda_body(["2026-06-01T00:00:00Z", "2026-06-01T00:15:00Z"]))
        second = h.parse_oanda_payload(oanda_body(["2026-06-01T00:15:00Z", "2026-06-01T00:30:00Z"]))
        second[0] = h.Candle(
            time=first[1].time,
            open=first[1].open,
            high=first[1].high,
            low=first[1].low,
            close=first[1].close,
            volume=first[1].volume,
        )
        self.assertIsNot(second[0], first[1])
        self.assertEqual(second[0], first[1])
        rows, duplicates = h.reconcile_candles([first, second])
        self.assertEqual(len(rows), 3)
        self.assertEqual(duplicates, 1)

        conflicting = list(second)
        conflicting[0] = h.Candle(
            time=first[1].time,
            open=first[1].open + 0.01,
            high=first[1].high + 0.01,
            low=first[1].low + 0.01,
            close=first[1].close + 0.01,
            volume=first[1].volume,
        )
        with self.assertRaises(ValueError):
            h.reconcile_candles([first, conflicting])

    def test_provider_aligned_h4_leading_candle_is_allowed(self):
        candles = h.parse_oanda_payload(
            oanda_body(
                [
                    "2026-05-31T21:00:00Z",
                    "2026-06-01T01:00:00Z",
                    "2026-06-01T05:00:00Z",
                ]
            )
        )
        leading = h._validate_chunk_window(
            candles,
            pair="EURUSD",
            timeframe="H4",
            window_start=z("2026-06-01T00:00:00Z"),
            window_end=z("2026-06-01T08:00:00Z"),
        )
        self.assertEqual(leading, 1)

    def test_provider_candle_older_than_one_timeframe_still_fails_closed(self):
        candles = h.parse_oanda_payload(
            oanda_body(
                [
                    "2026-05-31T20:00:00Z",
                    "2026-06-01T01:00:00Z",
                ]
            )
        )
        window_start = z("2026-06-01T00:00:00Z")
        window_end = z("2026-06-01T08:00:00Z")
        with self.assertRaises(ValueError):
            h._validate_chunk_window(
                candles,
                pair="EURUSD",
                timeframe="H4",
                window_start=window_start,
                window_end=window_end,
            )

    def test_preview_performs_no_network_and_creates_no_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preview = h.build_preview(
                repo_root=root,
                dataset_id="preview-1",
                pairs=["EURUSD", "GBPUSD"],
                timeframes=["M15", "H1"],
                start_utc=z("2026-06-01T00:00:00Z"),
                end_utc=z("2026-06-02T00:00:00Z"),
                max_candles_per_request=4500,
                base_url=h.DEFAULT_OANDA_URL,
            )
            self.assertFalse(preview["network_permitted"])
            self.assertFalse((root / "data" / "replay" / "preview-1").exists())

    def test_h4_aligned_leading_candle_acquires_and_filters_dataset_boundary(self):
        def fake_transport(base_url, path_and_query, token, timeout):
            return h.HttpResponse(
                200,
                {"RequestID": "h4-alignment"},
                oanda_body(
                    [
                        "2026-05-31T21:00:00Z",
                        "2026-06-01T01:00:00Z",
                        "2026-06-01T05:00:00Z",
                    ]
                ),
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = h.acquire_dataset(
                repo_root=root,
                dataset_id="h4-aligned",
                pairs=["EURUSD"],
                timeframes=["H4"],
                start_utc=z("2026-06-01T00:00:00Z"),
                end_utc=z("2026-06-01T08:00:00Z"),
                base_url=h.DEFAULT_OANDA_URL,
                token="test-token",
                transport=fake_transport,
                recorded_at=z("2026-08-07T20:10:49Z"),
            )
            stream = manifest["streams"][0]
            self.assertEqual(stream["rows"], 2)
            self.assertEqual(stream["first_time"], "2026-06-01T01:00:00Z")
            self.assertEqual(stream["provider_leading_overlaps_observed"], 1)
            csv_path = root / "data" / "replay" / "h4-aligned" / "candles" / "EURUSD_H4.csv"
            text = csv_path.read_text(encoding="utf-8")
            self.assertNotIn("2026-05-31 21:00:00", text)
            self.assertIn("2026-06-01 01:00:00", text)

    def test_dataset_is_immutable_and_manifest_checksums_match(self):
        calls = []

        def fake_transport(base_url, path_and_query, token, timeout):
            calls.append((base_url, path_and_query, token, timeout))
            query = parse_qs(urlsplit(path_and_query).query)
            start = h.parse_utc(query["from"][0])
            end = h.parse_utc(query["to"][0])
            stamps = []
            cursor = start
            while cursor <= end:
                stamps.append(h.iso_z(cursor))
                cursor += h.timedelta(minutes=15)
            global_start = h.parse_utc("2026-06-01T00:00:00Z")
            index_offset = int((start - global_start).total_seconds() / 900.0)
            shift = index_offset * 0.001
            body = oanda_body(stamps, shift=shift, index_offset=index_offset)
            return h.HttpResponse(200, {"RequestID": "abc", "Content-Type": "application/json"}, body)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live_cache = root / "data" / "candles" / "EURUSD_M15.csv"
            live_cache.parent.mkdir(parents=True)
            live_cache.write_text("sentinel\n", encoding="utf-8")
            before = hashlib.sha256(live_cache.read_bytes()).hexdigest()

            manifest = h.acquire_dataset(
                repo_root=root,
                dataset_id="unit-dataset",
                pairs=["EURUSD"],
                timeframes=["M15"],
                start_utc=z("2026-06-01T00:00:00Z"),
                end_utc=z("2026-06-01T01:00:00Z"),
                base_url=h.DEFAULT_OANDA_URL,
                token="test-token",
                max_candles_per_request=3,
                transport=fake_transport,
                recorded_at=z("2026-08-07T20:00:00Z"),
            )
            dataset = root / "data" / "replay" / "unit-dataset"
            self.assertEqual(manifest["status"], "COMPLETE")
            self.assertEqual(manifest["streams"][0]["rows"], 4)
            self.assertEqual(manifest["streams"][0]["request_count"], 2)
            self.assertEqual(before, hashlib.sha256(live_cache.read_bytes()).hexdigest())
            self.assertTrue((dataset / "manifest.json").is_file())
            self.assertTrue((dataset / "candles" / "EURUSD_M15.csv").is_file())
            self.assertEqual(len(calls), 2)
            for record in manifest["artifacts"]:
                path = dataset / record["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])

            manifest_before = (dataset / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                h.acquire_dataset(
                    repo_root=root,
                    dataset_id="unit-dataset",
                    pairs=["EURUSD"],
                    timeframes=["M15"],
                    start_utc=z("2026-06-01T00:00:00Z"),
                    end_utc=z("2026-06-01T01:00:00Z"),
                    base_url=h.DEFAULT_OANDA_URL,
                    token="test-token",
                    transport=fake_transport,
                )
            self.assertEqual(manifest_before, (dataset / "manifest.json").read_bytes())

    def test_failed_http_preserves_raw_evidence_and_failure_marker(self):
        def failing_transport(base_url, path_and_query, token, timeout):
            return h.HttpResponse(400, {"RequestID": "bad"}, b'{"errorMessage":"bad request"}')

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError):
                h.acquire_dataset(
                    repo_root=root,
                    dataset_id="failed-dataset",
                    pairs=["EURUSD"],
                    timeframes=["M15"],
                    start_utc=z("2026-06-01T00:00:00Z"),
                    end_utc=z("2026-06-01T01:00:00Z"),
                    base_url=h.DEFAULT_OANDA_URL,
                    token="test-token",
                    transport=failing_transport,
                    recorded_at=z("2026-08-07T20:00:00Z"),
                )
            dataset = root / "data" / "replay" / "failed-dataset"
            self.assertTrue(
                (dataset / "raw" / "EURUSD" / "M15" / "chunk-0000-attempt-01.json").is_file()
            )
            failure = json.loads((dataset / "FAILED.json").read_text(encoding="utf-8"))
            self.assertEqual(failure["status"], "FAILED")
            self.assertFalse(failure["production_cache_touched"])

    def test_retryable_http_preserves_each_attempt_and_succeeds(self):
        statuses = [503, 429, 200]
        calls = []
        sleeps = []

        def flaky_transport(base_url, path_and_query, token, timeout):
            status = statuses[len(calls)]
            calls.append(status)
            if status != 200:
                return h.HttpResponse(
                    status,
                    {"RequestID": f"attempt-{len(calls)}"},
                    json.dumps({"errorMessage": f"status {status}"}).encode("utf-8"),
                )
            body = oanda_body(
                [
                    "2026-06-01T00:00:00Z",
                    "2026-06-01T00:15:00Z",
                    "2026-06-01T00:30:00Z",
                    "2026-06-01T00:45:00Z",
                    "2026-06-01T01:00:00Z",
                ]
            )
            return h.HttpResponse(200, {"RequestID": "attempt-3"}, body)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = h.acquire_dataset(
                repo_root=root,
                dataset_id="retry-dataset",
                pairs=["EURUSD"],
                timeframes=["M15"],
                start_utc=z("2026-06-01T00:00:00Z"),
                end_utc=z("2026-06-01T01:00:00Z"),
                base_url=h.DEFAULT_OANDA_URL,
                token="test-token",
                transport=flaky_transport,
                sleep_fn=sleeps.append,
                recorded_at=z("2026-08-07T20:00:00Z"),
            )
            dataset = root / "data" / "replay" / "retry-dataset"
            self.assertEqual(calls, [503, 429, 200])
            self.assertEqual(sleeps, [0.5, 1.0])
            self.assertEqual(manifest["streams"][0]["request_count"], 1)
            self.assertEqual(manifest["streams"][0]["http_attempts"], 3)
            for attempt in range(1, 4):
                stem = f"chunk-0000-attempt-{attempt:02d}.json"
                self.assertTrue((dataset / "raw" / "EURUSD" / "M15" / stem).is_file())
                self.assertTrue((dataset / "metadata" / "EURUSD" / "M15" / stem).is_file())

    def test_transient_ssl_eof_retries_preserves_metadata_and_succeeds(self):
        calls = []
        sleeps = []

        def flaky_transport(base_url, path_and_query, token, timeout):
            calls.append(len(calls) + 1)
            if len(calls) < 3:
                raise ssl.SSLEOFError(8, "simulated unexpected EOF")
            return h.HttpResponse(
                200,
                {"RequestID": "ssl-recovered"},
                oanda_body(
                    [
                        "2026-06-01T00:00:00Z",
                        "2026-06-01T00:15:00Z",
                        "2026-06-01T00:30:00Z",
                        "2026-06-01T00:45:00Z",
                    ]
                ),
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = h.acquire_dataset(
                repo_root=root,
                dataset_id="ssl-retry-dataset",
                pairs=["EURUSD"],
                timeframes=["M15"],
                start_utc=z("2026-06-01T00:00:00Z"),
                end_utc=z("2026-06-01T01:00:00Z"),
                base_url=h.DEFAULT_OANDA_URL,
                token="test-token",
                transport=flaky_transport,
                sleep_fn=sleeps.append,
                recorded_at=z("2026-08-07T20:29:19Z"),
            )
            dataset = root / "data" / "replay" / "ssl-retry-dataset"
            self.assertEqual(calls, [1, 2, 3])
            self.assertEqual(sleeps, [0.5, 1.0])
            self.assertEqual(manifest["streams"][0]["http_attempts"], 3)

            for attempt in (1, 2):
                stem = f"chunk-0000-attempt-{attempt:02d}.json"
                meta_path = dataset / "metadata" / "EURUSD" / "M15" / stem
                raw_path = dataset / "raw" / "EURUSD" / "M15" / stem
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["transport_error"]["type"], "SSLEOFError")
                self.assertFalse(raw_path.exists())

            success_stem = "chunk-0000-attempt-03.json"
            self.assertTrue((dataset / "raw" / "EURUSD" / "M15" / success_stem).is_file())
            self.assertTrue((dataset / "metadata" / "EURUSD" / "M15" / success_stem).is_file())

    def test_dotenv_is_read_as_data_and_environment_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "OANDA_API_TOKEN='from-file'\nOANDA_API_URL=https://api-fxpractice.oanda.com\nIGNORED=$(touch nope)\n",
                encoding="utf-8",
            )
            url, token = h.oanda_config(root, environ={})
            self.assertEqual(url, h.DEFAULT_OANDA_URL)
            self.assertEqual(token, "from-file")
            self.assertFalse((root / "nope").exists())

            url, token = h.oanda_config(
                root,
                environ={"OANDA_API_TOKEN": "from-env", "OANDA_API_URL": "https://api-fxtrade.oanda.com"},
            )
            self.assertEqual(url, "https://api-fxtrade.oanda.com")
            self.assertEqual(token, "from-env")

    def test_unapproved_oanda_origin_is_rejected(self):
        for bad in (
            "http://api-fxpractice.oanda.com",
            "https://evil.example.com",
            "https://api-fxpractice.oanda.com.evil.example",
            "https://user:pass@api-fxpractice.oanda.com",
            "https://api-fxpractice.oanda.com/path",
            "https://api-fxpractice.oanda.com:8443",
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                h.validate_base_url(bad)

    def test_dataset_id_cannot_escape_replay_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for bad in ("../escape", "/absolute", "a/b", "", ".", "a" * 65):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    h.dataset_path_preview(root, bad)


if __name__ == "__main__":
    unittest.main()
