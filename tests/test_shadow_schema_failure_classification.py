from __future__ import annotations

import unittest
from unittest import mock

import requests

from tools import be_shadow_manager as shadow


class ShadowSchemaFailureClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        shadow.SCHEMA_CHECK_FAILURE_DETAIL = (
            "SCHEMA_COMPATIBILITY_FAILURE: see shadow_manager.log"
        )

    def test_success_keeps_schema_probe_healthy(self) -> None:
        with mock.patch.object(shadow, "sb_get", return_value=[]):
            self.assertTrue(shadow.check_schema_compatibility())

        self.assertEqual(
            shadow.SCHEMA_CHECK_FAILURE_DETAIL,
            "SCHEMA_COMPATIBILITY_FAILURE: see shadow_manager.log",
        )

    def test_dns_failure_is_connectivity_not_schema_mismatch(self) -> None:
        exc = requests.exceptions.ConnectionError(
            "Failed to resolve 'example.supabase.co' ([Errno 7] No address associated with hostname)"
        )

        with (
            mock.patch.object(shadow, "sb_get", side_effect=exc),
            self.assertLogs(shadow.log, level="ERROR") as captured,
        ):
            self.assertFalse(shadow.check_schema_compatibility())

        rendered = "\n".join(captured.output)
        self.assertIn("SCHEMA_CHECK_CONNECTIVITY_FAILURE", rendered)
        self.assertNotIn("ALTER TABLE", rendered)
        self.assertNotIn("Most likely missing", rendered)
        self.assertEqual(
            shadow.SCHEMA_CHECK_FAILURE_DETAIL,
            "SCHEMA_CHECK_CONNECTIVITY_FAILURE: see shadow_manager.log",
        )

    def test_tls_hostname_mismatch_is_tls_not_schema_mismatch(self) -> None:
        exc = requests.exceptions.SSLError(
            "certificate verify failed: Hostname mismatch, certificate is not valid for 'example.supabase.co'"
        )

        with (
            mock.patch.object(shadow, "sb_get", side_effect=exc),
            self.assertLogs(shadow.log, level="ERROR") as captured,
        ):
            self.assertFalse(shadow.check_schema_compatibility())

        rendered = "\n".join(captured.output)
        self.assertIn("SCHEMA_CHECK_TLS_FAILURE", rendered)
        self.assertNotIn("ALTER TABLE", rendered)
        self.assertNotIn("Most likely missing", rendered)
        self.assertEqual(
            shadow.SCHEMA_CHECK_FAILURE_DETAIL,
            "SCHEMA_CHECK_TLS_FAILURE: see shadow_manager.log",
        )

    def test_postgrest_missing_required_column_is_schema_mismatch(self) -> None:
        response = requests.Response()
        response.status_code = 400
        response.url = "https://example.supabase.co/rest/v1/shadow_log"
        response._content = (
            b'{"code":"PGRST204","message":"Could not find the '
            b"'last_candle_ts_processed' column of 'shadow_log' in the schema cache"}
        )
        exc = requests.exceptions.HTTPError(
            "400 Client Error",
            response=response,
        )

        with (
            mock.patch.object(shadow, "sb_get", side_effect=exc),
            self.assertLogs(shadow.log, level="ERROR") as captured,
        ):
            self.assertFalse(shadow.check_schema_compatibility())

        rendered = "\n".join(captured.output)
        self.assertIn("SCHEMA_COMPATIBILITY_FAILURE", rendered)
        self.assertIn("last_candle_ts_processed", rendered)
        self.assertNotIn("ALTER TABLE", rendered)
        self.assertNotIn("Most likely missing", rendered)
        self.assertEqual(
            shadow.SCHEMA_CHECK_FAILURE_DETAIL,
            "SCHEMA_COMPATIBILITY_FAILURE: see shadow_manager.log",
        )

    def test_non_schema_http_failure_is_not_schema_mismatch(self) -> None:
        response = requests.Response()
        response.status_code = 503
        response.url = "https://example.supabase.co/rest/v1/shadow_log"
        response._content = b'{"message":"service unavailable"}'
        exc = requests.exceptions.HTTPError(
            "503 Server Error",
            response=response,
        )

        with (
            mock.patch.object(shadow, "sb_get", side_effect=exc),
            self.assertLogs(shadow.log, level="ERROR") as captured,
        ):
            self.assertFalse(shadow.check_schema_compatibility())

        rendered = "\n".join(captured.output)
        self.assertIn("SCHEMA_CHECK_HTTP_FAILURE", rendered)
        self.assertNotIn("SCHEMA_COMPATIBILITY_FAILURE --", rendered)
        self.assertEqual(
            shadow.SCHEMA_CHECK_FAILURE_DETAIL,
            "SCHEMA_CHECK_HTTP_FAILURE: see shadow_manager.log",
        )


if __name__ == "__main__":
    unittest.main()
