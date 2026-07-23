from pathlib import Path
import unittest

from tools.runsvdir_guard import manager_pids, runsv_rows, topology


ROOT = Path("/data/data/com.termux/files/usr/var/service")


def row(exe: str, *argv: str, ppid: int) -> dict:
    return {"ppid": ppid, "argv": [exe, *argv]}


class TopologyTests(unittest.TestCase):
    def test_exact_manager_and_owned_services(self) -> None:
        table = {
            100: row("runsvdir", "-P", str(ROOT), ppid=1),
            201: row("runsv", "bota-updater", ppid=100),
            202: row("runsv", "bota-watcher", ppid=100),
            203: row("runsv", "bota-closer", ppid=100),
            204: row("runsv", "bota-shadow", ppid=100),
            205: row("runsv", "bota-heartbeat", ppid=100),
            206: row("runsv", "bota-supervisor", ppid=100),
            207: row("runsv", "crond", ppid=100),
        }
        result = topology(table, ROOT)
        self.assertEqual(result["manager_count"], 1)
        self.assertEqual(result["owned"], 7)
        self.assertEqual(result["orphaned"], 0)
        self.assertEqual(result["invalid"], 0)

    def test_manager_loss_classifies_all_orphans(self) -> None:
        table = {
            201: row("runsv", "bota-updater", ppid=1),
            202: row("runsv", "bota-watcher", ppid=1),
            203: row("runsv", "bota-closer", ppid=1),
            204: row("runsv", "bota-shadow", ppid=1),
            205: row("runsv", "bota-heartbeat", ppid=1),
            206: row("runsv", "bota-supervisor", ppid=1),
            207: row("runsv", "crond", ppid=1),
        }
        result = topology(table, ROOT)
        self.assertEqual(result["manager_count"], 0)
        self.assertEqual(result["owned"], 0)
        self.assertEqual(result["orphaned"], 7)

    def test_mixed_topology_is_explicit(self) -> None:
        table = {
            100: row("runsvdir", str(ROOT), ppid=1),
            201: row("runsv", "bota-updater", ppid=100),
            202: row("runsv", "bota-watcher", ppid=1),
        }
        result = topology(
            table,
            ROOT,
            services=("bota-updater", "bota-watcher"),
        )
        self.assertEqual(result["owned"], 1)
        self.assertEqual(result["orphaned"], 1)

    def test_manager_match_requires_service_root(self) -> None:
        table = {
            100: row("runsvdir", "/tmp/other-services", ppid=1),
            101: row("runsvdir", "-P", str(ROOT), ppid=1),
        }
        self.assertEqual(manager_pids(table, ROOT), [101])

    def test_runsv_match_is_exact_service_name(self) -> None:
        table = {
            200: row("runsv", "bota-watcher", ppid=1),
            201: row("runsv", "bota-watcher-old", ppid=1),
        }
        self.assertEqual(
            [pid for pid, _ in runsv_rows(table, "bota-watcher")],
            [200],
        )


if __name__ == "__main__":
    unittest.main()
