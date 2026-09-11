from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WRAPPER = REPO / "tools" / "m15_h1_fusion.sh"


class R5MutableRootScoringTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        code = root / "code"
        mutable = root / "mutable"
        tools = code / "tools"
        tools.mkdir(parents=True)
        (code / "config").mkdir()
        (code / "data").mkdir()
        (mutable / "cache").mkdir(parents=True)
        (mutable / "cache" / "sentinel.txt").write_text("ok", encoding="utf-8")

        legacy = tools / "m15_h1_fusion_legacy.sh"
        legacy.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "[[ -r \"${BOTA_ROOT}/cache/sentinel.txt\" ]]\n"
            "[[ \"$(readlink \"${BOTA_ROOT}/cache\")\" == \"${BOTA_MUTABLE_ROOT}/cache\" ]]\n"
            "[[ \"$(readlink \"${BOTA_ROOT}/logs\")\" == \"${BOTA_MUTABLE_ROOT}/logs\" ]]\n"
            "[[ \"$(readlink \"${BOTA_ROOT}/state\")\" == \"${BOTA_MUTABLE_ROOT}/state\" ]]\n"
            "[[ \"$(readlink \"${BOTA_ROOT}/tools\")\" == \"${BOTA_CODE_ROOT}/tools\" ]]\n"
            "[[ \"$(readlink \"${BOTA_ROOT}/config\")\" == \"${BOTA_CODE_ROOT}/config\" ]]\n"
            "printf 'RUNTIME_ROOT_OK=%s\\n' \"${BOTA_ROOT}\"\n",
            encoding="utf-8",
        )
        return code, mutable

    def test_wrapper_routes_legacy_code_and_runtime_data_to_separate_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            code, mutable = self._fixture(Path(temp))
            env = {
                **os.environ,
                "BOTA_CODE_ROOT": str(code),
                "BOTA_ROOT": str(code),
                "BOTA_MUTABLE_ROOT": str(mutable),
            }
            result = subprocess.run(
                ["bash", str(WRAPPER), "EURUSD"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"RUNTIME_ROOT_OK={mutable / 'runtime_root'}", result.stdout)

    def test_runtime_view_collision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            code, mutable = self._fixture(Path(temp))
            view = mutable / "runtime_root"
            view.mkdir(parents=True)
            (view / "cache").mkdir()
            env = {
                **os.environ,
                "BOTA_CODE_ROOT": str(code),
                "BOTA_ROOT": str(code),
                "BOTA_MUTABLE_ROOT": str(mutable),
            }
            result = subprocess.run(
                ["bash", str(WRAPPER), "EURUSD"],
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 78)
            self.assertIn("runtime view collision", result.stderr)

    def test_legacy_blob_is_preserved_as_separate_entry(self) -> None:
        legacy = REPO / "tools" / "m15_h1_fusion_legacy.sh"
        self.assertTrue(legacy.is_file())
        source = legacy.read_text(encoding="utf-8")
        self.assertIn('ROOT="${BOTA_ROOT:-$HOME/BotA}"', source)
        self.assertIn('LOGS="${ROOT}/logs"', source)


if __name__ == "__main__":
    unittest.main()
