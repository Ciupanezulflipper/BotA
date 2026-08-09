from __future__ import annotations

import argparse
import contextlib
import fcntl
import io
import os
import select
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Self
from unittest import mock

from tools import native_watchdog_guard as guard

_HOLD_SCRIPT = textwrap.dedent(
    """
    import fcntl, os, sys
    lock_path, mode = sys.argv[1:3]
    fd = os.open(lock_path, os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if mode == "release":
        fcntl.flock(fd, fcntl.LOCK_UN)
    sys.stdout.write("READY\\n")
    sys.stdout.flush()
    try:
        sys.stdin.read()
    finally:
        os._exit(0)
    """
).strip()


class _FlockChild:
    """Spawn a helper child that opens ``lock_path`` and takes a FLOCK.

    ``mode="hold"`` keeps the FLOCK. ``mode="release"`` calls ``LOCK_UN``
    while keeping the fd open. The child exits cleanly on ``stdin`` EOF —
    no signals are ever sent to it.
    """

    def __init__(self, lock_path: Path, mode: str) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-c", _HOLD_SCRIPT, str(lock_path), mode],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert self.proc.stdout is not None
        ready, _, _ = select.select([self.proc.stdout], [], [], 10.0)
        if not ready:
            self.close()
            raise RuntimeError("child did not signal READY within 10s")
        line = self.proc.stdout.readline().strip()
        if line != "READY":
            self.close()
            raise RuntimeError(f"child failed to signal READY, got {line!r}")

    @property
    def pid(self) -> int:
        return self.proc.pid

    def close(self) -> None:
        if self.proc.stdin is not None:
            with contextlib.suppress(OSError):
                self.proc.stdin.close()
        # Deliberately do NOT signal: a hang here surfaces as TimeoutExpired
        # and fails the test rather than issuing a kill.
        try:
            self.proc.wait(timeout=5)
        finally:
            for stream in (self.proc.stdout, self.proc.stderr):
                if stream is not None:
                    with contextlib.suppress(OSError):
                        stream.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


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


class WatchdogFdinfoOwnershipTests(unittest.TestCase):
    def test_active_flock_by_expected_pid_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            with _FlockChild(path, "hold") as child:
                self.assertEqual(
                    guard._fdinfo_flock_holder(path, child.pid), [child.pid]
                )
                print(
                    f"ANDROID_ACCEPTANCE=ACTIVE_FLOCK_DETECTED "
                    f"pid={child.pid} lock={path}",
                    file=sys.stderr,
                )

    def test_lock_un_with_fd_open_is_not_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            with _FlockChild(path, "release") as child:
                with self.assertRaisesRegex(
                    guard.GuardError, "flock_owner_not_confirmed"
                ):
                    guard._fdinfo_flock_holder(path, child.pid)
                print(
                    f"ANDROID_ACCEPTANCE=RELEASED_FLOCK_FD_OPEN_NOT_DETECTED "
                    f"pid={child.pid} lock={path}",
                    file=sys.stderr,
                )

    def test_missing_lock_file_with_pid_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent.lock"
            with self.assertRaisesRegex(guard.GuardError, "flock_lock_missing"):
                guard._fdinfo_flock_holder(path, os.getpid())

    def test_disappeared_pid_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            # PID 0 has no /proc/0/fd directory anywhere.
            with self.assertRaisesRegex(
                guard.GuardError, "flock_pid_disappeared"
            ):
                guard._fdinfo_flock_holder(path, 0)

    def test_fdinfo_denied_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            fake_st = os.stat(path)
            fake_entry = Path("/proc/self/fd/0")

            def fake_iterdir(self):
                if str(self).endswith("/fd"):
                    return iter([fake_entry])
                raise FileNotFoundError

            def fake_read_text(self, *_a, **_kw):
                raise PermissionError("denied")

            with mock.patch(
                "tools.native_watchdog_guard.Path.iterdir", fake_iterdir
            ), mock.patch(
                "tools.native_watchdog_guard.os.stat",
                side_effect=[fake_st, fake_st],
            ), mock.patch(
                "tools.native_watchdog_guard.Path.read_text", fake_read_text
            ), self.assertRaisesRegex(
                guard.GuardError, "flock_fdinfo_denied"
            ):
                guard._fdinfo_flock_holder(path, os.getpid())

    def test_malformed_fdinfo_lock_row_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            fake_st = os.stat(path)
            fake_entry = Path("/proc/self/fd/0")

            def fake_iterdir(self):
                if str(self).endswith("/fd"):
                    return iter([fake_entry])
                raise FileNotFoundError

            def fake_read_text(self, *a, **kw):
                return "pos:\t0\nlock:\t1: FLOCK ADVISORY WRITE not-a-pid 08:01:garbage 0 EOF\n"

            with mock.patch(
                "tools.native_watchdog_guard.Path.iterdir", fake_iterdir
            ), mock.patch(
                "tools.native_watchdog_guard.os.stat",
                side_effect=[fake_st, fake_st],
            ), mock.patch(
                "tools.native_watchdog_guard.Path.read_text", fake_read_text
            ), self.assertRaisesRegex(
                guard.GuardError, "flock_fdinfo_malformed"
            ):
                guard._fdinfo_flock_holder(path, os.getpid())

    def test_pid_mismatch_in_fdinfo_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            fake_st = os.stat(path)
            fake_entry = Path("/proc/self/fd/0")
            major, minor = os.major(fake_st.st_dev), os.minor(fake_st.st_dev)
            row = (
                f"pos:\t0\nlock:\t1: FLOCK ADVISORY WRITE 999999 "
                f"{major:02x}:{minor:02x}:{fake_st.st_ino} 0 EOF\n"
            )

            def fake_iterdir(self):
                if str(self).endswith("/fd"):
                    return iter([fake_entry])
                raise FileNotFoundError

            def fake_read_text(self, *a, **kw):
                return row

            with mock.patch(
                "tools.native_watchdog_guard.Path.iterdir", fake_iterdir
            ), mock.patch(
                "tools.native_watchdog_guard.os.stat",
                side_effect=[fake_st, fake_st],
            ), mock.patch(
                "tools.native_watchdog_guard.Path.read_text", fake_read_text
            ), self.assertRaisesRegex(
                guard.GuardError, "flock_pid_mismatch"
            ):
                guard._fdinfo_flock_holder(path, os.getpid())

    def test_dev_inode_mismatch_in_fdinfo_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            fake_st = os.stat(path)
            fake_entry = Path("/proc/self/fd/0")
            # A row whose FLOCK claims a different inode than the target.
            row = (
                f"pos:\t0\nlock:\t1: FLOCK ADVISORY WRITE {os.getpid()} "
                f"00:00:{fake_st.st_ino + 999999} 0 EOF\n"
            )

            def fake_iterdir(self):
                if str(self).endswith("/fd"):
                    return iter([fake_entry])
                raise FileNotFoundError

            def fake_read_text(self, *a, **kw):
                return row

            with mock.patch(
                "tools.native_watchdog_guard.Path.iterdir", fake_iterdir
            ), mock.patch(
                "tools.native_watchdog_guard.os.stat",
                side_effect=[fake_st, fake_st],
            ), mock.patch(
                "tools.native_watchdog_guard.Path.read_text", fake_read_text
            ), self.assertRaisesRegex(
                guard.GuardError, "flock_dev_inode_mismatch"
            ):
                guard._fdinfo_flock_holder(path, os.getpid())


