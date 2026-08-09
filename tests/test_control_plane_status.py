from __future__ import annotations

import unittest

from tools import control_plane_status as status


def service_rows() -> dict[str, dict]:
    rows = {
        service: {
            "runsv_count": 1,
            "runsv_pid": 200 + index,
            "runsv_ppid": 100,
            "owner": "manager",
            "service_running": True,
            "wrapper_pid": 500 + index,
        }
        for index, service in enumerate(status.SERVICES, start=1)
    }
    rows["crond"]["wrapper_pid"] = 777
    return rows


class ControlPlaneFailureTests(unittest.TestCase):
    def failures(
        self,
        *,
        rows=None,
        live_crond=None,
        pidfile=777,
        pidfile_error=None,
    ):
        rows = service_rows() if rows is None else rows
        crond_runsv = rows["crond"]["runsv_pid"]
        live_crond = (
            [{"pid": 777, "ppid": crond_runsv, "argv": ["crond", "-n", "-s"]}]
            if live_crond is None
            else live_crond
        )
        return status.topology_failures(
            1,
            7,
            7,
            0,
            0,
            rows,
            live_crond,
            pidfile,
            pidfile_error,
        )

    def test_healthy_crond_parent_wrapper_and_pidfile_pass(self) -> None:
        self.assertEqual(self.failures(), [])

    def test_stale_pid1_crond_fails_parent_and_wrapper_ownership(self) -> None:
        failures = self.failures(
            live_crond=[{"pid": 555, "ppid": 1, "argv": ["crond", "-n", "-s"]}],
            pidfile=555,
        )
        self.assertIn("crond_not_owned_by_current_runsv", failures)
        self.assertIn("crond_parent_not_current_runsv", failures)

    def test_wrong_crond_pidfile_fails(self) -> None:
        self.assertIn("crond_pidfile_not_live_crond", self.failures(pidfile=999))

    def test_missing_crond_pidfile_fails(self) -> None:
        self.assertIn("crond_pidfile:missing", self.failures(pidfile=None, pidfile_error="missing"))

    def test_multiple_live_crond_fails(self) -> None:
        failures = self.failures(
            live_crond=[
                {"pid": 777, "ppid": 207, "argv": ["crond", "-n", "-s"]},
                {"pid": 778, "ppid": 1, "argv": ["crond", "-n", "-s"]},
            ]
        )
        self.assertIn("live_crond_count:2", failures)


if __name__ == "__main__":
    unittest.main()
