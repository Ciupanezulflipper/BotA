from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    path = HERE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"missing loader for {relative}")
    spec.loader.exec_module(module)
    return module


deploy = load_module("phone_deploy_observability_locking", "ops/phone_deploy_observability.py")


class DeploymentLockTests(unittest.TestCase):
    def test_second_transaction_cannot_acquire_same_root_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with deploy.deployment_lock(root):
                with self.assertRaises(deploy.DeployError) as caught:
                    with deploy.deployment_lock(root):
                        pass
            self.assertIn("another_runtime_deployment_is_active", str(caught.exception))

    def test_lock_releases_after_context_exit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with deploy.deployment_lock(root):
                pass
            with deploy.deployment_lock(root):
                pass


class StagedCheckerTests(unittest.TestCase):
    def test_staged_checker_must_match_metadata_blob(self):
        with tempfile.TemporaryDirectory() as td:
            backup = Path(td)
            checker = backup / "stage" / "tools" / "control_plane_status.py"
            checker.parent.mkdir(parents=True)
            data = b"print('{}')\n"
            checker.write_bytes(data)
            metadata = {
                "expected_blobs": {
                    "tools/control_plane_status.py": deploy.git_blob_sha(data),
                }
            }
            self.assertEqual(
                deploy.validated_staged_checker(backup, metadata),
                checker,
            )
            checker.write_text("print('tampered')\n", encoding="utf-8")
            with self.assertRaises(deploy.DeployError):
                deploy.validated_staged_checker(backup, metadata)

    def test_missing_expected_checker_blob_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            backup = Path(td)
            checker = backup / "stage" / "tools" / "control_plane_status.py"
            checker.parent.mkdir(parents=True)
            checker.write_text("print('{}')\n", encoding="utf-8")
            with self.assertRaises(deploy.DeployError):
                deploy.validated_staged_checker(backup, {"expected_blobs": {}})


if __name__ == "__main__":
    unittest.main()