class WatchdogAbsenceProbeTests(unittest.TestCase):
    def test_missing_lock_file_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nope.lock"
            self.assertIsNone(guard._probe_lock_free(path))

    def test_free_existing_lock_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            self.assertIsNone(guard._probe_lock_free(path))
            # Probe must not leave the lock held: a second acquirer succeeds.
            fd = os.open(path, os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def test_contended_lock_fails_closed_without_invoking_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            with _FlockChild(path, "hold") as child:
                # Sentinel: any subprocess.run against the launcher path
                # would be visible here; the absence probe must never reach
                # a launcher branch.
                with mock.patch.object(
                    guard.subprocess, "run"
                ) as launcher_sentinel, self.assertRaises(guard.GuardError) as ctx:
                    guard._probe_lock_free(path)
                self.assertRegex(str(ctx.exception), "flock_probe_contended")
                launcher_sentinel.assert_not_called()
                print(
                    f"ANDROID_ACCEPTANCE=CONTENDED_ABSENCE_PROBE_FAILS_CLOSED "
                    f"pid={child.pid} lock={path} error={ctx.exception}",
                    file=sys.stderr,
                )

    def test_open_error_other_than_missing_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchdog.lock"
            path.touch()
            with mock.patch(
                "tools.native_watchdog_guard.os.open",
                side_effect=PermissionError("nope"),
            ), self.assertRaisesRegex(
                guard.GuardError, "flock_probe_open_failed"
            ):
                guard._probe_lock_free(path)


class WatchdogMainContendedLockTests(unittest.TestCase):
    """End-to-end fail-closed path when the lock is contended by a peer.

    Exercises ``guard.main`` with zero watchdog pids and a real same-UID
    process holding the watchdog lock. The reviewed launcher must never be
    invoked; the guardian must exit RC 4 and emit
    ``WATCHDOG_GUARD=FAIL:...flock_probe_contended...`` on stderr.
    """

    def test_main_ensure_contended_lock_returns_four_without_launcher(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tools").mkdir()
            (root / "state").mkdir()
            (root / "logs").mkdir()
            watchdog = root / "tools/native_service_daemon_watchdog.py"
            launcher = root / "tools/start_native_service_daemon_watchdog.sh"
            lock = root / "state/native_service_daemon_watchdog.lock"
            watchdog.write_text("# stub watchdog\n", encoding="utf-8")
            launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            launcher.chmod(0o755)
            lock.touch()

            with _FlockChild(lock, "hold") as child, mock.patch.object(
                guard.migration, "process_matches", return_value=[]
            ), mock.patch.object(
                guard.subprocess, "run"
            ) as launcher_sentinel:
                buf = io.StringIO()
                with contextlib.redirect_stderr(buf):
                    rc = guard.main(["--ensure", "--root", str(root)])
                stderr = buf.getvalue()

            self.assertEqual(rc, 4)
            self.assertIn("WATCHDOG_GUARD=FAIL", stderr)
            self.assertIn("flock_probe_contended", stderr)
            launcher_sentinel.assert_not_called()
            print(
                f"ANDROID_ACCEPTANCE=MAIN_CONTENDED_LOCK_NO_LAUNCHER "
                f"rc={rc} launcher_called=NO "
                f"pid={child.pid} lock={lock}",
                file=sys.stderr,
            )


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
                    Path("unused-log-path.jsonl"), guard.GuardError("boom")
                )
            self.assertEqual(rc, 4)
            self.assertIn("WATCHDOG_GUARD=FAIL:boom", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
