from pathlib import Path
import subprocess
import unittest
from unittest import mock

from tools import runsvdir_guard_runtime as runtime


ROOT = Path("/data/data/com.termux/files/usr/var/service")
SV = Path("/data/data/com.termux/files/usr/bin/sv")
RUNSVDIR = Path("/data/data/com.termux/files/usr/bin/runsvdir")
LOG = Path("/tmp/runsvdir.log")


def healthy_topology(manager: int = 100) -> dict:
    services = {
        name: {
            "runsv_count": 1,
            "runsv_pid": 200 + index,
            "runsv_ppid": manager,
            "owner": "manager",
        }
        for index, name in enumerate(runtime.base.SERVICES)
    }
    return {
        "manager_count": 1,
        "manager_pid": manager,
        "services": services,
        "owned": len(runtime.base.SERVICES),
        "orphaned": 0,
        "invalid": 0,
        "duplicates": 0,
    }


class RunningStateTests(unittest.TestCase):
    def test_manager_owned_down_service_is_brought_up(self) -> None:
        crond_calls = 0

        def running(_sv: Path, _root: Path, service: str) -> bool:
            nonlocal crond_calls
            if service != "crond":
                return True
            crond_calls += 1
            return crond_calls > 1

        with (
            mock.patch.object(
                runtime,
                "ORIGINAL_RECONCILE_ONCE",
                return_value=healthy_topology(),
            ),
            mock.patch.object(
                runtime.base,
                "topology",
                return_value=healthy_topology(),
            ),
            mock.patch.object(runtime.base, "service_running", side_effect=running),
            mock.patch.object(
                runtime.base,
                "run_sv",
                return_value=subprocess.CompletedProcess([], 0, "ok", ""),
            ) as run_sv,
            mock.patch.object(runtime.base, "wait_for", side_effect=lambda fn, _t: fn()),
        ):
            result = runtime.reconcile_once(
                ROOT,
                SV,
                RUNSVDIR,
                LOG,
                1.0,
                2,
                table_fn=lambda: {},
            )

        run_sv.assert_called_once_with(SV, ROOT, "crond", "up", 2)
        self.assertEqual(result["running"], 7)
        self.assertEqual(result["restarted_services"], ["crond"])

    def test_failed_sv_up_fails_closed(self) -> None:
        def running(_sv: Path, _root: Path, service: str) -> bool:
            return service != "crond"

        with (
            mock.patch.object(
                runtime,
                "ORIGINAL_RECONCILE_ONCE",
                return_value=healthy_topology(),
            ),
            mock.patch.object(
                runtime.base,
                "topology",
                return_value=healthy_topology(),
            ),
            mock.patch.object(runtime.base, "service_running", side_effect=running),
            mock.patch.object(
                runtime.base,
                "run_sv",
                return_value=subprocess.CompletedProcess([], 1, "", "failed"),
            ),
        ):
            with self.assertRaisesRegex(runtime.base.GuardError, "sv_up_failed:crond"):
                runtime.reconcile_once(
                    ROOT,
                    SV,
                    RUNSVDIR,
                    LOG,
                    1.0,
                    2,
                    table_fn=lambda: {},
                )

    def test_manager_change_fails_closed(self) -> None:
        snapshots = [healthy_topology(100), healthy_topology(101)]

        with (
            mock.patch.object(
                runtime,
                "ORIGINAL_RECONCILE_ONCE",
                return_value=healthy_topology(100),
            ),
            mock.patch.object(runtime.base, "topology", side_effect=snapshots),
        ):
            with self.assertRaisesRegex(
                runtime.base.GuardError,
                "manager_changed_during_running_recovery",
            ):
                runtime.reconcile_once(
                    ROOT,
                    SV,
                    RUNSVDIR,
                    LOG,
                    1.0,
                    2,
                    table_fn=lambda: {},
                )


if __name__ == "__main__":
    unittest.main()
