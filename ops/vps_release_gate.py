#!/usr/bin/env python3
"""Offline repository/static R0-R4 gate; never asserts production readiness."""
from __future__ import annotations

import argparse
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path

EXPECTED = {
    "PAIRS": "EURUSD GBPUSD USDJPY", "TIMEFRAMES": "M15",
    "POLICY_B_ENABLED": "1", "POLICY_B_SCORE_MIN": "70", "POLICY_B_ADX_MAX": "30",
    "FILTER_SCORE_MIN": "65", "FILTER_SCORE_MIN_ALL": "65", "NEWS_ON": "0",
    "TELEGRAM_MIN_SCORE": "70", "TELEGRAM_TIER_YELLOW_MIN": "70",
    "TELEGRAM_TIER_YELLOW_MIN_INT": "70", "TELEGRAM_TIER_GREEN_MIN": "75",
    "TELEGRAM_TIER_GREEN_MIN_INT": "75", "TELEGRAM_COOLDOWN_SECONDS": "1800",
    "CANDLE_MAX_AGE_SECS": "2700",
}
SHELLS = ("tools/run_shadow_manager.sh", "tools/watcher_gated_cycle.sh",
          "tools/run_signal_watcher_with_ledger.sh", "tools/signal_watcher_pro.sh",
          "tools/signal_watcher_core.sh", "tools/telegram_send.sh",
          "tools/run_runtime_health_push.sh")
PYTHONS = ("tools/vps_orchestrator.py", "tools/runtime_dependency_check.py",
           "tools/telegram_delivery.py", "tools/telegram_send_guard.py",
           "tools/telegram_delivery_boundary.py", "tools/watcher_cycle_contract.py",
           "tools/watcher_pending_delivery_recovery.py", "tools/watcher_cycle_ledger.py",
           "tools/pipeline_ledger.py", "tools/r5_no_side_effect_preflight.py",
           "r5_bootstrap/sitecustomize.py",
           "ops/vps_deploy.py", "ops/vps_state_handoff.py", "ops/vps_release_gate.py")
LOCAL_SUITES = ("tests.test_runtime_dependency_check", "tests.test_vps_orchestrator",
                "tests.test_vps_systemd_contract", "tests.test_vps_deploy",
                "tests.test_vps_migration_release", "tests.test_watcher_cycle_contract",
                "tests.test_watcher_cycle_integration", "tests.test_telegram_commit_ordering",
                "tests.test_telegram_evidence_fail_closed", "tests.test_telegram_split_root",
                "tests.test_vps_state_handoff", "tests.test_watcher_production_split_root",
                "tests.test_r5_no_side_effect_shadow")


def env_file(path: Path) -> dict[str, str]:
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1); out[key] = value.strip("'\"")
    return out


