#!/usr/bin/env python3
"""Transactional BotA weekend production deployment for Termux.

This deployer is intentionally self-contained so the phone only needs one
reviewed command. It downloads a pinned runtime dependency closure from the
reviewed production merge, verifies Git blob identities before mutation, backs
up every replaced file and the current crontab, deploys atomically, installs the
canonical BotA cron block while preserving all non-BotA cron content, and runs
bounded readiness checks.

It never reads or prints secret values. Historical replay datasets/results are
not touched. Telegram is never invoked by deployment validation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_COMMIT = "588624cba9eb905ca2c4c3fb46303eb692e6ea61"
REPOSITORY = "Ciupanezulflipper/BotA"
PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
TIMEFRAMES = ("M15", "H1", "H4", "D1")
BOTA_BEGIN = "# BotA runtime BEGIN"
BOTA_END = "# BotA runtime END"
BLOB_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class DeployFile:
    path: str
    blob: str
    mode: int


FILES = (
    DeployFile("tools/signal_watcher_pro.sh", "16d4651275cda3c5906554c64f083f22703b6b3a", 0o755),
    DeployFile("tools/scoring_engine.sh", "09c42362a5c3c679696e86d4131ce5dfabd86608", 0o755),
    DeployFile("tools/quality_filter.py", "18b76f908652d483c115c930373972836cea81dc", 0o755),
    DeployFile("tools/indicators_updater.sh", "a61905d398398fbabf7db015c3c2916f9a2d80d4", 0o755),
    DeployFile("tools/data_fetch_candles.sh", "3e689623382f52bd756c1d8e4f2c1147a865ef16", 0o755),
    DeployFile("tools/build_indicators.py", "2abce4a325d6d9da8bb0958b97a651d4288e1792", 0o755),
    DeployFile("tools/sr_score.py", "616b996a8ce439a19483762645a2247ca96fd066", 0o755),
    DeployFile("tools/market_open.sh", "a73ca97f3a63c3245311585e231e5e69eaffc506", 0o755),
    DeployFile("tools/emit_snapshot.py", "425c9adace57956981cf7e3111fd5df504c4f1ca", 0o755),
    DeployFile("tools/m15_h1_fusion.sh", "a177541aa8dc9e193ce6f057dab02886c24a4f40", 0o755),
    DeployFile("tools/production_signal_policy.py", "1683204657e64e7242269cfdff846bcc796cafaf", 0o755),
    DeployFile("tools/sync_d1_trend_cache.py", "8b930a7009cb3e6edfe6af5ef48632ec1160f8f3", 0o755),
    DeployFile("ops/bota_crontab.canonical", "987a3b9e0879a4f4045e4257bf8be8f8c5e64cd2", 0o644),
)


class DeploymentError(RuntimeError):
    """Raised when an integrity or transactional deployment gate fails."""


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _run(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 60,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _git_blob(path: Path, root: Path) -> str:
    completed = _run(
        ["git", "hash-object", "--no-filters", str(path)],
        cwd=root,
        timeout=15,
    )
    if completed.returncode != 0:
        raise DeploymentError(f"git hash-object failed for {path.name}")
    value = completed.stdout.strip()
    if not BLOB_RE.fullmatch(value):
        raise DeploymentError(f"invalid Git blob output for {path.name}")
    return value


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BotA-reviewed-production-deployer"},
        method="GET",
    )
    last_error = ""
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise DeploymentError(f"HTTP {response.status}")
                payload = response.read()
            if not payload:
                raise DeploymentError("empty response")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            return
        except (OSError, urllib.error.URLError, DeploymentError) as exc:
            last_error = type(exc).__name__
            if attempt < 4:
                time.sleep(attempt)
    raise DeploymentError(f"download failed: {destination.name}:{last_error}")


def _validate_manifest() -> None:
    if len(FILES) != 13:
        raise DeploymentError("runtime manifest count changed")
    paths = [item.path for item in FILES]
    if len(paths) != len(set(paths)):
        raise DeploymentError("runtime manifest contains duplicate paths")
    for item in FILES:
        if item.path.startswith("/") or ".." in Path(item.path).parts:
            raise DeploymentError(f"unsafe manifest path: {item.path}")
        if not BLOB_RE.fullmatch(item.blob):
            raise DeploymentError(f"invalid manifest blob: {item.path}")


def _required_commands() -> tuple[str, ...]:
    return ("bash", "crontab", "git", "python3", "timeout")


def _validate_commands() -> None:
    missing = [name for name in _required_commands() if shutil.which(name) is None]
    if missing:
        raise DeploymentError("missing commands: " + ",".join(missing))


def _download_and_verify(stage: Path, root: Path) -> None:
    base = f"https://raw.githubusercontent.com/{REPOSITORY}/{SOURCE_COMMIT}"
    for item in FILES:
        destination = stage / item.path
        _download(f"{base}/{item.path}", destination)
        actual = _git_blob(destination, root)
        print(f"SOURCE_BLOB={item.path}|expected={item.blob}|actual={actual}")
        if actual != item.blob:
            raise DeploymentError(f"source blob mismatch: {item.path}")


def _preflight_syntax(stage: Path) -> None:
    shell_files = [item for item in FILES if item.path.endswith(".sh")]
    python_files = [item for item in FILES if item.path.endswith(".py")]
    for item in shell_files:
        completed = _run(["bash", "-n", str(stage / item.path)], timeout=15)
        if completed.returncode != 0:
            raise DeploymentError(f"bash syntax failed: {item.path}")
    for item in python_files:
        completed = _run(
            ["python3", "-m", "py_compile", str(stage / item.path)],
            timeout=20,
        )
        if completed.returncode != 0:
            raise DeploymentError(f"python compile failed: {item.path}")

    cron = (stage / "ops/bota_crontab.canonical").read_text(encoding="utf-8")
    required = (
        'PAIRS="EURUSD GBPUSD USDJPY"',
        "POLICY_B_ENABLED=1",
        "POLICY_B_SCORE_MIN=70",
        "POLICY_B_ADX_MAX=30",
        "NEWS_ON=0",
        "sync_d1_trend_cache.py",
    )
    missing = [token for token in required if token not in cron]
    if missing:
        raise DeploymentError("canonical cron missing: " + ",".join(missing))


def _load_module(path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("bota_deploy_policy", path)
    if spec is None or spec.loader is None:
        raise DeploymentError("cannot load staged production policy")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _policy_probes(policy_path: Path) -> None:
    module = _load_module(policy_path)
    prior = {
        key: os.environ.get(key)
        for key in (
            "POLICY_B_ENABLED",
            "POLICY_B_SCORE_MIN",
            "POLICY_B_ADX_MAX",
            "SCALP_SL_ATR_MULT",
            "SCALP_TP_ATR_MULT",
            "MAX_SL_PIPS",
            "MAX_TP_PIPS",
        )
    }
    os.environ.update(
        {
            "POLICY_B_ENABLED": "1",
            "POLICY_B_SCORE_MIN": "70",
            "POLICY_B_ADX_MAX": "30",
            "SCALP_SL_ATR_MULT": "2.0",
            "SCALP_TP_ATR_MULT": "4.0",
            "MAX_SL_PIPS": "30",
            "MAX_TP_PIPS": "60",
        }
    )
    try:
        base: dict[str, Any] = {
            "pair": "EURUSD",
            "tf": "M15",
            "direction": "BUY",
            "entry": 1.1,
            "sl": 1.098,
            "tp": 1.104,
            "atr": 0.001,
            "score": 75.0,
            "filter_rejected": False,
            "filter_reasons": [],
            "reasons": "probe|adx=25.0",
        }
        passed = module.apply_policy(base)
        if passed.get("filter_rejected") or passed.get("policy_b_pass") is not True:
            raise DeploymentError("Policy-B pass probe failed")

        high_adx = dict(base)
        high_adx["reasons"] = "probe|adx=35.0"
        rejected = module.apply_policy(high_adx)
        if rejected.get("filter_rejected") is not True:
            raise DeploymentError("Policy-B high-ADX rejection probe failed")

        jpy = dict(base)
        jpy.update(
            {
                "pair": "USDJPY",
                "entry": 150.0,
                "sl": 149.997,
                "tp": 150.006,
                "atr": 0.2,
                "reasons": "probe|adx=25.0",
            }
        )
        normalized = module.apply_policy(jpy)
        if normalized.get("filter_rejected"):
            raise DeploymentError("USDJPY risk probe rejected unexpectedly")
        if normalized.get("sl") != 149.7 or normalized.get("tp") != 150.6:
            raise DeploymentError("USDJPY risk probe levels incorrect")
        if normalized.get("risk_pip_size") != 0.01:
            raise DeploymentError("USDJPY pip-size probe incorrect")

        try:
            module._decode('{"score":NaN}')
        except ValueError:
            pass
        else:
            raise DeploymentError("strict JSON NaN probe failed")
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _backup_files(root: Path, backup: Path) -> None:
    records: list[dict[str, str]] = []
    for item in FILES:
        source = root / item.path
        backup_path = backup / "files" / item.path
        if source.is_file():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup_path)
            records.append({"path": item.path, "state": "existing"})
        else:
            records.append({"path": item.path, "state": "missing"})
    (backup / "files_manifest.json").write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _backup_crontab(backup: Path) -> bool:
    completed = _run(["crontab", "-l"], timeout=15)
    if completed.returncode != 0:
        raise DeploymentError("existing crontab is not readable")
    (backup / "crontab.before.txt").write_text(completed.stdout, encoding="utf-8")
    (backup / "crontab_state.json").write_text(
        json.dumps({"had_crontab": True}) + "\n",
        encoding="utf-8",
    )
    return True


def _deploy_files(root: Path, stage: Path) -> None:
    for item in FILES:
        source = stage / item.path
        target = root / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.deploy.{os.getpid()}")
        shutil.copyfile(source, temporary)
        os.chmod(temporary, item.mode)
        os.replace(temporary, target)


def _verify_deployed_files(root: Path) -> None:
    for item in FILES:
        actual = _git_blob(root / item.path, root)
        print(f"DEPLOYED_BLOB={item.path}|expected={item.blob}|actual={actual}")
        if actual != item.blob:
            raise DeploymentError(f"deployed blob mismatch: {item.path}")


def _strip_bota_block(current: str) -> str:
    output: list[str] = []
    inside = False
    begin_count = 0
    end_count = 0
    for line in current.splitlines():
        stripped = line.strip()
        if stripped == BOTA_BEGIN:
            if inside:
                raise DeploymentError("nested BotA cron block")
            inside = True
            begin_count += 1
            continue
        if stripped == BOTA_END:
            if not inside:
                raise DeploymentError("unmatched BotA cron end marker")
            inside = False
            end_count += 1
            continue
        if not inside:
            output.append(line)
    if inside or begin_count != end_count or begin_count > 1:
        raise DeploymentError("invalid existing BotA cron block markers")
    while output and not output[-1].strip():
        output.pop()
    return "\n".join(output)


def _install_cron(root: Path, stage: Path) -> None:
    current = _run(["crontab", "-l"], timeout=15)
    if current.returncode != 0:
        raise DeploymentError("existing crontab became unreadable")
    preserved = _strip_bota_block(current.stdout)
    canonical = (root / "ops/bota_crontab.canonical").read_text(encoding="utf-8").strip()
    if not canonical.startswith(BOTA_BEGIN) or not canonical.endswith(BOTA_END):
        raise DeploymentError("canonical BotA cron markers invalid")
    new_text = (preserved + "\n\n" if preserved else "") + canonical + "\n"
    candidate = stage / "crontab.new"
    candidate.write_text(new_text, encoding="utf-8")
    installed = _run(["crontab", str(candidate)], timeout=20)
    if installed.returncode != 0:
        raise DeploymentError("crontab install failed")


def _extract_bota_block(text: str) -> str:
    output: list[str] = []
    inside = False
    seen = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == BOTA_BEGIN:
            if seen or inside:
                raise DeploymentError("duplicate live BotA cron block")
            inside = True
            seen = True
        if inside:
            output.append(line)
        if stripped == BOTA_END and inside:
            inside = False
    if not seen or inside:
        raise DeploymentError("live BotA cron block missing/incomplete")
    return "\n".join(output).strip() + "\n"


def _verify_cron(root: Path) -> None:
    current = _run(["crontab", "-l"], timeout=15)
    if current.returncode != 0:
        raise DeploymentError("cannot read installed crontab")
    live = _extract_bota_block(current.stdout)
    canonical = (root / "ops/bota_crontab.canonical").read_text(encoding="utf-8").strip() + "\n"
    if live != canonical:
        raise DeploymentError("live BotA cron block differs from canonical")
    for token in (
        'PAIRS="EURUSD GBPUSD USDJPY"',
        "POLICY_B_ENABLED=1",
        "POLICY_B_SCORE_MIN=70",
        "POLICY_B_ADX_MAX=30",
        "NEWS_ON=0",
    ):
        if token not in live:
            raise DeploymentError(f"live cron missing token: {token}")


def _restore(root: Path, backup: Path, had_crontab: bool) -> None:
    try:
        records = json.loads((backup / "files_manifest.json").read_text(encoding="utf-8"))
        for record in records:
            target = root / record["path"]
            if record["state"] == "existing":
                source = backup / "files" / record["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            elif target.exists():
                target.unlink()
    except Exception as exc:
        print(f"ROLLBACK_FILES=FAIL|error={type(exc).__name__}")
    else:
        print("ROLLBACK_FILES=PASS")

    cron_backup = backup / "crontab.before.txt"
    if had_crontab:
        restored = _run(["crontab", str(cron_backup)], timeout=20)
    else:
        restored = _run(["crontab", "-r"], timeout=20)
    print("ROLLBACK_CRONTAB=" + ("PASS" if restored.returncode == 0 else "FAIL"))


def _refresh_market_data(root: Path) -> bool:
    env = os.environ.copy()
    runtime_env = root / ".env.runtime"
    command = (
        'if [ -f "$HOME/BotA/.env.runtime" ]; then . "$HOME/BotA/.env.runtime"; fi; '
        'PAIRS="EURUSD GBPUSD USDJPY" TIMEFRAMES="M15 H1 H4 D1" '
        'FETCH_RETRIES=3 FETCH_BACKOFF_BASE=5 FETCH_BACKOFF_MAX=20 '
        'FETCH_MIN_GAP_SECS=1 timeout -k 30s 10m '
        'bash "$HOME/BotA/tools/indicators_updater.sh"'
    )
    if not runtime_env.exists():
        print("RUNTIME_ENV_PRESENT=NO")
    completed = _run(["bash", "-lc", command], cwd=root, env=env, timeout=660)
    print(f"INDICATOR_REFRESH_RC={completed.returncode}")
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout).strip().splitlines()[-3:]
        for line in tail:
            print("INDICATOR_REFRESH_DIAG=" + line[:240])
        return False

    synced = _run(
        [
            "python3",
            str(root / "tools/sync_d1_trend_cache.py"),
            "--pairs",
            *PAIRS,
        ],
        cwd=root,
        timeout=30,
    )
    print(f"D1_SYNC_RC={synced.returncode}")
    if synced.stdout:
        for line in synced.stdout.strip().splitlines():
            print(line)
    return synced.returncode == 0


def _validate_indicator_cache(root: Path) -> bool:
    failures: list[str] = []
    for pair in PAIRS:
        for tf in TIMEFRAMES:
            path = root / "cache" / f"indicators_{pair}_{tf}.json"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("not object")
                if str(data.get("pair", "")).upper() != pair:
                    raise ValueError("pair")
                if str(data.get("timeframe", "")).upper() != tf:
                    raise ValueError("timeframe")
                if data.get("tf_ok", True) is False or data.get("error") == "tf_mismatch":
                    raise ValueError("tf validation")
            except Exception:
                failures.append(f"{pair}:{tf}")
    for pair in PAIRS:
        path = root / "cache" / f"d1_trend_{pair}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("pair") != pair or data.get("trend") not in {"BUY", "SELL"}:
                raise ValueError("trend cache")
        except Exception:
            failures.append(f"{pair}:D1_TREND")
    if failures:
        print("CACHE_VALIDATION_FAILURES=" + ",".join(failures))
        return False
    print("CACHE_VALIDATION_STREAMS=12")
    print("D1_TREND_CACHES=3")
    return True


def _fusion_smoke(root: Path) -> bool:
    env = os.environ.copy()
    env.update(
        {
            "NEWS_ON": "0",
            "POLICY_B_ENABLED": "1",
            "POLICY_B_SCORE_MIN": "70",
            "POLICY_B_ADX_MAX": "30",
            "TELEGRAM_ENABLED": "0",
            "DRY_RUN_MODE": "1",
        }
    )
    failures: list[str] = []
    for pair in PAIRS:
        completed = _run(
            ["bash", str(root / "tools/m15_h1_fusion.sh"), pair],
            cwd=root,
            env=env,
            timeout=90,
        )
        try:
            payload = json.loads(completed.stdout)
            if completed.returncode != 0 or not isinstance(payload, dict):
                raise ValueError("invalid fusion result")
            if payload.get("pair") != pair:
                raise ValueError("wrong pair")
            if str(payload.get("tf", "")).upper() != "M15":
                raise ValueError("wrong timeframe")
            if str(payload.get("direction", "")) not in {"BUY", "SELL", "HOLD"}:
                raise ValueError("bad direction")
        except Exception:
            failures.append(pair)
    if failures:
        print("FUSION_SMOKE_FAILURES=" + ",".join(failures))
        return False
    print("FUSION_SMOKE_PAIRS=3")
    return True


def _write_marker(root: Path, backup: Path, readiness: str) -> None:
    marker_dir = root / "logs" / "deployments"
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / f"weekend_production_{_utc_stamp()}.json"
    payload = {
        "source_commit": SOURCE_COMMIT,
        "readiness": readiness,
        "pairs": list(PAIRS),
        "policy_b": {"score_min": 70, "adx_max_exclusive": 30},
        "backup": str(backup),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "telegram_validation_send": False,
    }
    marker.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"DEPLOYMENT_MARKER={marker}")


def self_check() -> int:
    try:
        _validate_manifest()
        if SOURCE_COMMIT != "588624cba9eb905ca2c4c3fb46303eb692e6ea61":
            raise DeploymentError("source commit changed")
        if PAIRS != ("EURUSD", "GBPUSD", "USDJPY"):
            raise DeploymentError("pair scope changed")
    except DeploymentError as exc:
        print(f"DEPLOY_SELF_CHECK=FAIL|reason={exc}")
        return 1
    print("DEPLOY_SELF_CHECK=PASS")
    print("MANIFEST_FILES=13")
    print("NETWORK_USED=NO")
    print("PRODUCTION_MUTATION=NO")
    return 0


def deploy() -> int:
    root = (Path.home() / "BotA").resolve()
    print("===================================================================")
    print("BOTA WEEKEND PRODUCTION DEPLOYMENT")
    print(f"DEVICE_UTC={datetime.now(timezone.utc).isoformat()}")
    print(f"SOURCE_COMMIT={SOURCE_COMMIT}")
    print("TARGET_PAIRS=EURUSD GBPUSD USDJPY")
    print("POLICY_B=score>=70 AND ADX<30")
    print("TELEGRAM_VALIDATION_SEND=NO")
    print("===================================================================")

    try:
        _validate_manifest()
        _validate_commands()
        if not root.is_dir() or not (root / ".git").exists():
            raise DeploymentError(f"BotA repository missing: {root}")
    except DeploymentError as exc:
        print(f"PRECHECK=FAIL|reason={exc}")
        print("MONDAY_READINESS=FAIL")
        return 1

    backup = root / "logs" / "deploy_backups" / f"weekend_production_{_utc_stamp()}"
    backup.mkdir(parents=True, exist_ok=False)
    had_crontab = False
    mutated = False

    with tempfile.TemporaryDirectory(prefix="bota_weekend_deploy_") as temp:
        stage = Path(temp)
        try:
            _download_and_verify(stage, root)
            _preflight_syntax(stage)
            _policy_probes(stage / "tools/production_signal_policy.py")
            print("SOURCE_INTEGRITY=PASS")
            print("PREFLIGHT_SYNTAX=PASS")
            print("PREFLIGHT_POLICY_PROBES=PASS")

            _backup_files(root, backup)
            had_crontab = _backup_crontab(backup)
            print(f"BACKUP_DIR={backup}")

            _deploy_files(root, stage)
            mutated = True
            _verify_deployed_files(root)
            _policy_probes(root / "tools/production_signal_policy.py")
            print("DEPLOYED_FILE_INTEGRITY=PASS")
            print("POST_DEPLOY_POLICY_PROBES=PASS")

            _install_cron(root, stage)
            _verify_cron(root)
            print("CRONTAB_INSTALL=PASS")
            print("CRONTAB_THREE_PAIR_POLICY=PASS")

            if not _fusion_smoke(root):
                raise DeploymentError("fusion integration smoke failed")
            print("FUSION_INTEGRATION=PASS")
        except (DeploymentError, OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"TRANSACTION_GATE=FAIL|reason={type(exc).__name__}:{exc}")
            if mutated:
                _restore(root, backup, had_crontab)
                print("TRANSACTION_ROLLBACK=ATTEMPTED")
            else:
                print("TRANSACTION_ROLLBACK=NOT_NEEDED")
            print("DEPLOYMENT_INSTALLED=NO")
            print("MONDAY_READINESS=FAIL")
            return 1

    print("TRANSACTION_GATE=PASS")
    print("DEPLOYMENT_INSTALLED=YES")

    data_refresh = _refresh_market_data(root)
    cache_valid = _validate_indicator_cache(root) if data_refresh else False
    print("MARKET_DATA_REFRESH=" + ("PASS" if data_refresh else "FAIL"))
    print("THREE_PAIR_CACHE_VALIDATION=" + ("PASS" if cache_valid else "FAIL"))

    readiness = "PASS" if data_refresh and cache_valid else "DEGRADED_DATA_REFRESH"
    _write_marker(root, backup, readiness)
    print("HISTORICAL_REPLAY_DATA_TOUCHED=NO")
    print("TELEGRAM_VALIDATION_SEND=NO")
    print("MONDAY_READINESS=" + readiness)
    print("===================================================================")
    return 0 if readiness == "PASS" else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy reviewed BotA weekend production candidate")
    parser.add_argument("--self-check", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    return self_check() if args.self_check else deploy()


if __name__ == "__main__":
    raise SystemExit(main())
