#!/usr/bin/env python3
"""Regression tests for BotA heartbeat delivery and retry policy."""

from __future__ import annotations

import io
import json
import math
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import heartbeat_delivery


WRAPPER = Path(__file__).resolve().parents[1] / "tools" / "heartbeat.sh"


class FakeResponse:
    """Minimal context-managed HTTP response for urllib tests."""

    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self.body = body.encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False

    def getcode(self) -> int:
        return self.status

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self.body
        return self.body[:size]


def write_runtime_health(path: Path) -> None:
    """Write a complete local runtime-health fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "bot_mode": "HEALTHY",
                "market_state": "open",
                "failure_reasons": [],
                "control_plane": {
                    "owned": 7,
                    "required": 7,
                    "running": 7,
                    "orphaned": 0,
                },
                "pipeline_progress": {"healthy": True},
            }
        ),
        encoding="utf-8",
    )


def write_telegram_env(path: Path) -> None:
    """Write non-secret Telegram test credentials."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "TELEGRAM_BOT_TOKEN=unit-test-token\n"
        "TELEGRAM_CHAT_ID='unit-test-chat'\n",
        encoding="utf-8",
    )


class HeartbeatSourcePolicyTests(unittest.TestCase):
    """Protect the production wrapper from regaining embedded transport logic."""

    def test_wrapper_delegates_without_direct_telegram_transport(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("heartbeat_delivery.py", source)
        self.assertIn("BOTA_ROOT", source)
        self.assertNotIn("curl", source)
        self.assertNotIn("api.telegram.org", source)
        self.assertNotIn("<<'PY", source)


class HeartbeatValueAndEnvTests(unittest.TestCase):
    """Validate numeric and environment parsing safety."""

    def test_finite_number_accepts_zero_and_rejects_invalid_values(self) -> None:
        self.assertEqual(heartbeat_delivery.finite_number(0), 0.0)
        self.assertEqual(heartbeat_delivery.finite_number("12.5"), 12.5)
        for value in (-1, math.nan, math.inf, -math.inf, "bad", None):
            with self.subTest(value=value):
                self.assertIsNone(heartbeat_delivery.finite_number(value))

    def test_env_parser_accepts_ascii_keys_without_executing_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "tele.env"
            sentinel = directory / "should-not-run"
            shell_value = f"$(touch {sentinel})"
            path.write_text(
                "# comment\n"
                "TELEGRAM_BOT_TOKEN=token-value\n"
                "TELEGRAM_CHAT_ID=\"chat-value\"\n"
                "SAFE_UNDERSCORE='quoted value'\n"
                "1INVALID=value\n"
                "BAD-KEY=value\n"
                "ÅKEY=value\n"
                f"SHELL={shell_value}\n",
                encoding="utf-8",
            )
            values = heartbeat_delivery.parse_env_file(path)
            sentinel_exists = sentinel.exists()

        self.assertEqual(values["TELEGRAM_BOT_TOKEN"], "token-value")
        self.assertEqual(values["TELEGRAM_CHAT_ID"], "chat-value")
        self.assertEqual(values["SAFE_UNDERSCORE"], "quoted value")
        self.assertEqual(values["SHELL"], shell_value)
        self.assertNotIn("1INVALID", values)
        self.assertNotIn("BAD-KEY", values)
        self.assertNotIn("ÅKEY", values)
        self.assertFalse(sentinel_exists)

    def test_timeout_configuration_is_bounded(self) -> None:
        with patch.dict(
            os.environ,
            {"HEARTBEAT_TELEGRAM_TIMEOUT_SEC": "0"},
            clear=False,
        ):
            minimum = heartbeat_delivery.timeout_from_env()
        with patch.dict(
            os.environ,
            {"HEARTBEAT_TELEGRAM_TIMEOUT_SEC": "999"},
            clear=False,
        ):
            maximum = heartbeat_delivery.timeout_from_env()
        with patch.dict(
            os.environ,
            {"HEARTBEAT_TELEGRAM_TIMEOUT_SEC": "invalid"},
            clear=False,
        ):
            default = heartbeat_delivery.timeout_from_env()

        self.assertEqual(minimum, 1.0)
        self.assertEqual(maximum, 30.0)
        self.assertEqual(default, heartbeat_delivery.DEFAULT_TIMEOUT_SEC)


class HeartbeatSummaryTests(unittest.TestCase):
    """Verify stable local runtime summary generation."""

    def test_valid_health_document_builds_complete_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime_health.json"
            write_runtime_health(path)
            summary = heartbeat_delivery.build_summary(path)

        self.assertIn("mode=HEALTHY", summary)
        self.assertIn("market=open", summary)
        self.assertIn("owned=7/7", summary)
        self.assertIn("running=7/7", summary)
        self.assertIn("orphaned=0", summary)
        self.assertIn("useful_progress=PASS", summary)

    def test_missing_and_invalid_health_documents_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.json"
            invalid = Path(temporary) / "invalid.json"
            invalid.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            missing_summary = heartbeat_delivery.build_summary(missing)
            invalid_summary = heartbeat_delivery.build_summary(invalid)

        self.assertIn("missing or unreadable", missing_summary)
        self.assertIn("runtime_health.json invalid", invalid_summary)


class HeartbeatStateTests(unittest.TestCase):
    """Verify monotonic cadence, failure backoff, and reboot behavior."""

    def test_failure_backoff_is_exponential_and_bounded(self) -> None:
        expected = [300.0, 600.0, 1200.0, 2400.0, 3600.0, 3600.0]
        actual = [heartbeat_delivery.retry_delay(index) for index in range(1, 7)]
        self.assertEqual(actual, expected)

    def test_success_and_failure_state_schedule_distinct_suppression(self) -> None:
        base = heartbeat_delivery.default_state()
        success = heartbeat_delivery.record_success(base, 100.0, "boot-a")
        failure = heartbeat_delivery.record_failure(
            base,
            100.0,
            "boot-a",
            "timeout",
        )

        success_reason, success_remaining = heartbeat_delivery.suppression_reason(
            success, 101.0
        )
        failure_reason, failure_remaining = heartbeat_delivery.suppression_reason(
            failure, 101.0
        )

        self.assertEqual(success_reason, "success_interval")
        self.assertEqual(success_remaining, 3599.0)
        self.assertEqual(failure_reason, "failure_backoff")
        self.assertEqual(failure_remaining, 299.0)
        self.assertFalse(success["delivery_failure"])
        self.assertTrue(failure["delivery_failure"])
        self.assertEqual(failure["last_error"], "timeout")

    def test_boot_identity_change_resets_persisted_monotonic_state(self) -> None:
        state = heartbeat_delivery.record_failure(
            heartbeat_delivery.default_state(),
            5000.0,
            "boot-a",
            "timeout",
        )
        reset = heartbeat_delivery.reset_after_reboot(state, 6000.0, "boot-b")
        self.assertEqual(reset, heartbeat_delivery.default_state())

    def test_monotonic_rollback_resets_state_when_boot_id_is_unavailable(self) -> None:
        state = heartbeat_delivery.record_success(
            heartbeat_delivery.default_state(),
            5000.0,
            "",
        )
        reset = heartbeat_delivery.reset_after_reboot(state, 100.0, "")
        self.assertEqual(reset, heartbeat_delivery.default_state())

    def test_corrupt_state_is_normalized_and_written_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "heartbeat_delivery.json"
            path.write_text(
                json.dumps(
                    {
                        "delivery_failure": False,
                        "consecutive_failures": "99",
                        "last_attempt_monotonic": "bad",
                        "next_retry_monotonic": "not-finite",
                        "last_error": "stale",
                    }
                ),
                encoding="utf-8",
            )
            normalized = heartbeat_delivery.load_state(path)
            heartbeat_delivery.write_state(path, normalized)
            persisted = json.loads(path.read_text(encoding="utf-8"))
            leftovers = list(path.parent.glob("heartbeat_delivery.json.*.tmp"))

        self.assertFalse(normalized["delivery_failure"])
        self.assertEqual(normalized["consecutive_failures"], 0)
        self.assertEqual(normalized["last_attempt_monotonic"], 0.0)
        self.assertEqual(normalized["next_retry_monotonic"], 0.0)
        self.assertEqual(normalized["last_error"], "")
        self.assertEqual(persisted, normalized)
        self.assertEqual(leftovers, [])


class HeartbeatTransportTests(unittest.TestCase):
    """Exercise Telegram response classification without real network calls."""

    def test_success_response_is_accepted(self) -> None:
        response = FakeResponse(200, '{"ok":true}')
        with patch.object(
            heartbeat_delivery.urllib.request,
            "urlopen",
            return_value=response,
        ):
            success, detail = heartbeat_delivery.send_telegram(
                "https://api.telegram.org/bottest/sendMessage",
                "chat",
                "message",
                5.0,
            )
        self.assertTrue(success)
        self.assertEqual(detail, "http_status:200")

    def test_invalid_json_and_url_error_are_reported(self) -> None:
        invalid_response = FakeResponse(200, "not-json")
        with patch.object(
            heartbeat_delivery.urllib.request,
            "urlopen",
            return_value=invalid_response,
        ):
            success, detail = heartbeat_delivery.send_telegram(
                "https://api.telegram.org/bottest/sendMessage",
                "chat",
                "message",
                5.0,
            )
        self.assertFalse(success)
        self.assertIn("invalid_json", detail)

        with patch.object(
            heartbeat_delivery.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            success, detail = heartbeat_delivery.send_telegram(
                "https://api.telegram.org/bottest/sendMessage",
                "chat",
                "message",
                5.0,
            )
        self.assertFalse(success)
        self.assertEqual(detail, "url_error:offline")

    def test_oversized_response_is_bounded(self) -> None:
        oversized = "x" * (heartbeat_delivery.MAX_RESPONSE_BYTES + 100)
        response = FakeResponse(500, oversized)
        with patch.object(
            heartbeat_delivery.urllib.request,
            "urlopen",
            return_value=response,
        ):
            success, detail = heartbeat_delivery.send_telegram(
                "https://api.telegram.org/bottest/sendMessage",
                "chat",
                "message",
                5.0,
            )

        self.assertFalse(success)
        self.assertLessEqual(len(detail), heartbeat_delivery.MAX_DETAIL_CHARS)
        self.assertIn("http_status:500", detail)


class HeartbeatCycleTests(unittest.TestCase):
    """Exercise complete local cycles with delivery mocked at the boundary."""

    def test_dry_run_writes_summary_without_state_or_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_runtime_health(root / "state" / "runtime_health.json")
            output = io.StringIO()
            with (
                patch.dict(os.environ, {"HEARTBEAT_DRY_RUN": "1"}, clear=False),
                patch.object(heartbeat_delivery, "send_telegram") as sender,
                redirect_stdout(output),
            ):
                result = heartbeat_delivery.run_cycle(root)
            state_exists = (root / "state" / "heartbeat_delivery.json").exists()
            log = (root / "logs" / "cron.heartbeat.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(result, 0)
        self.assertIn("mode=HEALTHY", output.getvalue())
        self.assertFalse(state_exists)
        sender.assert_not_called()
        self.assertIn("DRY_RUN", log)

    def test_missing_config_persists_failure_then_suppresses_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_runtime_health(root / "state" / "runtime_health.json")
            with (
                patch.object(
                    heartbeat_delivery.time,
                    "monotonic",
                    side_effect=[100.0, 101.0],
                ),
                patch.object(heartbeat_delivery, "boot_identity", return_value="boot-a"),
                patch.object(heartbeat_delivery, "send_telegram") as sender,
            ):
                first_result = heartbeat_delivery.run_cycle(root)
                second_result = heartbeat_delivery.run_cycle(root)
            state = heartbeat_delivery.load_state(
                root / "state" / "heartbeat_delivery.json"
            )
            log = (root / "logs" / "cron.heartbeat.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(first_result, 0)
        self.assertEqual(second_result, 0)
        self.assertTrue(state["delivery_failure"])
        self.assertEqual(state["consecutive_failures"], 1)
        self.assertEqual(state["next_retry_monotonic"], 400.0)
        sender.assert_not_called()
        self.assertIn("telegram_config_missing", log)
        self.assertIn("reason=failure_backoff", log)

    def test_success_persists_hourly_interval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_runtime_health(root / "state" / "runtime_health.json")
            write_telegram_env(root / "config" / "tele.env")
            with (
                patch.object(heartbeat_delivery.time, "monotonic", return_value=100.0),
                patch.object(heartbeat_delivery, "boot_identity", return_value="boot-a"),
                patch.object(
                    heartbeat_delivery,
                    "send_telegram",
                    return_value=(True, "http_status:200"),
                ) as sender,
            ):
                result = heartbeat_delivery.run_cycle(root)
            state = heartbeat_delivery.load_state(
                root / "state" / "heartbeat_delivery.json"
            )
            log = (root / "logs" / "cron.heartbeat.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(result, 0)
        sender.assert_called_once()
        self.assertFalse(state["delivery_failure"])
        self.assertEqual(state["last_success_monotonic"], 100.0)
        self.assertEqual(state["next_retry_monotonic"], 3700.0)
        self.assertIn("heartbeat sent", log)

    def test_transport_failure_persists_diagnostics_and_backoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "BotA"
            write_runtime_health(root / "state" / "runtime_health.json")
            write_telegram_env(root / "config" / "tele.env")
            with (
                patch.object(heartbeat_delivery.time, "monotonic", return_value=200.0),
                patch.object(heartbeat_delivery, "boot_identity", return_value="boot-a"),
                patch.object(
                    heartbeat_delivery,
                    "send_telegram",
                    return_value=(False, "url_error:offline"),
                ),
            ):
                result = heartbeat_delivery.run_cycle(root)
            state = heartbeat_delivery.load_state(
                root / "state" / "heartbeat_delivery.json"
            )
            log = (root / "logs" / "cron.heartbeat.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(result, 0)
        self.assertTrue(state["delivery_failure"])
        self.assertEqual(state["next_retry_monotonic"], 500.0)
        self.assertEqual(state["last_error"], "url_error:offline")
        self.assertIn("url_error:offline", log)


if __name__ == "__main__":
    unittest.main()
