from __future__ import annotations
import os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import telegram_delivery as delivery

class TelegramSplitRootTests(unittest.TestCase):
    def test_all_runtime_paths_use_mutable_root_with_read_only_code(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); code=base/"code"; mutable=base/"mutable"; code.mkdir(); mutable.mkdir()
            code.chmod(0o500)
            env={"BOTA_CODE_ROOT":str(code), "BOTA_ROOT":str(code), "BOTA_MUTABLE_ROOT":str(mutable),
                 "BOTA_ALERTS_OFFSET":"0", "BOTA_DELIVERY_STATE_DIR":str(mutable/"logs/state")}
            with mock.patch.dict(os.environ,env,clear=False):
                self.assertEqual(delivery.code_root(),code.resolve()); self.assertEqual(delivery.mutable_root(),mutable.resolve())
                state, lock=delivery.state_paths("a"*64)
                self.assertEqual(state.parent,mutable/"state/telegram_delivery"); self.assertEqual(lock.parent,state.parent)
                (mutable/"logs/state").mkdir(parents=True)
                self.assertEqual(delivery.delivery_state_dir(),(mutable/"logs/state").resolve())
            self.assertEqual(list(code.iterdir()),[])
            code.chmod(0o700)

    def test_legacy_combined_root_fallback_remains(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ,{"BOTA_ROOT":td},clear=True):
            self.assertEqual(delivery.mutable_root(),Path(td).resolve())
