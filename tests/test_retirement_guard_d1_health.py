"""Offline acceptance coverage for credential-file guard and D1 health."""
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import test_vps_deploy as _deploy_tests
from test_vps_deploy import deploy
from test_runtime_health_hetzner_publisher import MOD, healthy_orchestrator_health

FORBIDDEN = (".env", ".env.runtime", "config/strategy.env", "strategy.env")

class CredentialGuardTests(unittest.TestCase):
    setUp = _deploy_tests.VPSDeployTests.setUp
    tearDown = _deploy_tests.VPSDeployTests.tearDown
    make = _deploy_tests.VPSDeployTests.make
    # Use the real staging/finalized validation with synthetic repo and fake systemd.
    def test_guard_rejects_all_legacy_file_paths(self):
        import subprocess
        for name in FORBIDDEN:
            with self.subTest(path=name):
                path = self.repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("SYNTHETIC=not-a-secret")
                subprocess.run(("git","add","-f",name),cwd=self.repo,check=True)
                subprocess.run(("git","commit","-qm","fixture forbidden "+name),cwd=self.repo,check=True)
                sha = subprocess.check_output(("git","rev-parse","HEAD"),cwd=self.repo,text=True).strip()
                subject, runner, systemd, _ = self.make()
                with self.assertRaisesRegex(deploy.DeployError, "forbidden_release_config"):
                    subject.stage_only(sha)
                self.assertFalse(systemd.events)
                path.unlink()
                subprocess.run(("git","add","-u"),cwd=self.repo,check=True)
                subprocess.run(("git","commit","-qm","reset fixture"),cwd=self.repo,check=True)

    def test_guard_rejects_broken_link_on_finalized_candidate(self):
        subject, _, systemd, _ = self.make()
        subject.stage_only(self.sha)
        release=self.paths.release_root / self.sha
        link=release / ".env.runtime"
        link.symlink_to("/nonexistent-retirement-fixture")
        with self.assertRaisesRegex(deploy.DeployError, "forbidden_release_config"):
            subject.stage_only(self.sha)
        self.assertFalse(systemd.events)

class D1HealthTests(unittest.TestCase):
    def test_missing_d1_visible_in_health_and_recovery(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"state").mkdir()
            (root/"cache").mkdir()
            (root/"state/vps_orchestrator_health.json").write_text(json.dumps(healthy_orchestrator_health()))
            payload=MOD.build_payload_hetzner(root)
            self.assertEqual(payload["bot_mode"], "DEGRADED")
            self.assertIn("d1_cache", payload["failure_reasons"])
            for pair in ("EURUSD","GBPUSD","USDJPY"):
                (root/"cache"/f"d1_trend_{pair}.json").write_text(json.dumps({"pair":pair,"trend":"BUY"}))
            self.assertEqual(MOD.build_payload_hetzner(root)["bot_mode"], "HEALTHY")
            (root/"cache/d1_trend_EURUSD.json").write_text('{"trend":"ANY"}')
            payload=MOD.build_payload_hetzner(root)
            self.assertEqual(payload["bot_mode"],"DEGRADED")
            self.assertIn("EURUSD",payload["failure_reasons"])

if __name__ == "__main__":
    unittest.main()
