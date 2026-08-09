from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
