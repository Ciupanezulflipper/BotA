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
SUPABASE_SECRET = "obvious-fake-supabase-service-key-do-not-use"


def make_runtime(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    source = Path(__file__).resolve().parents[1]
    root = tmp_path / "BotA"
    subprocess.run(["git", "clone", "--shared", "--no-checkout", str(source), str(root)], check=True,
                   capture_output=True, text=True)
    subprocess.run(["git", "checkout", "--detach", RELEASE], cwd=root, check=True,
                   capture_output=True, text=True)
    (root / ".env.runtime").write_text(
        f"TELEGRAM_BOT_TOKEN={SECRET}\nTELEGRAM_CHAT_ID=999000\n"
        f"SUPABASE_SERVICE_KEY={SUPABASE_SECRET}\n", encoding="utf-8"
    )
    state = tmp_path / "service.state"
    state.write_text("run\n", encoding="ascii")
    log = tmp_path / "service.log"
    fake = tmp_path / "fake-sv"
    fake.write_text(
        "#!/bin/sh\n"
        "action=$1\n"
        "printf '%s\\n' \"$action\" >> \"$FAKE_SV_LOG\"\n"
        "if [ \"${FAKE_SV_HANG_ACTION:-}\" = \"$action\" ] && [ ! -e \"${FAKE_SV_HANG_MARKER:-}\" ]; then\n"
        "  : > \"$FAKE_SV_HANG_MARKER\"\n"
        "  sleep 30\n"
        "fi\n"
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
        ["python3", EXECUTOR, *args], cwd=root, env=env, text=True, capture_output=True, check=False,
        timeout=15
    )


def apply(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return invoke(root, env, "--apply", "--source-commit", RELEASE)


def assert_no_temps(root: Path) -> None:
    leftovers = [p for p in root.rglob("*") if ".deploy." in p.name or ".rollback." in p.name]
    assert leftovers == []
    assert not any(p.is_dir() for p in (root / "audits").glob("*/stage"))


def assert_no_deployment_audit(root: Path) -> None:
    assert not list((root / "audits").glob("transactional_phone_deploy_*"))


def _load_executor():
    import importlib.util
    spec = importlib.util.spec_from_file_location("transactional_phone_deploy", Path(EXECUTOR))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    journal.write_text(json.dumps({"schema": 1, "phase": "files_installed", "source": RELEASE,
                                   "audit": str(root / "audits/old")}), encoding="utf-8")
    result = apply(root, env)
    assert result.returncode != 0
    assert "INCOMPLETE_JOURNAL_DETECTED" in result.stdout
    assert_no_deployment_audit(root)


  def test_complete_journal_is_reconciled_without_rollback(self):
    root, env = self.root, self.env
    first = apply(root, env)
    assert first.returncode == 0, first.stdout + first.stderr
    audit = next(line.split("=", 1)[1] for line in first.stdout.splitlines()
                 if line.startswith("AUDIT_DIRECTORY="))
    journal = root / "state/transactional_phone_deploy/active.json"
    journal.write_text(json.dumps({"schema": 1, "phase": "complete", "source": RELEASE,
                                   "audit": audit}), encoding="utf-8")
    Path(env["FAKE_SV_LOG"]).write_text("", encoding="ascii")
    result = apply(root, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not journal.exists()
    assert "ROLLBACK=" not in result.stdout
    actions = Path(env["FAKE_SV_LOG"]).read_text().splitlines()
    assert "down" not in actions
    assert "up" not in actions


  def test_backup_failure_is_audited_before_transaction_becomes_authoritative(self):
    root, env = self.root, self.env
    old = b"previous chart before failed backup\n"
    (root / CHANGED).write_bytes(old)
    env["BOTA_TEST_FAIL_BACKUP_AT"] = "0"
    result = apply(root, env)
    assert result.returncode != 0
    assert "INJECTED_BACKUP_FAILURE" in result.stdout
    assert "ROLLBACK=" not in result.stdout
    assert (root / CHANGED).read_bytes() == old
    assert Path(env["FAKE_SV_STATE"]).read_text().strip() == "run"
    actions = Path(env["FAKE_SV_LOG"]).read_text().splitlines()
    assert "down" not in actions
    assert "up" not in actions
    audit = next((root / "audits").glob("transactional_phone_deploy_*"))
    assert not (audit / "deployment.json").exists()
    evidence = json.loads((audit / "backup_failure.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "backup_failed"
    assert not (root / "state/transactional_phone_deploy/active.json").exists()


  def test_missing_supabase_service_key_fails_before_mutation_without_leaking_secrets(self):
    root, env = self.root, self.env
    config = root / ".env.runtime"
    config.write_text(f"TELEGRAM_BOT_TOKEN={SECRET}\nTELEGRAM_CHAT_ID=999000\n", encoding="utf-8")
    before = (root / CHANGED).read_bytes()
    result = apply(root, env)
    assert result.returncode != 0
    assert "REQUIRED_CREDENTIALS_MISSING" in result.stdout
    assert (root / CHANGED).read_bytes() == before
    assert not Path(env["FAKE_SV_LOG"]).exists()
    assert_no_deployment_audit(root)
    assert SECRET not in result.stdout + result.stderr


  def test_service_command_timeout_rolls_back_and_restores_service(self):
    root, env = self.root, self.env
    old = b"previous chart before service timeout\n"
    (root / CHANGED).write_bytes(old)
    env["BOTA_TEST_COMMAND_TIMEOUT_SECONDS"] = "0.2"
    env["FAKE_SV_HANG_ACTION"] = "up"
    env["FAKE_SV_HANG_MARKER"] = str(Path(self.temporary.name) / "hung-once")
    result = apply(root, env)
    assert result.returncode != 0
    assert "COMMAND_TIMEOUT:fake-sv" in result.stdout
    assert "ROLLBACK=PASS" in result.stdout
    assert (root / CHANGED).read_bytes() == old
    assert Path(env["FAKE_SV_STATE"]).read_text().strip() == "run"
    assert_no_temps(root)


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


  def test_dependency_closure_reports_pass_when_all_runtime_deps_intact(self):
    root, env = self.root, self.env
    result = apply(root, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MANIFEST_PARITY=PASS" in result.stdout
    assert "DEPENDENCY_CLOSURE=PASS" in result.stdout
    assert "RUNTIME_GENERATION=PASS" in result.stdout


  def test_missing_watcher_persistence_gate_dep_fails_closed(self):
    # The Aug-16 (Package-6) incident: watcher_persistence_gate.py is invoked
    # by the deployed run_signal_watcher_with_ledger.sh but is not part of the
    # MANIFEST. Removing it from the target must be caught before any mutation.
    root, env = self.root, self.env
    dep = root / "tools/watcher_persistence_gate.py"
    assert dep.is_file()
    dep.unlink()
    before = (root / CHANGED).read_bytes()
    result = apply(root, env)
    assert result.returncode != 0
    assert "MANIFEST_PARITY=PASS" in result.stdout
    assert "DEPENDENCY_CLOSURE=FAIL" in result.stdout
    assert "DEPENDENCY_MISSING=tools/watcher_persistence_gate.py" in result.stdout
    assert "DEPLOYMENT=PASS" not in result.stdout
    assert "RUNTIME_GENERATION=PASS" not in result.stdout
    assert (root / CHANGED).read_bytes() == before
    assert_no_deployment_audit(root)


  def test_missing_telegram_delivery_dep_fails_closed(self):
    # telegram_send_guard.py imports telegram_delivery; telegram_delivery.py is
    # not in MANIFEST. Removing it must be caught by Python-import closure.
    root, env = self.root, self.env
    dep = root / "tools/telegram_delivery.py"
    assert dep.is_file()
    dep.unlink()
    before = (root / CHANGED).read_bytes()
    result = apply(root, env)
    assert result.returncode != 0
    assert "MANIFEST_PARITY=PASS" in result.stdout
    assert "DEPENDENCY_CLOSURE=FAIL" in result.stdout
    assert "DEPENDENCY_MISSING=tools/telegram_delivery.py" in result.stdout
    assert "DEPLOYMENT=PASS" not in result.stdout
    assert (root / CHANGED).read_bytes() == before
    assert_no_deployment_audit(root)


  def test_stale_dependency_on_disk_fails_closed(self):
    # Even if the required dep file exists, if its content differs from the
    # pinned RELEASE blob the runtime generation is mixed and must fail closed.
    root, env = self.root, self.env
    dep = root / "tools/watcher_cycle_ledger.py"
    assert dep.is_file()
    dep.write_text("# stale generation, not the pinned RELEASE\n", encoding="utf-8")
    before = (root / CHANGED).read_bytes()
    result = apply(root, env)
    assert result.returncode != 0
    assert "MANIFEST_PARITY=PASS" in result.stdout
    assert "DEPENDENCY_CLOSURE=FAIL" in result.stdout
    assert "DEPENDENCY_STALE=tools/watcher_cycle_ledger.py" in result.stdout
    assert "DEPLOYMENT=PASS" not in result.stdout
    assert (root / CHANGED).read_bytes() == before
    assert_no_deployment_audit(root)


  def test_dependency_discovery_covers_persistence_gate_and_telegram_delivery(self):
    # Unit-level check that the bounded parser actually surfaces the two
    # dependencies whose absence caused the Aug-16 (Package-6) false-green.
    # Import inline so that this file can also be executed standalone.
    module = _load_executor()
    root, _ = self.root, self.env
    deps = module.discover_runtime_dependencies(root, RELEASE)
    assert "tools/watcher_persistence_gate.py" in deps
    assert "tools/telegram_delivery.py" in deps
    # And the historically stale-observed files must also be classified as deps
    # so that generation mismatches on them are caught.
    assert "tools/watcher_cycle_ledger.py" in deps
    assert "tools/pipeline_ledger.py" in deps
    # Embedded python heredoc dep in signal_watcher_core.sh.
    assert "tools/news_filter_real.py" in deps
    # Manifest members are never re-reported as separate dependencies.
    assert not (deps & set([
      "tools/chart_generator.py",
      "tools/chart_generator_core.py",
      "tools/signal_watcher_pro.sh",
      "tools/telegram_send_guard.py",
      "tools/telegram_send.sh",
    ]))


  def test_dependency_discovery_reaches_transitive_fixed_point(self):
    # The RELEASE has real second-level dependencies that only appear because
    # a first-level dependency imports them (not the MANIFEST). A single-pass
    # scan would miss all of these -- their presence in the closure is proof
    # the recursion runs to fixed point.
    module = _load_executor()
    deps = module.discover_runtime_dependencies(self.root, RELEASE)
    # Second-level: reached only via calendar_guard.py / news_filter_real.py /
    # scoring_engine.sh imports of `trusted_time`.
    assert "tools/trusted_time.py" in deps
    # Second-level: reached only via m15_h1_fusion.sh (a first-level shell dep
    # invoked from signal_watcher_core.sh).
    assert "tools/emit_snapshot.py" in deps
    assert "tools/news_sentiment.py" in deps
    assert "tools/production_signal_policy.py" in deps
    # Second-level: reached only via scoring_engine.sh (first-level shell dep).
    assert "tools/market_open.sh" in deps
    assert "tools/sr_score.py" in deps


  def test_transitive_closure_recurses_through_A_B_C_chain(self):
    # Controlled A -> B -> C chain. Only A is in the entry set; B is
    # discoverable only from A; C is discoverable only from B. A single-pass
    # scan would find only {B}. A fixed-point closure must yield {A, B, C}.
    module = _load_executor()
    modules = {"a_mod", "b_mod", "c_mod"}
    texts = {
        "tools/a_mod.py": "from b_mod import go\n",
        "tools/b_mod.py": "from c_mod import here\n",
        "tools/c_mod.py": "# leaf module\n",
    }
    def resolve(path):
        return texts.get(path)
    closure = module._transitive_closure({"tools/a_mod.py"}, modules, resolve)
    assert closure == {"tools/a_mod.py", "tools/b_mod.py", "tools/c_mod.py"}


  def test_transitive_closure_terminates_on_cycles(self):
    # A dependency cycle (A -> B -> A) must not loop forever.
    module = _load_executor()
    modules = {"a_mod", "b_mod"}
    texts = {
        "tools/a_mod.py": "from b_mod import x\n",
        "tools/b_mod.py": "from a_mod import y\n",
    }
    def resolve(path):
        return texts.get(path)
    closure = module._transitive_closure({"tools/a_mod.py"}, modules, resolve)
    assert closure == {"tools/a_mod.py", "tools/b_mod.py"}


  def test_transitive_chain_missing_C_fails_before_mutation(self):
    # Real end-to-end proof that a second-level dependency is discovered and
    # then gated: trusted_time.py is only reachable via calendar_guard.py /
    # news_filter_real.py / scoring_engine.sh, none of which are in MANIFEST.
    # Removing trusted_time.py must be caught, and the failure must occur
    # before any deployment mutation begins.
    root, env = self.root, self.env
    a_path = root / "tools/calendar_guard.py"
    b_path = root / "tools/news_filter_real.py"
    c_path = root / "tools/trusted_time.py"
    assert a_path.is_file(), "A (calendar_guard.py) must exist at RELEASE"
    assert b_path.is_file(), "B (news_filter_real.py) must exist at RELEASE"
    assert c_path.is_file(), "C (trusted_time.py) must exist at RELEASE"
    c_path.unlink()
    before = (root / CHANGED).read_bytes()
    log_before = Path(env["FAKE_SV_LOG"]).read_text() if Path(env["FAKE_SV_LOG"]).exists() else ""
    result = apply(root, env)
    assert result.returncode != 0
    assert "MANIFEST_PARITY=PASS" in result.stdout
    assert "DEPENDENCY_CLOSURE=FAIL" in result.stdout
    assert "DEPENDENCY_MISSING=tools/trusted_time.py" in result.stdout
    assert "DEPLOYMENT=PASS" not in result.stdout
    assert "RUNTIME_GENERATION=PASS" not in result.stdout
    # Pre-mutation ordering: no service quiesce, no generation marker, no audit.
    log_after = Path(env["FAKE_SV_LOG"]).read_text() if Path(env["FAKE_SV_LOG"]).exists() else ""
    new_actions = [l for l in log_after[len(log_before):].splitlines() if l.strip()]
    assert "down" not in new_actions, f"service was quiesced pre-check: {new_actions}"
    assert "up" not in new_actions
    assert not (root / "state/transactional_phone_deploy/runtime_deploy_in_progress.json").exists()
    assert (root / CHANGED).read_bytes() == before
    assert_no_deployment_audit(root)


  def test_transitive_chain_stale_C_fails_before_mutation(self):
    # Same A -> B -> C chain, but C exists with wrong content. Content drift
    # against the pinned RELEASE blob must be caught pre-mutation.
    root, env = self.root, self.env
    c_path = root / "tools/trusted_time.py"
    assert c_path.is_file()
    c_path.write_text("# not the pinned RELEASE content\n", encoding="utf-8")
    before = (root / CHANGED).read_bytes()
    result = apply(root, env)
    assert result.returncode != 0
    assert "MANIFEST_PARITY=PASS" in result.stdout
    assert "DEPENDENCY_CLOSURE=FAIL" in result.stdout
    assert "DEPENDENCY_STALE=tools/trusted_time.py" in result.stdout
    assert "DEPLOYMENT=PASS" not in result.stdout
    assert "RUNTIME_GENERATION=PASS" not in result.stdout
    assert (root / CHANGED).read_bytes() == before
    assert_no_deployment_audit(root)


  def test_no_secret_value_in_audit_or_output(self):
    root, env = self.root, self.env
    (root / CHANGED).write_bytes(b"old\n")
    result = apply(root, env)
    assert result.returncode == 0
    assert SECRET not in result.stdout + result.stderr
    assert SUPABASE_SECRET not in result.stdout + result.stderr
    for path in (root / "audits").rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
            assert SUPABASE_SECRET.encode() not in path.read_bytes()
