from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vps_deploy_tests", ROOT / "ops/vps_deploy.py")
assert SPEC and SPEC.loader
deploy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = deploy
SPEC.loader.exec_module(deploy)


class FakeRunner(deploy.Runner):
    def __init__(self):
        self.commands = []

    def run(self, argv, *, cwd=None, env=None):
        self.commands.append(tuple(map(str, argv)))
        if argv[0] == "git":
            return super().run(argv, cwd=cwd, env=env)
        if tuple(argv[1:3]) == ("-m", "venv"):
            Path(argv[3], "bin").mkdir(parents=True)
            Path(argv[3], "bin/python").write_bytes(b"")
            Path(argv[3], "bin/python").chmod(0o755)
            return b""
        if argv[-1] == "--release-preflight":
            return b'{"healthy":true}'
        return b""


class FakeSystemd:
    def __init__(self, paths, *, stop_error=False, survivors=False, stale_pid=False,
                 health_overrides=None):
        self.paths = paths
        self.stop_error = stop_error
        self.survivors = survivors
        self.stale_pid = stale_pid
        self.health_overrides = health_overrides or {}
        self.active = True
        self.events = []
        self.instance = 0
        self.main_pid = 4100

    def stop(self):
        self.events.append("stop")
        if self.stop_error:
            raise deploy.DeployError("systemd_stop_failed")
        self.active = False

    def start(self):
        self.events.append("start")
        self.active = True
        self.instance += 1
        target = Path(os.readlink(self.paths.current))
        manifest = json.loads((target / deploy.MANIFEST_NAME).read_text())
        health = {"lifecycle": "RUNNING", "process_liveness": True,
                  "orchestrator_pid": self.main_pid,
                  "runtime_instance_id": f"new-{uuid.uuid4()}",
                  "release_git_sha": target.name,
                  "effective_config_fingerprint": manifest["effective_config_fingerprint"],
                  "last_loop_progress_utc": datetime.now(timezone.utc).isoformat()}
        health.update(self.health_overrides)
        path = self.paths.mutable_root / "state/vps_orchestrator_health.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(health))

    def prove_stopped(self):
        self.events.append("prove_stopped")
        if self.active:
            raise deploy.DeployError("service_not_stopped")
        if self.stale_pid:
            raise deploy.DeployError("stale_main_pid")
        if self.survivors:
            raise deploy.DeployError("service_cgroup_not_empty")

    def prove_active(self):
        self.events.append("prove_active")
        if not self.active:
            raise deploy.DeployError("service_not_active")
        return self.main_pid

    def is_active(self):
        self.events.append("is_active")
        return self.active


class VPSDeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(("git", "init", "-q", str(self.repo)), check=True)
        subprocess.run(("git", "config", "user.email", "test@example.invalid"), cwd=self.repo, check=True)
        subprocess.run(("git", "config", "user.name", "Test"), cwd=self.repo, check=True)
        for relative in ("config", "tools"):
            (self.repo / relative).mkdir()
        for relative in ("pyproject.toml", "requirements-runtime.txt", "config/production-vps.env",
                         "tools/vps_orchestrator.py"):
            source = ROOT / relative
            target = self.repo / relative
            target.write_bytes(source.read_bytes())
        (self.repo / "ordinary.txt").write_text("committed\n")
        (self.repo / "binary.bin").write_bytes(bytes(range(256)))
        executable = self.repo / "executable.sh"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        os.symlink("ordinary.txt", self.repo / "safe-link")
        subprocess.run(("git", "add", "."), cwd=self.repo, check=True)
        subprocess.run(("git", "commit", "-qm", "fixture"), cwd=self.repo, check=True)
        self.sha = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=self.repo, text=True).strip()
        self.tree = subprocess.check_output(("git", "show", "-s", "--format=%T", "HEAD"),
                                            cwd=self.repo, text=True).strip()
        self.paths = deploy.Paths(base / "releases", base / "current", base / "mutable", base / "lock")

    def tearDown(self):
        self.temp.cleanup()

    def make(self, **systemd_kwargs):
        runner = FakeRunner()
        systemd = FakeSystemd(self.paths, **systemd_kwargs)
        fsyncs = []
        subject = deploy.Deployer(self.repo, self.paths, runner=runner, systemd=systemd,
                                  activation_timeout=0.03, directory_fsync=fsyncs.append)
        return subject, runner, systemd, fsyncs

    def test_exact_sha_rejections_and_commit_tree_resolution(self):
        runner = FakeRunner()
        with self.assertRaises(deploy.DeployError):
            deploy.resolve_exact_commit(self.repo, self.sha[:8], runner)
        with self.assertRaises(deploy.CommandError):
            deploy.resolve_exact_commit(self.repo, "f" * 40, runner)
        self.assertEqual(deploy.resolve_exact_commit(self.repo, self.sha, runner),
                         (self.sha, self.tree))

    def test_binary_safe_exact_staging_modes_symlink_and_dirty_checkout(self):
        (self.repo / "ordinary.txt").write_text("dirty bytes must not deploy\n")
        subject, runner, _systemd, _fsyncs = self.make()
        result = subject.deploy(self.sha)
        release = self.paths.release_root / self.sha
        self.assertEqual((release / "ordinary.txt").read_text(), "committed\n")
        self.assertEqual((release / "binary.bin").read_bytes(), bytes(range(256)))
        self.assertEqual((release / "executable.sh").stat().st_mode & 0o777, 0o755)
        self.assertEqual((release / "ordinary.txt").stat().st_mode & 0o777, 0o644)
        self.assertTrue((release / "safe-link").is_symlink())
        self.assertEqual(os.readlink(release / "safe-link"), "ordinary.txt")
        manifest = json.loads((release / deploy.MANIFEST_NAME).read_text())
        self.assertEqual((manifest["git_commit_sha"], manifest["git_tree_sha"]),
                         (self.sha, self.tree))
        self.assertEqual(result["phase"], "COMPLETE")
        rendered = " ".join(" ".join(command) for command in runner.commands)
        self.assertIn("git archive --format=tar", rendered)
        self.assertNotIn("git show " + self.sha + ":", rendered)

    def test_restrictive_umask_still_finalizes_service_readable_release(self):
        original_umask = os.umask(0o077)
        try:
            subject, *_ = self.make()
            subject.deploy(self.sha)
        finally:
            os.umask(original_umask)
        release = self.paths.release_root / self.sha
        self.assertEqual(self.paths.release_root.parent.stat().st_mode & 0o777, 0o755)
        self.assertEqual(self.paths.release_root.stat().st_mode & 0o777, 0o755)
        self.assertEqual(release.stat().st_mode & 0o777, 0o755)
        self.assertEqual((release / deploy.MANIFEST_NAME).stat().st_mode & 0o777, 0o644)
        self.assertEqual((release / "ordinary.txt").stat().st_mode & 0o777, 0o644)
        self.assertEqual((release / "executable.sh").stat().st_mode & 0o777, 0o755)
        python = release / ".venv/bin/python"
        self.assertEqual(python.stat().st_mode & 0o111, 0o111)
        for directory in (release / ".venv", release / ".venv/bin"):
            self.assertEqual(directory.stat().st_mode & 0o111, 0o111)
        self.assertEqual(self.paths.journal.stat().st_mode & 0o777, 0o600)
        manifest = (release / deploy.MANIFEST_NAME).read_text().lower()
        for marker in ("token", "password", "secret", "api_key", "service_key"):
            self.assertNotIn(marker, manifest)

    def test_unsafe_archive_paths_and_links_are_rejected(self):
        for name, link in (("../escape", None), ("link", "../../escape")):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                member = tarfile.TarInfo(name)
                if link:
                    member.type = tarfile.SYMTYPE
                    member.linkname = link
                    archive.addfile(member)
                else:
                    member.size = 1
                    archive.addfile(member, io.BytesIO(b"x"))
            with self.assertRaises(deploy.DeployError):
                deploy.extract_archive_safely(stream.getvalue(), self.paths.release_root)

    def test_exclusive_nonblocking_lock(self):
        with deploy.DeployLock(self.paths.deploy_lock):
            with self.assertRaises(deploy.DeployLocked):
                with deploy.DeployLock(self.paths.deploy_lock):
                    pass

    def test_valid_release_reuse_and_inconsistent_release_rejected(self):
        subject, runner, _systemd, _ = self.make()
        subject.deploy(self.sha)
        archive_count = sum(command[:2] == ("git", "archive") for command in runner.commands)
        second, runner2, _systemd2, _ = self.make()
        second.deploy(self.sha)
        self.assertFalse(any(command[:2] == ("git", "archive") for command in runner2.commands))
        manifest = self.paths.release_root / self.sha / deploy.MANIFEST_NAME
        value = json.loads(manifest.read_text())
        value["git_tree_sha"] = "0" * 40
        manifest.write_text(json.dumps(value))
        third, *_ = self.make()
        with self.assertRaises(deploy.DeployError):
            third.deploy(self.sha)
        self.assertEqual(archive_count, 1)

    def test_finalized_release_reuse_is_immutable_and_modes_fail_closed(self):
        subject, *_ = self.make()
        release, _, _ = subject._stage(self.sha, self.tree)
        manifest = release / deploy.MANIFEST_NAME
        before = {path: (path.stat().st_ino, path.stat().st_mode, path.read_bytes())
                  for path in (release / "ordinary.txt", manifest)}
        chmod_paths = []
        real_chmod = os.chmod
        with mock.patch.object(deploy.os, "chmod",
                               side_effect=lambda path, mode: (chmod_paths.append(Path(path)),
                                                                real_chmod(path, mode))[1]):
            reused, _, reused_existing = subject._stage(self.sha, self.tree)
        self.assertEqual(reused, release)
        self.assertTrue(reused_existing)
        self.assertNotIn(release, chmod_paths)
        self.assertNotIn(manifest, chmod_paths)
        after = {path: (path.stat().st_ino, path.stat().st_mode, path.read_bytes())
                 for path in before}
        self.assertEqual(after, before)

        for path, mode, error in ((release, 0o750, "release_mode_invalid"),
                                  (manifest, 0o600, "manifest_mode_invalid")):
            with self.subTest(path=path):
                real_chmod(path, mode)
                with self.assertRaisesRegex(deploy.DeployError, error):
                    subject._stage(self.sha, self.tree)
                real_chmod(path, 0o755 if path == release else 0o644)

        manifest.write_text("{malformed")
        with self.assertRaisesRegex(deploy.DeployError, "invalid_json"):
            subject._stage(self.sha, self.tree)

    def test_stage_only_finalizes_without_runtime_or_current_changes(self):
        subject, _runner, systemd, _ = self.make()
        activation = mock.Mock(side_effect=AssertionError("activation must not run"))
        subject._prove_activation = activation
        result = subject.stage_only(self.sha)
        release = self.paths.release_root / self.sha
        self.assertTrue(release.is_dir())
        self.assertEqual(result, {
            "healthy": True,
            "operation": "STAGE_ONLY",
            "requested_sha": self.sha,
            "resolved_commit_sha": self.sha,
            "tree_sha": self.tree,
            "finalized_release_path": str(release),
            "effective_config_fingerprint": json.loads(
                (release / deploy.MANIFEST_NAME).read_text())["effective_config_fingerprint"],
            "reused_existing_release": False,
            "service_touched": False,
            "current_release_changed": False,
        })
        self.assertEqual(systemd.events, [])
        self.assertFalse(os.path.lexists(self.paths.current))
        activation.assert_not_called()

    def test_stage_only_reuses_valid_release_and_corruption_fails_closed(self):
        subject, *_ = self.make()
        first = subject.stage_only(self.sha)
        second, runner, systemd, _ = self.make()
        reused = second.stage_only(self.sha)
        self.assertFalse(first["reused_existing_release"])
        self.assertTrue(reused["reused_existing_release"])
        self.assertFalse(any(command[:2] == ("git", "archive") for command in runner.commands))
        self.assertEqual(systemd.events, [])
        self.assertFalse(os.path.lexists(self.paths.current))

        policy = self.paths.release_root / self.sha / "config/production-vps.env"
        policy.write_text(policy.read_text() + "\nPAIRS=CORRUPTED\n")
        corrupted, *_ = self.make()
        with self.assertRaisesRegex(deploy.DeployError, "fingerprint_"):
            corrupted.stage_only(self.sha)

    def test_stage_only_keeps_exact_sha_requirement(self):
        subject, *_ = self.make()
        with self.assertRaisesRegex(deploy.DeployError, "full_lowercase_40"):
            subject.stage_only(self.sha.upper())

    def test_stage_only_cli_emits_direct_machine_readable_evidence(self):
        evidence = {"healthy": True, "operation": "STAGE_ONLY",
                    "requested_sha": self.sha, "service_touched": False,
                    "current_release_changed": False}
        output = io.StringIO()
        with mock.patch.object(deploy.Deployer, "stage_only", return_value=evidence) as stage, \
                mock.patch("sys.stdout", output):
            self.assertEqual(deploy.main((self.sha, "--repo", str(self.repo), "--stage-only")), 0)
        self.assertEqual(json.loads(output.getvalue()), evidence)
        stage.assert_called_once_with(self.sha)

    def test_normal_deploy_still_stops_switches_starts_and_activates(self):
        subject, _runner, systemd, _ = self.make()
        real_activation = subject._prove_activation
        subject._prove_activation = mock.Mock(side_effect=real_activation)
        subject.deploy(self.sha)
        self.assertEqual(systemd.events[:4], ["is_active", "stop", "prove_stopped", "start"])
        self.assertEqual(Path(os.readlink(self.paths.current)), self.paths.release_root / self.sha)
        subject._prove_activation.assert_called_once()

    def test_pre_stop_failure_leaves_runtime_and_no_prepared_stop(self):
        subject, _runner, systemd, _ = self.make()
        subject.fault = lambda point: (_ for _ in ()).throw(RuntimeError("injected")) \
            if point == "after_staging" else None
        with self.assertRaises(RuntimeError):
            subject.deploy(self.sha)
        self.assertNotIn("stop", systemd.events)
        self.assertFalse(os.path.lexists(self.paths.current))

    def test_fault_after_prepared_journal_does_not_stop_or_switch(self):
        subject, _runner, systemd, _ = self.make()
        subject.fault = lambda point: (_ for _ in ()).throw(RuntimeError("prepared")) \
            if point == "after_journal_prepared" else None
        with self.assertRaises(RuntimeError):
            subject.deploy(self.sha)
        self.assertNotIn("stop", systemd.events)
        self.assertFalse(os.path.lexists(self.paths.current))
        self.assertEqual(json.loads(self.paths.journal.read_text())["phase"], "PREPARED")

    def test_journal_is_durable_before_stop_and_parent_fsync_exercised(self):
        subject, _runner, systemd, fsyncs = self.make()
        seen = []
        original = systemd.stop
        def stop():
            seen.append(json.loads(self.paths.journal.read_text())["phase"])
            original()
        systemd.stop = stop
        subject.deploy(self.sha)
        self.assertEqual(seen[0], "PREPARED")
        self.assertIn(self.paths.journal.parent, fsyncs)
        self.assertIn(self.paths.current.parent, fsyncs)
        self.assertIn(self.paths.release_root, fsyncs)

    def test_stop_failure_cgroup_survivor_and_stale_pid_prevent_switch(self):
        for kwargs in ({"stop_error": True}, {"survivors": True}, {"stale_pid": True}):
            with self.subTest(kwargs=kwargs):
                subject, *_ = self.make(**kwargs)
                with self.assertRaises(deploy.DeployError):
                    subject.deploy(self.sha)
                self.assertFalse(os.path.lexists(self.paths.current))
                if self.paths.journal.exists():
                    self.paths.journal.unlink()
                shutil = __import__("shutil")
                shutil.rmtree(self.paths.release_root, ignore_errors=True)

    def test_systemd_cgroup_truth_empty_nonempty_missing_and_stale_pid(self):
        class PropertyRunner:
            def __init__(self, main_pid="0", control="/system.slice/bota.service"):
                self.main_pid, self.control = main_pid, control
            def run(self, _argv, **_kwargs):
                return (f"ActiveState=inactive\nSubState=dead\nMainPID={self.main_pid}\n"
                        f"ControlGroup={self.control}\n").encode()
        root = Path(self.temp.name) / "cgroup"
        group = root / "system.slice/bota.service"
        group.mkdir(parents=True)
        procs = group / "cgroup.procs"
        procs.write_text("")
        deploy.Systemd(PropertyRunner(), root).prove_stopped()
        procs.write_text("123\n")
        with self.assertRaisesRegex(deploy.DeployError, "not_empty"):
            deploy.Systemd(PropertyRunner(), root).prove_stopped()
        procs.unlink()
        with self.assertRaisesRegex(deploy.DeployError, "unverifiable"):
            deploy.Systemd(PropertyRunner(), root).prove_stopped()
        with self.assertRaisesRegex(deploy.DeployError, "stale_main_pid"):
            deploy.Systemd(PropertyRunner(main_pid="99"), root).prove_stopped()
        __import__("shutil").rmtree(group)
        deploy.Systemd(PropertyRunner(), root).prove_stopped()

    def test_systemd_active_returns_validated_main_pid(self):
        class PropertyRunner:
            def __init__(self, main_pid="731"):
                self.main_pid = main_pid
            def run(self, _argv, **_kwargs):
                return (f"ActiveState=active\nSubState=running\nMainPID={self.main_pid}\n"
                        "ControlGroup=/system.slice/bota.service\n").encode()
        self.assertEqual(deploy.Systemd(PropertyRunner()).prove_active(), 731)
        for invalid in ("0", "-1", "not-a-pid"):
            with self.subTest(invalid=invalid), self.assertRaises(deploy.DeployError):
                deploy.Systemd(PropertyRunner(invalid)).prove_active()

    def test_systemd_runtime_state_is_authoritative_and_ambiguous_fails_closed(self):
        class PropertyRunner:
            def __init__(self, active, sub, pid):
                self.values = active, sub, pid
            def run(self, _argv, **_kwargs):
                active, sub, pid = self.values
                return (f"ActiveState={active}\nSubState={sub}\nMainPID={pid}\n"
                        "ControlGroup=/system.slice/bota.service\n").encode()
        self.assertTrue(deploy.Systemd(PropertyRunner("active", "running", "731")).is_active())
        self.assertFalse(deploy.Systemd(PropertyRunner("inactive", "dead", "0")).is_active())
        for values in (("active", "running", "0"), ("activating", "start", "731"),
                       ("inactive", "dead", "731"), ("active", "running", "bad")):
            with self.subTest(values=values), self.assertRaises(deploy.DeployError):
                deploy.Systemd(PropertyRunner(*values)).is_active()

    def test_previous_running_comes_from_systemd_not_health(self):
        first, *_ = self.make()
        first.deploy(self.sha)
        previous = self.paths.release_root / self.sha
        health_path = self.paths.mutable_root / "state/vps_orchestrator_health.json"
        health_path.unlink()
        (self.repo / "ordinary.txt").write_text("upgrade\n")
        subprocess.run(("git", "add", "ordinary.txt"), cwd=self.repo, check=True)
        subprocess.run(("git", "commit", "-qm", "upgrade"), cwd=self.repo, check=True)
        target = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=self.repo,
                                         text=True).strip()
        subject, _runner, systemd, _ = self.make()
        subject.fault = lambda point: (_ for _ in ()).throw(RuntimeError("upgrade")) \
            if point == "after_current_switch" else None
        with self.assertRaises(RuntimeError):
            subject.deploy(target)
        journal = json.loads(self.paths.journal.read_text())
        self.assertTrue(journal["previous_expected_running"])
        self.assertEqual(Path(os.readlink(self.paths.current)), previous)
        self.assertTrue(systemd.active)
        self.assertIn("start", systemd.events)

        health_path.write_text(json.dumps({"lifecycle": "STOPPED", "process_liveness": False,
                                           "runtime_instance_id": "stale-stopped"}))
        active_stale, _runner, active_systemd, _ = self.make()
        active_stale.fault = lambda point: (_ for _ in ()).throw(RuntimeError("stale")) \
            if point == "after_current_switch" else None
        with self.assertRaises(RuntimeError):
            active_stale.deploy(target)
        self.assertTrue(json.loads(self.paths.journal.read_text())["previous_expected_running"])
        self.assertTrue(active_systemd.active)

        health_path.write_text(json.dumps({"lifecycle": "RUNNING", "process_liveness": True,
                                           "runtime_instance_id": "stale"}))
        inactive, _runner, inactive_systemd, _ = self.make()
        inactive_systemd.active = False
        inactive.fault = lambda point: (_ for _ in ()).throw(RuntimeError("inactive")) \
            if point == "after_current_switch" else None
        with self.assertRaises(RuntimeError):
            inactive.deploy(target)
        journal = json.loads(self.paths.journal.read_text())
        self.assertFalse(journal["previous_expected_running"])
        self.assertFalse(inactive_systemd.active)

    def test_ambiguous_systemd_state_fails_before_stop_or_switch(self):
        subject, _runner, systemd, _ = self.make()
        systemd.is_active = lambda: (_ for _ in ()).throw(
            deploy.DeployError("service_runtime_state_ambiguous"))
        with self.assertRaisesRegex(deploy.DeployError, "runtime_state_ambiguous"):
            subject.deploy(self.sha)
        self.assertNotIn("stop", systemd.events)
        self.assertFalse(os.path.lexists(self.paths.current))

    def test_activation_retries_stale_health_pid_then_accepts_current_main_pid(self):
        subject, _runner, systemd, _ = self.make()
        subject.activation_timeout = 0.12
        now = datetime.now(timezone.utc).isoformat()
        health = {"lifecycle": "RUNNING", "process_liveness": True,
                  "runtime_instance_id": "new-instance", "release_git_sha": self.sha,
                  "effective_config_fingerprint": "f" * 64,
                  "last_loop_progress_utc": now, "orchestrator_pid": systemd.main_pid + 1}
        reads = []
        def read_health():
            reads.append(health["orchestrator_pid"])
            if len(reads) > 1:
                health["orchestrator_pid"] = systemd.main_pid
            return dict(health)
        subject._read_health_optional = read_health
        result = subject._prove_activation(self.sha, "f" * 64, "old-instance")
        self.assertGreaterEqual(len(reads), 2)
        self.assertEqual(result["orchestrator_pid"], systemd.main_pid)

    def test_activation_binds_health_to_main_pid_before_and_after(self):
        subject, _runner, systemd, _ = self.make()
        subject.activation_timeout = 0.15
        pid_a, pid_b = 4100, 4200
        calls = []
        sequence = iter((pid_a, pid_b, pid_b, pid_b))
        systemd.prove_active = lambda: (calls.append(True), next(sequence))[1]
        reads = []
        def health():
            pid = pid_a if not reads else pid_b
            reads.append(pid)
            return {"lifecycle": "RUNNING", "process_liveness": True,
                    "runtime_instance_id": f"new-{pid}", "release_git_sha": self.sha,
                    "effective_config_fingerprint": "f" * 64,
                    "last_loop_progress_utc": datetime.now(timezone.utc).isoformat(),
                    "orchestrator_pid": pid}
        subject._read_health_optional = health
        result = subject._prove_activation(self.sha, "f" * 64, "old")
        self.assertEqual(result["orchestrator_pid"], pid_b)
        self.assertEqual(len(calls), 4)

    def test_activation_persistent_main_pid_churn_times_out(self):
        subject, _runner, systemd, _ = self.make()
        counter = iter(range(5000, 6000))
        current = [0]
        def prove():
            current[0] = next(counter)
            return current[0]
        systemd.prove_active = prove
        subject._read_health_optional = lambda: {
            "lifecycle": "RUNNING", "process_liveness": True,
            "runtime_instance_id": "new", "release_git_sha": self.sha,
            "effective_config_fingerprint": "f" * 64,
            "last_loop_progress_utc": datetime.now(timezone.utc).isoformat(),
            "orchestrator_pid": current[0]}
        with self.assertRaisesRegex(deploy.DeployError, "main_pid_changed"):
            subject._prove_activation(self.sha, "f" * 64, "old")

    def test_activation_never_accepts_wrong_health_pid_despite_fresh_identity(self):
        subject, _runner, systemd, _ = self.make()
        subject._read_health_optional = lambda: {
            "lifecycle": "RUNNING", "process_liveness": True,
            "runtime_instance_id": "new-instance", "release_git_sha": self.sha,
            "effective_config_fingerprint": "f" * 64,
            "last_loop_progress_utc": datetime.now(timezone.utc).isoformat(),
            "orchestrator_pid": systemd.main_pid + 1,
        }
        with self.assertRaisesRegex(deploy.DeployError, "orchestrator_pid_mismatch"):
            subject._prove_activation(self.sha, "f" * 64, "old-instance")

    def test_activation_contract_rejects_stale_identity_release_fingerprint_and_progress(self):
        cases = ({"runtime_instance_id": "old"}, {"release_git_sha": "0" * 40},
                 {"effective_config_fingerprint": "0" * 64},
                 {"last_loop_progress_utc": "2000-01-01T00:00:00Z"})
        for override in cases:
            with self.subTest(override=override):
                subject, _runner, systemd, _ = self.make(health_overrides=override)
                old = self.paths.mutable_root / "state/vps_orchestrator_health.json"
                old.parent.mkdir(parents=True, exist_ok=True)
                old.write_text(json.dumps({"lifecycle": "RUNNING", "process_liveness": True,
                                           "runtime_instance_id": "old"}))
                with self.assertRaises(deploy.DeployError):
                    subject.deploy(self.sha)
                self.assertFalse(os.path.lexists(self.paths.current))
                self.assertEqual(json.loads(self.paths.journal.read_text())["phase"], "ROLLED_BACK")
                self.assertGreaterEqual(systemd.events.count("stop"), 2)
                __import__("shutil").rmtree(self.paths.release_root, ignore_errors=True)
                self.paths.journal.unlink()

    def test_faults_after_stop_rollback_to_first_deploy_safe_state(self):
        for boundary in ("after_service_stop", "after_current_switch", "after_service_start",
                         "before_activation_proof_completion"):
            with self.subTest(boundary=boundary):
                subject, _runner, systemd, _ = self.make()
                subject.fault = lambda point, boundary=boundary: (_ for _ in ()).throw(
                    RuntimeError(boundary)) if point == boundary else None
                with self.assertRaises(RuntimeError):
                    subject.deploy(self.sha)
                self.assertFalse(os.path.lexists(self.paths.current))
                self.assertFalse(systemd.active)
                self.assertEqual(json.loads(self.paths.journal.read_text())["phase"], "ROLLED_BACK")
                __import__("shutil").rmtree(self.paths.release_root, ignore_errors=True)
                self.paths.journal.unlink()

    def test_rollback_boundary_failure_retries_to_safe_state(self):
        subject, _runner, systemd, _ = self.make()
        def fault(point):
            if point in {"after_current_switch", "during_rollback"}:
                raise RuntimeError(point)
        subject.fault = fault
        with self.assertRaises(RuntimeError):
            subject.deploy(self.sha)
        self.assertFalse(os.path.lexists(self.paths.current))
        self.assertFalse(systemd.active)
        journal = json.loads(self.paths.journal.read_text())
        self.assertEqual(journal["phase"], "ROLLED_BACK")
        self.assertTrue(str(journal["rollback_result"]).startswith("PASS_AFTER_RETRY"))

    def test_failed_upgrade_restores_restarts_and_proves_previous_release(self):
        first, _runner, systemd, _ = self.make()
        first.deploy(self.sha)
        previous = self.paths.release_root / self.sha
        (self.repo / "ordinary.txt").write_text("second\n")
        subprocess.run(("git", "add", "ordinary.txt"), cwd=self.repo, check=True)
        subprocess.run(("git", "commit", "-qm", "second"), cwd=self.repo, check=True)
        target = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=self.repo,
                                         text=True).strip()
        second = deploy.Deployer(self.repo, self.paths, runner=FakeRunner(), systemd=systemd,
                                 activation_timeout=0.03,
                                 directory_fsync=lambda _path: None)
        second.fault = lambda point: (_ for _ in ()).throw(RuntimeError("activate")) \
            if point == "after_service_start" else None
        with self.assertRaises(RuntimeError):
            second.deploy(target)
        self.assertEqual(Path(os.readlink(self.paths.current)), previous)
        self.assertTrue(systemd.active)
        self.assertEqual(json.loads(self.paths.journal.read_text())["phase"], "ROLLED_BACK")
        self.assertTrue(previous.is_dir())

    def test_current_regular_file_is_rejected_and_previous_release_preserved(self):
        self.paths.current.write_text("unexpected")
        subject, *_ = self.make()
        with self.assertRaises(deploy.DeployError):
            subject.deploy(self.sha)
        self.assertEqual(self.paths.current.read_text(), "unexpected")
        self.assertTrue((self.paths.release_root / self.sha).is_dir())

    def test_interrupted_recovery_before_switch_after_switch_and_after_start(self):
        for phase, switched, active in (("PREPARED", False, False),
                                        ("ACTIVATING", True, False),
                                        ("ACTIVATING", True, True)):
            with self.subTest(phase=phase, switched=switched, active=active):
                subject, _runner, systemd, _ = self.make()
                final, _manifest, _reused = subject._stage(self.sha, self.tree)
                if switched:
                    subject._switch(final)
                systemd.active = active
                journal = {"schema_version": "1.0", "deployment_id": "interrupted",
                           "target_sha": self.sha, "target_tree_sha": self.tree,
                           "previous_release": None, "previous_runtime_instance_id": None,
                           "previous_expected_running": False, "phase": phase,
                           "started_at_utc": deploy.utc_now(), "updated_at_utc": deploy.utc_now(),
                           "failure": None, "rollback_result": None}
                deploy.durable_json(self.paths.journal, journal, lambda _path: None)
                with self.assertRaisesRegex(deploy.DeployError, "recovered_rerun_required"):
                    subject.deploy(self.sha)
                self.assertFalse(os.path.lexists(self.paths.current))
                self.assertFalse(systemd.active)
                recovered = json.loads(self.paths.journal.read_text())
                self.assertEqual(recovered["phase"], "RECOVERED_ROLLED_BACK")
                self.paths.journal.unlink()
                __import__("shutil").rmtree(self.paths.release_root)

    def test_source_has_no_pgrep_pgrep_authority_or_secret_fields(self):
        source = (ROOT / "ops/vps_deploy.py").read_text().lower()
        self.assertNotIn("pgrep", source)
        self.assertNotIn("text=true", source)
        release, *_ = self.make()
        release.deploy(self.sha)
        emitted = (self.paths.release_root / self.sha / deploy.MANIFEST_NAME).read_text()
        emitted += self.paths.journal.read_text()
        for marker in ("token", "password", "secret", "api_key", "service_key"):
            self.assertNotIn(marker, emitted.lower())


if __name__ == "__main__":
    unittest.main()
