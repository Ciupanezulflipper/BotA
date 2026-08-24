from __future__ import annotations

import tempfile
import unittest
from importlib import metadata
from pathlib import Path
from unittest import mock

from tools import runtime_dependency_check as dependency_check


class ManifestTests(unittest.TestCase):
    def test_repository_manifest_exactly_pins_requests(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pins = dependency_check.parse_manifest(root / "requirements-runtime.txt")
        self.assertEqual(
            pins,
            [
                ("requests", "2.34.2"),
                ("matplotlib", "3.11.1"),
                ("numpy", "2.5.1"),
                ("pandas", "3.0.5"),
            ],
        )

    def test_manifest_rejects_unpinned_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "requirements-runtime.txt"
            manifest.write_text("requests>=2\n", encoding="utf-8")
            with self.assertRaisesRegex(
                dependency_check.DependencyContractError,
                "manifest_not_exact_pin",
            ):
                dependency_check.parse_manifest(manifest)

    def test_manifest_rejects_duplicate_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "requirements-runtime.txt"
            manifest.write_text(
                "requests==2.34.2\nRequests==2.34.2\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                dependency_check.DependencyContractError,
                "manifest_duplicate:requests",
            ):
                dependency_check.parse_manifest(manifest)


class DependencyTests(unittest.TestCase):
    def test_exact_version_and_import_pass(self) -> None:
        with (
            mock.patch.object(
                dependency_check.metadata,
                "version",
                return_value="2.34.2",
            ),
            mock.patch.object(
                dependency_check.importlib,
                "import_module",
                return_value=object(),
            ),
        ):
            result = dependency_check.dependency_result("requests", "2.34.2")
        self.assertTrue(result["healthy"])
        self.assertEqual(result["failure_reasons"], [])

    def test_missing_distribution_fails(self) -> None:
        with (
            mock.patch.object(
                dependency_check.metadata,
                "version",
                side_effect=metadata.PackageNotFoundError("requests"),
            ),
            mock.patch.object(
                dependency_check.importlib,
                "import_module",
                side_effect=ModuleNotFoundError("No module named 'requests'"),
            ),
        ):
            result = dependency_check.dependency_result("requests", "2.34.2")
        self.assertFalse(result["healthy"])
        self.assertIn("missing_distribution:requests", result["failure_reasons"])
        self.assertTrue(
            any(reason.startswith("import_failed:requests:ModuleNotFoundError") for reason in result["failure_reasons"])
        )

    def test_wrong_version_fails_even_when_importable(self) -> None:
        with (
            mock.patch.object(
                dependency_check.metadata,
                "version",
                return_value="2.33.0",
            ),
            mock.patch.object(
                dependency_check.importlib,
                "import_module",
                return_value=object(),
            ),
        ):
            result = dependency_check.dependency_result("requests", "2.34.2")
        self.assertFalse(result["healthy"])
        self.assertIn(
            "version_mismatch:requests:installed=2.33.0:required=2.34.2",
            result["failure_reasons"],
        )

    def test_import_failure_blocks_even_if_distribution_version_matches(self) -> None:
        with (
            mock.patch.object(
                dependency_check.metadata,
                "version",
                return_value="2.34.2",
            ),
            mock.patch.object(
                dependency_check.importlib,
                "import_module",
                side_effect=ImportError("transitive import failure"),
            ),
        ):
            result = dependency_check.dependency_result("requests", "2.34.2")
        self.assertFalse(result["healthy"])
        self.assertTrue(
            any(reason.startswith("import_failed:requests:ImportError") for reason in result["failure_reasons"])
        )


class ShadowRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.script = (root / "tools/run_shadow_manager.sh").read_text(encoding="utf-8")

    def test_dependency_preflight_runs_before_shadow_manager(self) -> None:
        checker_position = self.script.index('python3 "${DEPENDENCY_CHECK}"')
        manager_position = self.script.index('python3 "${TOOLS}/be_shadow_manager.py"')
        self.assertLess(checker_position, manager_position)

    def test_prelogger_stderr_has_durable_destination(self) -> None:
        self.assertIn('RUNTIME_ERR_LOG="${LOGS}/shadow_runtime.stderr.log"', self.script)
        self.assertIn('2>>"${RUNTIME_ERR_LOG}"', self.script)

    def test_dependency_failure_is_persisted_and_ledgered(self) -> None:
        self.assertIn('runtime_error "dependency_check_failed rc=${rc}"', self.script)
        self.assertIn('ledger failed "dependency_check_exit_code=${rc}"', self.script)


if __name__ == "__main__":
    unittest.main()