def evaluate(root: Path) -> dict[str, object]:
    checks: dict[str, bool] = {}
    policy = env_file(root / "config/production-vps.env")
    checks["strategy_fingerprint_frozen"] = all(policy.get(k) == v for k, v in EXPECTED.items())
    orchestrator = (root / "tools/vps_orchestrator.py").read_text(encoding="utf-8")
    checks["updater_supporting_timeframes"] = '"TIMEFRAMES": "M15 H1 H4 D1"' in orchestrator
    checks["watcher_execution_m15"] = policy.get("TIMEFRAMES") == "M15"
    checks["python_314_contract"] = 'requires-python = ">=3.14,<3.15"' in (root / "pyproject.toml").read_text()
    checks["exact_dependency_manifest"] = all("==" in x for x in (root / "requirements-runtime.txt").read_text().splitlines() if x and not x.startswith("#"))
    checks["release_venv_contract"] = "release_python_unusable" in orchestrator and 'env["PATH"]' in orchestrator
    deploy = (root / "ops/vps_deploy.py").read_text(encoding="utf-8")
    checks["transactional_deploy_contract"] = all(x in deploy for x in ("os.replace", "fsync", "_rollback", '("git", "archive"'))
    unit = (root / "ops/systemd/bota.service").read_text(encoding="utf-8")
    checks["one_systemd_authority"] = "ExecStart=/opt/bota/current/.venv/bin/python" in unit and "KillMode=control-group" in unit
    runner = (root / "tools/run_signal_watcher_with_ledger.sh").read_text()
    core = (root / "tools/signal_watcher_core.sh").read_text()
    delivery = (root / "tools/telegram_delivery.py").read_text()
    checks["canonical_telegram_transport_count"] = all(x not in core for x in ("urllib.request.urlopen", "api.telegram.org", "sendPhoto")) and delivery.count("urllib.request.urlopen") == 1
    checks["telegram_mutable_root"] = "BOTA_MUTABLE_ROOT" in delivery and 'bash "${TOOLS}/telegram_send.sh"' in core
    checks["watcher_persistence_non_vacuous"] = "watcher_persistence_gate.py" not in runner and "watcher_cycle_contract.py" in runner and "os.fsync" in (root / "tools/watcher_cycle_contract.py").read_text()
    checks["dependency_evidence_durable"] = "write_evidence" in (root / "tools/runtime_dependency_check.py").read_text() and "shadow-latest.json" in (root / "tools/run_shadow_manager.sh").read_text()
    handoff = (root / "ops/vps_state_handoff.py").read_text()
    checks["state_handoff_allowlist"] = "PAUSE_LINE_RE.fullmatch" in handoff and "PAUSE_(?:EURUSD|GBPUSD|USDJPY)" in handoff
    checks["no_termux_vps_shebang"] = all(not (root / p).read_text().startswith("#!/data/data/com.termux") for p in SHELLS)
    migration_text = "\n".join((root / p).read_text(errors="replace") for p in (*SHELLS, *PYTHONS))
    checks["no_migration_secrets"] = not re.search(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b|\beyJ[A-Za-z0-9_-]{40,}\.", migration_text)
    try:
        for relative in PYTHONS: py_compile.compile(str(root / relative), doraise=True)
        checks["python_compile"] = True
    except py_compile.PyCompileError:
        checks["python_compile"] = False
    checks["shell_syntax"] = all(subprocess.run(["bash", "-n", str(root / p)], capture_output=True).returncode == 0 for p in SHELLS)
    r0 = checks["strategy_fingerprint_frozen"] and checks["updater_supporting_timeframes"] and checks["watcher_execution_m15"]
    r1 = all(checks[k] for k in ("python_compile", "shell_syntax", "no_migration_secrets", "no_termux_vps_shebang", "one_systemd_authority"))
    r2 = all(checks[k] for k in ("python_314_contract", "exact_dependency_manifest", "release_venv_contract", "transactional_deploy_contract", "dependency_evidence_durable"))
    r3 = checks["canonical_telegram_transport_count"] and checks["telegram_mutable_root"]
    r4 = checks["strategy_fingerprint_frozen"] and checks["watcher_persistence_non_vacuous"] and checks["state_handoff_allowlist"]
    passed = all((r0, r1, r2, r3, r4))
    return {"schema_version": "1.0", "R0": "PASS" if r0 else "FAIL",
            "R1": "PASS" if r1 else "FAIL", "R2": "PASS" if r2 else "FAIL",
            "R3": "PASS" if r3 else "FAIL", "R4": "PASS" if r4 else "FAIL",
            "VPS_SHELL_PYTHON_IS_RELEASE_VENV": "YES" if checks["release_venv_contract"] else "NO",
            "DEPENDENCY_PASS_EVIDENCE_DURABLE": "YES" if checks["dependency_evidence_durable"] else "NO",
            "TELEGRAM_MUTABLE_ROOT_CONTRACT": "PASS" if checks["telegram_mutable_root"] else "FAIL",
            "CANONICAL_TELEGRAM_TRANSPORT_COUNT": 1 if checks["canonical_telegram_transport_count"] else 0,
            "WATCHER_DECISION_PERSISTENCE_NON_VACUOUS": "YES" if checks["watcher_persistence_non_vacuous"] else "NO",
            "STATE_HANDOFF_CONTRACT": "PASS" if checks["state_handoff_allowlist"] else "FAIL",
            "REPOSITORY_RELEASE_GATE": "PASS" if passed else "FAIL",
            "PRODUCTION_READY": "NO", "NEXT_GATE": "R5_VPS_NO_SIDE_EFFECT_SHADOW",
            "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1]); parser.add_argument("--skip-tests", action="store_true"); args = parser.parse_args()
    root = args.root.resolve(); result = evaluate(root)
    if not args.skip_tests:
        completed = subprocess.run([sys.executable, "-m", "unittest", "-q", *LOCAL_SUITES], cwd=root,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        result["LOCAL_ACCEPTANCE_TESTS"] = "PASS" if completed.returncode == 0 else "FAIL"
        if completed.returncode != 0:
            result["REPOSITORY_RELEASE_GATE"] = "FAIL"
            result["local_test_failure_tail"] = completed.stderr[-2000:]
    else:
        result["LOCAL_ACCEPTANCE_TESTS"] = "SKIPPED"
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["REPOSITORY_RELEASE_GATE"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
