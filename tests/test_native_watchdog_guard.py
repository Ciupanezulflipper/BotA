from __future__ import annotations

import argparse
import contextlib
import fcntl
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import native_watchdog_guard as guard


class WatchdogGuardStateTests(unittest.TestCase):
    def test_single_process_with_same_lock_holder_is_healthy(self) -> None:
        self.assertEqual(guard.state_for([101], [101]), "healthy")

    def test_no_process_and_no_lock_holder_is_absent(self) -> None:
        self.assertEqual(guard.state_for([], []), "absent")

    def test_duplicate_watchdog_processes_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            guard.GuardError, "watchdog_process_ambiguous"
        ):
            guard.state_for([101, 102], [101])

    def test_lock_without_watchdog_process_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            guard.GuardError, "watchdog_lock_without_process"
        ):
            guard.state_for([], [101])

    def test_watchdog_process_without_lock_holder_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            guard.GuardError, "watchdog_lock_owner_mismatch"
        ):
            guard.state_for([101], [])

    def test_wrong_lock_holder_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            guard.GuardError, "watchdog_lock_owner_mismatch"
        ):
            guard.state_for([101], [202])

    def test_duplicate_lock_holders_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            guard.GuardError, "watchdog_lock_ambiguous"
        ):
            guard.state_for([101], [101, 202])

    def test_duplicate_identical_rows_are_normalized(self) -> None:
        self.assertEqual(guard.state_for([101, 101], [101, 101]), "healthy")


_PROC_LOCKS_READABLE = os.access("/proc/locks", os.R_OK)


class WatchdogFlockHoldersTests(unittest.TestCase):
    @unittest.skipUnless(
        _PROC_LOCKS_READABLE, "/proc/locks not readable in this environment"
    )
    def test_reports_holder_only_while_flock_is_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            fd = os.open(path, os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertIn(os.getpid(), guard._flock_holders(path))
                fcntl.flock(fd, fcntl.LOCK_UN)
                # Negative case: fd remains open after release. Ownership
                # must not be inferred from the open fd alone.
                self.assertEqual(guard._flock_holders(path), [])
            finally:
                os.close(fd)

    def test_missing_lock_file_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nope.lock"
            self.assertEqual(guard._flock_holders(path), [])

    def test_proc_locks_unreadable_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lock"
            path.touch()
            # Redirect the module's /proc/locks reference to a path that
            # cannot be read. FileNotFoundError is an OSError, so the guard
            # must raise a fail-closed GuardError rather than silently
            # returning an empty holder list.
            with mock.patch.object(
                guard,
                "_PROC_LOCKS",
                Path(tmp) / "definitely_absent" / "proc_locks",
            ), self.assertRaisesRegex(guard.GuardError, "flock_proc_unreadable"):
                guard._flock_holders(path)

    def test_stat_failure_other_than_missing_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lock"
            path.touch()
            with mock.patch(
                "tools.native_watchdog_guard.os.stat",
                side_effect=PermissionError("nope"),
            ), self.assertRaisesRegex(guard.GuardError, "flock_stat_failed"):
                guard._flock_holders(path)


class WatchdogTimeoutArgumentTests(unittest.TestCase):
    def test_finite_zero_and_negative_still_accepted(self) -> None:
        for text, expected in [("0", 0.0), ("-1.5", -1.5), ("15", 15.0)]:
            with self.subTest(text=text):
                ns = guard.arguments(["--timeout", text])
                self.assertEqual(ns.timeout, expected)

    def test_default_timeout_preserved(self) -> None:
        ns = guard.arguments([])
        self.assertEqual(ns.timeout, 15.0)

    def test_rejects_non_finite_timeout_values(self) -> None:
        for bad in ["nan", "NaN", "inf", "+inf", "-inf", "Infinity", "-Infinity"]:
            with self.subTest(bad=bad), contextlib.redirect_stderr(
                io.StringIO()
            ), self.assertRaises(SystemExit):
                guard.arguments(["--timeout", bad])

    def test_finite_float_type_raises_argument_type_error(self) -> None:
        for bad in ["nan", "inf", "-inf"]:
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError):
                guard._finite_float(bad)


class WatchdogEmitFailureTests(unittest.TestCase):
    def test_emit_failure_survives_append_event_oserror(self) -> None:
        with mock.patch.object(
            guard, "append_event", side_effect=OSError("disk full")
        ):
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = guard._emit_failure(
                    Path("/tmp/does-not-matter"), guard.GuardError("boom")
                )
            self.assertEqual(rc, 4)
            self.assertIn("WATCHDOG_GUARD=FAIL:boom", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
