from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

RELEASE = "f36836315526fd2be826e8abff1c333004b64b0c"
EXECUTOR = str(Path(__file__).resolve().parents[1] / "ops/transactional_phone_deploy.py")
CHANGED = "tools/chart_generator.py"
ADDED = "tools/chart_generator_core.py"
SECRET = "123456:OBVIOUS_FAKE_TEST_TOKEN_DO_NOT_USE"


def make_runtime(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    source = Path(__file__).resolve().parents[1]
    root = tmp_path / "BotA"
    subprocess.run(["git", "clone", "--shared", "--no-checkout", str(source), str(root)], check=True,
                   capture_output=True, text=True)
    subprocess.run(["git", "checkout", "--detach", RELEASE], cwd=root, check=True,
                   capture_output=True, text=True)
    (root / ".env.runtime").write_text(
        f"TELEGRAM_BOT_TOKEN={SECRET}\nTELEGRAM_CHAT_ID=999000\n", encoding="utf-8"
    )
    state = tmp_path / "service.state"
    state.write_text("run\n", encoding="ascii")
    log = tmp_path / "service.log"
    fake = tmp_path / "fake-sv"
    fake.write_text(
        "#!/bin/sh\n"
        "action=$1\n"
        "printf '%s\\n' \"$action\" >> \"$FAKE_SV_LOG\"\n"
        "[ \"${FAKE_SV_FAIL_ACTION:-}\" = \"$action\" ] && exit 91\n"
        "case $action in\n"
        " status) [ \"$(cat \"$FAKE_SV_STATE\")\" = run ] && { echo 'run: bota-watcher'; exit 0; }; echo 'down: bota-watcher'; exit 1;;\n"
        " down) echo down > \"$FAKE_SV_STATE\";;\n"
        " up) echo run > \"$FAKE_SV_STATE\";;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    env = os.environ.copy()
    env.update({"BOTA_ROOT": str(root), "BOTA_ALLOW_NON_TERMUX": "1", "BOTA_SV_COMMAND": str(fake),
                "FAKE_SV_STATE": str(state), "FAKE_SV_LOG": str(log),
                "BOTA_TEST_WATCHER_INSTANCE_COUNT": "1"})
    return root, env


def invoke(root: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", EXECUTOR, *args], cwd=root, env=env, text=True, capture_output=True, check=False
    )


def apply(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return invoke(root, env, "--apply", "--source-commit", RELEASE)


def assert_no_temps(root: Path) -> None:
    leftovers = [p for p in root.rglob("*") if ".deploy." in p.name or ".rollback." in p.name]
    assert leftovers == []
    assert not any(p.is_dir() for p in (root / "audits").glob("*/stage"))


def assert_no_deployment_audit(root: Path) -> None:
    assert not list((root / "audits").glob("transactional_phone_deploy_*"))


class TransactionalPhoneDeployTests(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.root, self.env = make_runtime(Path(self.temporary.name))

  def tearDown(self):
    self.temporary.cleanup()

  def test_requires_explicit_apply_before_any_mutation(self):
    root, env = self.root, self.env
    before = (root / CHANGED).read_bytes()
    result = invoke(root, env, "--source-commit", RELEASE)
    assert result.returncode != 0
    assert "APPLY_FLAG_REQUIRED" in result.stdout
    assert (root / CHANGED).read_bytes() == before
    assert_no_deployment_audit(root)


  def test_wrong_release_aborts_before_mutation(self):
    root, env = self.root, self.env
    result = invoke(root, env, "--apply", "--source-commit", "0" * 40)
    assert result.returncode != 0
    assert "SOURCE_COMMIT_NOT_ALLOWED" in result.stdout
    assert_no_deployment_audit(root)


  def test_missing_source_path_aborts_before_mutation(self):
    root, env = self.root, self.env
    env["BOTA_TEST_MISSING_SOURCE_PATH"] = ADDED
    result = apply(root, env)
    assert result.returncode != 0
    assert "SOURCE_PATH_MISSING" in result.stdout
    assert_no_deployment_audit(root)


  def test_staged_blob_mismatch_aborts(self):
    root, env = self.root, self.env
    env["BOTA_TEST_CORRUPT_STAGE_PATH"] = CHANGED
    result = apply(root, env)
    assert result.returncode != 0
    assert "STAGED_BLOB_MISMATCH" in result.stdout
    assert_no_temps(root)


  def test_success_replaces_exact_bytes_and_preserves_mutable_secret(self):
    root, env = self.root, self.env
    expected = subprocess.run(["git", "show", f"{RELEASE}:{CHANGED}"], cwd=root, check=True,
                              capture_output=True).stdout
    (root / CHANGED).write_bytes(b"old runtime bytes\n")
    secret_file = root / "state" / "provider-cache.json"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(SECRET, encoding="utf-8")
    env_file = (root / ".env.runtime").read_bytes()
    result = apply(root, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / CHANGED).read_bytes() == expected
    assert secret_file.read_text() == SECRET
    assert (root / ".env.runtime").read_bytes() == env_file
    assert SECRET not in result.stdout + result.stderr
    assert_no_temps(root)


  def test_mid_install_failure_restores_existing_and_removes_new(self):
    root, env = self.root, self.env
    old = b"previous chart\n"
    (root / CHANGED).write_bytes(old)
    (root / ADDED).unlink()
    env["BOTA_TEST_FAIL_INSTALL_AT"] = "1"
    result = apply(root, env)
    assert result.returncode != 0
    assert "ROLLBACK=PASS" in result.stdout
    assert (root / CHANGED).read_bytes() == old
    assert not (root / ADDED).exists()
    assert_no_temps(root)


  def test_service_control_failure_triggers_rollback(self):
    root, env = self.root, self.env
    old = b"previous chart\n"
    (root / CHANGED).write_bytes(old)
    env["FAKE_SV_FAIL_ACTION"] = "up"
    result = apply(root, env)
    assert result.returncode != 0
    assert "ROLLBACK=" in result.stdout
    assert (root / CHANGED).read_bytes() == old
    assert_no_temps(root)


  def test_post_deploy_verification_mismatch_rolls_back(self):
    root, env = self.root, self.env
    old = b"previous chart\n"
    (root / CHANGED).write_bytes(old)
    env["BOTA_TEST_POST_VERIFY_MISMATCH"] = "1"
    result = apply(root, env)
    assert result.returncode != 0
    assert "ROLLBACK=PASS" in result.stdout
    assert (root / CHANGED).read_bytes() == old


  def test_incomplete_journal_is_detected(self):
    root, env = self.root, self.env
    journal = root / "state/transactional_phone_deploy/active.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({"phase": "files_installed", "audit": str(root / "audits/old")}), encoding="utf-8")
    result = apply(root, env)
    assert result.returncode != 0
    assert "INCOMPLETE_JOURNAL_DETECTED" in result.stdout
    assert_no_deployment_audit(root)


  def test_already_deployed_is_idempotent_and_does_not_restart(self):
    root, env = self.root, self.env
    first = apply(root, env)
    assert first.returncode == 0, first.stdout + first.stderr
    Path(env["FAKE_SV_LOG"]).write_text("", encoding="ascii")
    result = apply(root, env)
    assert result.returncode == 0
    assert "ALREADY_CURRENT" in result.stdout
    actions = Path(env["FAKE_SV_LOG"]).read_text().splitlines()
    assert "down" not in actions
    assert "up" not in actions
    assert_no_temps(root)


  def test_manual_rollback_uses_audit_backup(self):
    root, env = self.root, self.env
    old = b"previous chart\n"
    (root / CHANGED).write_bytes(old)
    result = apply(root, env)
    assert result.returncode == 0
    audit_lines = [line for line in result.stdout.splitlines() if line.startswith("AUDIT_DIRECTORY=")]
    assert len(audit_lines) == 1
    audit = audit_lines[0].split("=", 1)[1]
    rolled = invoke(root, env, "--apply", "--rollback-audit", audit)
    assert rolled.returncode == 0
    assert "ROLLBACK=PASS" in rolled.stdout
    assert (root / CHANGED).read_bytes() == old

  def test_previously_down_service_remains_down(self):
    root, env = self.root, self.env
    Path(env["FAKE_SV_STATE"]).write_text("down\n", encoding="ascii")
    (root / CHANGED).write_bytes(b"old\n")
    result = apply(root, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert Path(env["FAKE_SV_STATE"]).read_text().strip() == "down"
    assert "up" not in Path(env["FAKE_SV_LOG"]).read_text().splitlines()


  def test_no_secret_value_in_audit_or_output(self):
    root, env = self.root, self.env
    (root / CHANGED).write_bytes(b"old\n")
    result = apply(root, env)
    assert result.returncode == 0
    assert SECRET not in result.stdout + result.stderr
    for path in (root / "audits").rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
