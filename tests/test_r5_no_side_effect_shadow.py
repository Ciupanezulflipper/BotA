from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "r5_bootstrap" / "sitecustomize.py"
PREFLIGHT = ROOT / "tools" / "r5_no_side_effect_preflight.py"
HEALTH_WRAPPER = ROOT / "tools" / "run_runtime_health_push.sh"
SENTINEL = "R5_SHADOW_NO_NETWORK"


def _base_env(mutable: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "BOTA_R5_SHADOW": "1",
        "BOTA_REQUIRE_R5_SHADOW": "1",
        "BOTA_CODE_ROOT": str(ROOT),
        "BOTA_ROOT": str(ROOT),
        "BOTA_MUTABLE_ROOT": str(mutable),
        "PYTHONPATH": str(ROOT / "r5_bootstrap"),
    })
    for key in (
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "BOT_TOKEN",
        "TELEGRAM_CHAT_ID", "CHAT_ID", "TG_CHAT_ID",
        "SUPABASE_SERVICE_KEY", "BOTA_HEALTH_INGEST_SECRET",
    ):
        env[key] = SENTINEL
    return env


class R5NoSideEffectShadowTests(unittest.TestCase):
    def test_fresh_interpreter_auto_loads_exact_bootstrap_before_user_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = _base_env(Path(temporary))
            code = (
                "import os,pathlib,sys;"
                "assert os.environ['BOTA_R5_BOOTSTRAP_ACTIVE']=='1';"
                f"assert pathlib.Path(sys.modules['sitecustomize'].__file__).resolve()==pathlib.Path({str(BOOTSTRAP)!r}).resolve()"
            )
            completed = subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT,
                                       text=True, capture_output=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_active_bootstrap_suppresses_known_transports_and_records_sanitized_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            mutable = Path(temporary)
            env = _base_env(mutable)
            code = (
                "import http.client,json,socket,urllib.request,os;"
                "r=urllib.request.Request('https://api.telegram.org/botSECRET_DO_NOT_LOG/sendMessage',data=b'x',method='POST');"
                "u=urllib.request.urlopen(r,timeout=1);"
                "assert json.loads(u.read())['result']['message_id']==-1;"
                "c=http.client.HTTPSConnection('unit.supabase.co',timeout=1);c.request('GET','/rest/v1/signals');"
                "assert c.getresponse().read()==b'[]';"
                "exec(\"try:\\n socket.getaddrinfo(\'api.telegram.org\',443)\\n raise AssertionError(\'dns_not_blocked\')\\nexcept socket.gaierror:\\n pass\");"
                "assert os.environ['BOTA_R5_BOOTSTRAP_ACTIVE']=='1';"
                "print('R5_TRANSPORT_TEST=PASS')"
            )
            completed = subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT,
                                       text=True, capture_output=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("R5_TRANSPORT_TEST=PASS", completed.stdout)
            ledger = (mutable / "state" / "r5_side_effects.jsonl").read_text(encoding="utf-8")
            self.assertIn('"host_category":"telegram"', ledger)
            self.assertIn('"host_category":"supabase"', ledger)
            self.assertIn('"transport":"socket"', ledger)
            self.assertNotIn("SECRET_DO_NOT_LOG", ledger)
            self.assertNotIn(SENTINEL, ledger)

    def test_secret_is_detected_then_replaced_without_printing_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = _base_env(Path(temporary))
            secret = "dont-print-me-production-secret"
            env["SUPABASE_SERVICE_KEY"] = secret
            code = (
                "import os;"
                "print(os.environ['BOTA_R5_PRODUCTION_SECRET_PRESENT']);"
                "print(os.environ['BOTA_R5_REJECTED_SECRET_KEYS']);"
                "print(os.environ['SUPABASE_SERVICE_KEY'])"
            )
            completed = subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT,
                                       text=True, capture_output=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn(secret, completed.stdout + completed.stderr)
            lines = completed.stdout.splitlines()
            self.assertEqual(lines[0], "1")
            self.assertIn("SUPABASE_SERVICE_KEY", lines[1])
            self.assertEqual(lines[2], SENTINEL)

    def test_preflight_passes_only_after_exact_bootstrap_is_loaded(self):
        with tempfile.TemporaryDirectory() as temporary:
            mutable = Path(temporary)
            env = _base_env(mutable)
            completed = subprocess.run([sys.executable, str(PREFLIGHT)], env=env, cwd=ROOT,
                                       text=True, capture_output=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout.strip().splitlines()[-1])
            self.assertTrue(result["healthy"])
            self.assertTrue(result["r5_shadow"])
            self.assertFalse(result["side_effects_enabled"])
            self.assertTrue(result["checks"]["bootstrap_module_exact"])
            self.assertTrue(result["checks"]["suppression_ledger_grew"])

    def test_preflight_fails_when_r5_is_required_but_bootstrap_is_not_active(self):
        for shadow in (None, "0"):
            with self.subTest(shadow=shadow):
                env = dict(os.environ)
                if shadow is None:
                    env.pop("BOTA_R5_SHADOW", None)
                else:
                    env["BOTA_R5_SHADOW"] = shadow
                env["BOTA_REQUIRE_R5_SHADOW"] = "1"
                completed = subprocess.run([sys.executable, str(PREFLIGHT)], env=env, cwd=ROOT,
                                           text=True, capture_output=True, timeout=10)
                self.assertEqual(completed.returncode, 2)
                result = json.loads(completed.stdout.strip())
                self.assertFalse(result["healthy"])
                self.assertEqual(result["checks"]["failure"], "r5_shadow_required_but_inactive")

    def test_r5_active_with_missing_or_wrong_bootstrap_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            wrong = temporary_path / "wrong"
            wrong.mkdir()
            (wrong / "sitecustomize.py").write_text(
                "import os\nos.environ['BOTA_R5_BOOTSTRAP_ACTIVE']='1'\n",
                encoding="utf-8",
            )
            for bootstrap_path in (temporary_path / "missing", wrong):
                with self.subTest(bootstrap_path=bootstrap_path):
                    env = _base_env(temporary_path)
                    env["PYTHONPATH"] = str(bootstrap_path)
                    completed = subprocess.run([sys.executable, str(PREFLIGHT)], env=env, cwd=ROOT,
                                               text=True, capture_output=True, timeout=10)
                    self.assertEqual(completed.returncode, 2)
                    result = json.loads(completed.stdout.strip())
                    self.assertEqual(result["checks"]["failure"], "r5_bootstrap_not_proven")

    def test_non_r5_auto_load_is_inert(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = _base_env(Path(temporary))
            env.pop("BOTA_R5_SHADOW")
            env.pop("BOTA_REQUIRE_R5_SHADOW")
            env["TELEGRAM_BOT_TOKEN"] = "unchanged-non-r5-value"
            code = (
                "import os,pathlib,sys;"
                f"assert pathlib.Path(sys.modules['sitecustomize'].__file__).resolve()==pathlib.Path({str(BOOTSTRAP)!r}).resolve();"
                "assert 'BOTA_R5_BOOTSTRAP_ACTIVE' not in os.environ;"
                "assert os.environ.get('TELEGRAM_BOT_TOKEN')=='unchanged-non-r5-value'"
            )
            completed = subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT,
                                       text=True, capture_output=True, timeout=10)
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_runtime_health_r5_branch_precedes_secret_file_loading(self):
        text = HEALTH_WRAPPER.read_text(encoding="utf-8")
        marker = 'RESULT=R5_SHADOW_LOCAL_ONLY rc=$rc'
        secret_guard = 'if [ ! -f "$SECRET_FILE" ]; then'
        source_secret = '. "$SECRET_FILE"'
        self.assertIn(marker, text)
        self.assertLess(text.index(marker), text.index(secret_guard))
        self.assertLess(text.index(marker), text.index(source_secret))


if __name__ == "__main__":
    unittest.main()
