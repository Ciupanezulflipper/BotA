#!/usr/bin/env python3
"""Final transactional BotA weekend production deployment for Termux.

One reviewed phone execution deploys the pinned three-pair production runtime,
canonical cron block, and persistent bota-watcher runit launcher. It verifies
source/deployed Git blobs, backs up all replaced runtime state, performs offline
policy/fusion checks with Telegram disabled, refreshes all 12 indicator streams,
derives three D1 trend caches, restarts only bota-watcher, and emits one Monday
readiness verdict.

Secrets are never printed. Historical replay data/results are never touched.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_COMMIT = "080e930a2150c7fcb60fbefb4892f1e7d05424fb"
REPOSITORY = "Ciupanezulflipper/BotA"
PAIRS = ("EURUSD", "GBPUSD", "USDJPY")
TIMEFRAMES = ("M15", "H1", "H4", "D1")
TERMUX_PREFIX = Path("/data/data/com.termux/files/usr")
SERVICE_DIR = TERMUX_PREFIX / "var/service/bota-watcher"
SERVICE_RUN = SERVICE_DIR / "run"
BOTA_BEGIN = "# BotA runtime BEGIN"
BOTA_END = "# BotA runtime END"
BLOB_RE = re.compile(r"^[0-9a-f]{40}$")

WATCHER_RUN = """#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
set +x

ROOT="${HOME}/BotA"
RUNTIME_ENV="${ROOT}/.env.runtime"

if [[ -f "${RUNTIME_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${RUNTIME_ENV}"
  set +a
fi

export PAIRS="EURUSD GBPUSD USDJPY"
export TIMEFRAMES="M15"
export POLICY_B_ENABLED="1"
export POLICY_B_SCORE_MIN="70"
export POLICY_B_ADX_MAX="30"
export NEWS_ON="0"
export FILTER_SCORE_MIN="65"
export FILTER_SCORE_MIN_ALL="65"
export TELEGRAM_MIN_SCORE="70"
export TELEGRAM_TIER_YELLOW_MIN="70"
export TELEGRAM_TIER_YELLOW_MIN_INT="70"
export TELEGRAM_TIER_GREEN_MIN="75"
export TELEGRAM_TIER_GREEN_MIN_INT="75"
export TELEGRAM_COOLDOWN_SECONDS="1800"
export CANDLE_MAX_AGE_SECS="2700"
export DRY_RUN_MODE="0"
export TELEGRAM_ENABLED="1"

exec bash "${ROOT}/tools/signal_watcher_pro.sh"
"""


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
    """Raised when a deployment integrity/readiness gate fails."""


def _stamp() -> str:
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


def _validate_manifest() -> None:
    if len(FILES) != 13 or len({item.path for item in FILES}) != 13:
        raise DeploymentError("runtime manifest shape changed")
    for item in FILES:
        if item.path.startswith("/") or ".." in Path(item.path).parts:
            raise DeploymentError(f"unsafe manifest path: {item.path}")
        if not BLOB_RE.fullmatch(item.blob):
            raise DeploymentError(f"invalid expected blob: {item.path}")


def _require_commands() -> None:
    required = ("bash", "crontab", "curl", "git", "python3", "sv", "timeout")
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        raise DeploymentError("missing commands: " + ",".join(missing))


def _git_blob(path: Path, root: Path) -> str:
    result = _run(
        ["git", "hash-object", "--no-filters", str(path)],
        cwd=root,
        timeout=15,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not BLOB_RE.fullmatch(value):
        raise DeploymentError(f"cannot hash {path.name}")
    return value


def _download(item: DeployFile, stage: Path, root: Path) -> None:
    target = stage / item.path
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{SOURCE_COMMIT}/{item.path}"
    result = _run(
        [
            "curl",
            "--proto", "=https",
            "--proto-redir", "=https",
            "--fail", "--silent", "--show-error", "--location",
            "--retry", "4", "--retry-delay", "1", "--retry-all-errors",
            "--connect-timeout", "15", "--max-time", "90",
            "--output", str(target),
            url,
        ],
        timeout=120,
    )
    if result.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
        raise DeploymentError(f"download failed: {item.path}")
    actual = _git_blob(target, root)
    print(f"SOURCE_BLOB={item.path}|expected={item.blob}|actual={actual}")
    if actual != item.blob:
        raise DeploymentError(f"source blob mismatch: {item.path}")


def _stage_sources(stage: Path, root: Path) -> None:
    for item in FILES:
        _download(item, stage, root)
    for item in FILES:
        path = stage / item.path
        if item.path.endswith(".sh"):
            if _run(["bash", "-n", str(path)], timeout=15).returncode != 0:
                raise DeploymentError(f"shell syntax failed: {item.path}")
        elif item.path.endswith(".py"):
            if _run(["python3", "-m", "py_compile", str(path)], timeout=20).returncode != 0:
                raise DeploymentError(f"python compile failed: {item.path}")
    service_stage = stage / "bota-watcher.run"
    service_stage.write_text(WATCHER_RUN, encoding="utf-8")
    if _run(["bash", "-n", str(service_stage)], timeout=15).returncode != 0:
        raise DeploymentError("watcher service launcher syntax failed")
    cron = (stage / "ops/bota_crontab.canonical").read_text(encoding="utf-8")
    for token in (
        'PAIRS="EURUSD GBPUSD USDJPY"',
        "POLICY_B_ENABLED=1",
        "POLICY_B_SCORE_MIN=70",
        "POLICY_B_ADX_MAX=30",
        "NEWS_ON=0",
    ):
        if token not in cron:
            raise DeploymentError(f"canonical cron missing {token}")


def _load_policy(path: Path):
    spec = importlib.util.spec_from_file_location("bota_deploy_policy", path)
    if spec is None or spec.loader is None:
        raise DeploymentError("cannot load production policy")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _policy_probes(path: Path) -> None:
    module = _load_policy(path)
    with _temporary_policy_env():
        base: dict[str, Any] = {
            "pair": "EURUSD", "tf": "M15", "direction": "BUY",
            "entry": 1.1, "sl": 1.098, "tp": 1.104, "atr": 0.001,
            "score": 75.0, "filter_rejected": False,
            "filter_reasons": [], "reasons": "probe|adx=25.0",
        }
        passed = module.apply_policy(base)
        if passed.get("filter_rejected") or passed.get("policy_b_pass") is not True:
            raise DeploymentError("Policy-B pass probe failed")
        high = dict(base)
        high["reasons"] = "probe|adx=35.0"
        if module.apply_policy(high).get("filter_rejected") is not True:
            raise DeploymentError("Policy-B ADX rejection probe failed")
        jpy = dict(base)
        jpy.update({"pair": "USDJPY", "entry": 150.0, "sl": 149.997,
                    "tp": 150.006, "atr": 0.2})
        jpy_out = module.apply_policy(jpy)
        if jpy_out.get("sl") != 149.7 or jpy_out.get("tp") != 150.6:
            raise DeploymentError("USDJPY risk probe failed")
        if jpy_out.get("risk_pip_size") != 0.01 or jpy_out.get("filter_rejected"):
            raise DeploymentError("USDJPY pip probe failed")
    strict = _run(["python3", str(path)], input_text='{"score":NaN}', timeout=15)
    try:
        strict_payload = json.loads(strict.stdout)
    except ValueError as exc:
        raise DeploymentError("strict JSON probe emitted invalid JSON") from exc
    if strict.returncode != 0 or strict_payload.get("filter_rejected") is not True:
        raise DeploymentError("strict JSON fail-closed probe failed")


class _temporary_policy_env:
    KEYS = {
        "POLICY_B_ENABLED": "1",
        "POLICY_B_SCORE_MIN": "70",
        "POLICY_B_ADX_MAX": "30",
        "SCALP_SL_ATR_MULT": "2.0",
        "SCALP_TP_ATR_MULT": "4.0",
        "MAX_SL_PIPS": "30",
        "MAX_TP_PIPS": "60",
    }

    def __enter__(self):
        self.previous = {key: os.environ.get(key) for key in self.KEYS}
        os.environ.update(self.KEYS)
        return self

    def __exit__(self, exc_type, exc, tb):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return False


def _read_crontab() -> str:
    result = _run(["crontab", "-l"], timeout=15)
    if result.returncode != 0:
        raise DeploymentError("existing crontab is not readable")
    return result.stdout


def _strip_bota_block(text: str) -> str:
    output: list[str] = []
    inside = False
    begin_count = 0
    end_count = 0
    for line in text.splitlines():
        marker = line.strip()
        if marker == BOTA_BEGIN:
            if inside:
                raise DeploymentError("nested BotA cron block")
            inside = True
            begin_count += 1
            continue
        if marker == BOTA_END:
            if not inside:
                raise DeploymentError("unmatched BotA cron end marker")
            inside = False
            end_count += 1
            continue
        if not inside:
            output.append(line)
    if inside or begin_count != end_count or begin_count > 1:
        raise DeploymentError("invalid existing BotA cron markers")
    while output and not output[-1].strip():
        output.pop()
    return "\n".join(output)


def _extract_bota_block(text: str) -> str:
    lines: list[str] = []
    inside = False
    seen = False
    for line in text.splitlines():
        marker = line.strip()
        if marker == BOTA_BEGIN:
            if seen or inside:
                raise DeploymentError("duplicate live BotA cron block")
            seen = True
            inside = True
        if inside:
            lines.append(line)
        if marker == BOTA_END and inside:
            inside = False
    if not seen or inside:
        raise DeploymentError("live BotA cron block missing/incomplete")
    return "\n".join(lines).strip() + "\n"


def _backup(root: Path, backup: Path, current_cron: str) -> None:
    records: list[dict[str, str]] = []
    for item in FILES:
        source = root / item.path
        destination = backup / "files" / item.path
        if source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            records.append({"path": item.path, "state": "existing"})
        else:
            records.append({"path": item.path, "state": "missing"})
    if not SERVICE_RUN.is_file():
        raise DeploymentError(f"persistent watcher launcher missing: {SERVICE_RUN}")
    service_backup = backup / "service" / "bota-watcher.run"
    service_backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SERVICE_RUN, service_backup)
    (backup / "files_manifest.json").write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (backup / "crontab.before.txt").write_text(current_cron, encoding="utf-8")


def _deploy_files(root: Path, stage: Path) -> None:
    for item in FILES:
        target = root / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.deploy.{os.getpid()}")
        shutil.copyfile(stage / item.path, temporary)
        os.chmod(temporary, item.mode)
        os.replace(temporary, target)
        actual = _git_blob(target, root)
        print(f"DEPLOYED_BLOB={item.path}|expected={item.blob}|actual={actual}")
        if actual != item.blob:
            raise DeploymentError(f"deployed blob mismatch: {item.path}")


def _install_service_runner(stage: Path) -> None:
    if not SERVICE_DIR.is_dir():
        raise DeploymentError(f"bota-watcher service missing: {SERVICE_DIR}")
    temporary = SERVICE_RUN.with_name(f".run.deploy.{os.getpid()}")
    shutil.copyfile(stage / "bota-watcher.run", temporary)
    os.chmod(temporary, 0o755)
    os.replace(temporary, SERVICE_RUN)
    if SERVICE_RUN.read_text(encoding="utf-8") != WATCHER_RUN:
        raise DeploymentError("persistent watcher launcher verification failed")


def _install_cron(root: Path, stage: Path, current: str) -> None:
    preserved = _strip_bota_block(current)
    canonical = (root / "ops/bota_crontab.canonical").read_text(encoding="utf-8").strip()
    new_text = (preserved + "\n\n" if preserved else "") + canonical + "\n"
    candidate = stage / "crontab.new"
    candidate.write_text(new_text, encoding="utf-8")
    if _run(["crontab", str(candidate)], timeout=20).returncode != 0:
        raise DeploymentError("crontab install failed")
    live = _extract_bota_block(_read_crontab())
    if live != canonical + "\n":
        raise DeploymentError("live BotA cron block differs from canonical")


def _fusion_smoke(root: Path) -> None:
    env = os.environ.copy()
    env.update({
        "NEWS_ON": "0", "POLICY_B_ENABLED": "1",
        "POLICY_B_SCORE_MIN": "70", "POLICY_B_ADX_MAX": "30",
        "TELEGRAM_ENABLED": "0", "DRY_RUN_MODE": "1",
    })
    for pair in PAIRS:
        result = _run(
            ["bash", str(root / "tools/m15_h1_fusion.sh"), pair],
            cwd=root, env=env, timeout=90,
        )
        try:
            payload = json.loads(result.stdout)
        except ValueError as exc:
            raise DeploymentError(f"fusion JSON invalid: {pair}") from exc
        if result.returncode != 0 or payload.get("pair") != pair:
            raise DeploymentError(f"fusion smoke failed: {pair}")
        if str(payload.get("direction", "")) not in {"BUY", "SELL", "HOLD"}:
            raise DeploymentError(f"fusion direction invalid: {pair}")
    print("FUSION_SMOKE_PAIRS=3")


def _refresh(root: Path) -> bool:
    command = (
        'if [ -f "$HOME/BotA/.env.runtime" ]; then . "$HOME/BotA/.env.runtime"; fi; '
        'PAIRS="EURUSD GBPUSD USDJPY" TIMEFRAMES="M15 H1 H4 D1" '
        'FETCH_RETRIES=3 FETCH_BACKOFF_BASE=5 FETCH_BACKOFF_MAX=20 '
        'FETCH_MIN_GAP_SECS=1 timeout -k 30s 10m '
        'bash "$HOME/BotA/tools/indicators_updater.sh"'
    )
    update = _run(["bash", "-lc", command], cwd=root, timeout=660)
    print(f"INDICATOR_REFRESH_RC={update.returncode}")
    if update.returncode != 0:
        return False
    sync = _run(
        ["python3", str(root / "tools/sync_d1_trend_cache.py"),
         "--pairs", *PAIRS], cwd=root, timeout=30,
    )
    print(f"D1_SYNC_RC={sync.returncode}")
    for line in sync.stdout.strip().splitlines():
        print(line)
    return sync.returncode == 0


def _validate_cache(root: Path) -> bool:
    failures: list[str] = []
    for pair in PAIRS:
        for tf in TIMEFRAMES:
            path = root / "cache" / f"indicators_{pair}_{tf}.json"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                valid = (
                    isinstance(data, dict)
                    and str(data.get("pair", "")).upper() == pair
                    and str(data.get("timeframe", "")).upper() == tf
                    and data.get("tf_ok", True) is not False
                    and data.get("error") != "tf_mismatch"
                )
                if not valid:
                    raise ValueError("invalid bundle")
            except (OSError, ValueError, TypeError):
                failures.append(f"{pair}:{tf}")
        trend_path = root / "cache" / f"d1_trend_{pair}.json"
        try:
            trend = json.loads(trend_path.read_text(encoding="utf-8"))
            if trend.get("pair") != pair or trend.get("trend") not in {"BUY", "SELL"}:
                raise ValueError("invalid trend")
        except (OSError, ValueError, TypeError):
            failures.append(f"{pair}:D1_TREND")
    if failures:
        print("CACHE_VALIDATION_FAILURES=" + ",".join(failures))
        return False
    print("CACHE_VALIDATION_STREAMS=12")
    print("D1_TREND_CACHES=3")
    return True


def _restart_watcher() -> None:
    restart = _run(["sv", "restart", str(SERVICE_DIR)], timeout=30)
    if restart.returncode != 0:
        raise DeploymentError("bota-watcher restart failed")
    status = _run(["sv", "status", str(SERVICE_DIR)], timeout=15)
    if status.returncode != 0 or not status.stdout.startswith("run:"):
        raise DeploymentError("bota-watcher is not up after restart")
    print("BOTA_WATCHER_RESTART=PASS")


def _rollback(root: Path, backup: Path) -> None:
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
        shutil.copy2(backup / "service/bota-watcher.run", SERVICE_RUN)
        os.chmod(SERVICE_RUN, 0o755)
        cron = _run(["crontab", str(backup / "crontab.before.txt")], timeout=20)
        if cron.returncode != 0:
            raise DeploymentError("crontab rollback failed")
        _run(["sv", "restart", str(SERVICE_DIR)], timeout=30)
    except (OSError, ValueError, DeploymentError) as exc:
        print(f"ROLLBACK=FAIL|reason={type(exc).__name__}")
    else:
        print("ROLLBACK=PASS")


def _marker(root: Path, backup: Path, readiness: str) -> None:
    directory = root / "logs/deployments"
    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / f"weekend_production_{_stamp()}.json"
    marker.write_text(
        json.dumps({
            "source_commit": SOURCE_COMMIT,
            "readiness": readiness,
            "pairs": list(PAIRS),
            "policy_b": {"score_min": 70, "adx_max_exclusive": 30},
            "backup": str(backup),
            "telegram_validation_send": False,
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"DEPLOYMENT_MARKER={marker}")


def self_check() -> int:
    try:
        _validate_manifest()
        if SOURCE_COMMIT != "080e930a2150c7fcb60fbefb4892f1e7d05424fb":
            raise DeploymentError("source commit changed")
        if PAIRS != ("EURUSD", "GBPUSD", "USDJPY"):
            raise DeploymentError("pair scope changed")
        if 'export PAIRS="EURUSD GBPUSD USDJPY"' not in WATCHER_RUN:
            raise DeploymentError("persistent watcher scope missing")
    except DeploymentError as exc:
        print(f"DEPLOY_SELF_CHECK=FAIL|reason={exc}")
        return 1
    print("DEPLOY_SELF_CHECK=PASS")
    print("RUNTIME_FILES=13")
    print("PERSISTENT_WATCHER_SCOPE=PINNED_THREE_PAIRS")
    print("NETWORK_USED=NO")
    print("PRODUCTION_MUTATION=NO")
    return 0


def deploy() -> int:
    root = (Path.home() / "BotA").resolve()
    print("===================================================================")
    print("BOTA FINAL WEEKEND PRODUCTION DEPLOYMENT")
    print(f"DEVICE_UTC={datetime.now(timezone.utc).isoformat()}")
    print(f"SOURCE_COMMIT={SOURCE_COMMIT}")
    print("TARGET_PAIRS=EURUSD GBPUSD USDJPY")
    print("POLICY_B=score>=70 AND ADX<30")
    print("TELEGRAM_VALIDATION_SEND=NO")
    print("===================================================================")
    try:
        _validate_manifest()
        _require_commands()
        if not (root / ".git").is_dir():
            raise DeploymentError("BotA repository missing")
        if not SERVICE_RUN.is_file():
            raise DeploymentError("persistent bota-watcher service runner missing")
        current_cron = _read_crontab()
    except DeploymentError as exc:
        print(f"PRECHECK=FAIL|reason={exc}")
        print("MONDAY_READINESS=FAIL")
        return 1

    backup = root / "logs/deploy_backups" / f"weekend_production_{_stamp()}"
    backup.mkdir(parents=True, exist_ok=False)
    mutated = False
    with tempfile.TemporaryDirectory(prefix="bota_final_deploy_") as temp:
        stage = Path(temp)
        try:
            _stage_sources(stage, root)
            _policy_probes(stage / "tools/production_signal_policy.py")
            print("SOURCE_INTEGRITY=PASS")
            print("PREFLIGHT_POLICY_PROBES=PASS")
            _backup(root, backup, current_cron)
            print(f"BACKUP_DIR={backup}")
            _deploy_files(root, stage)
            _install_service_runner(stage)
            _install_cron(root, stage, current_cron)
            mutated = True
            _policy_probes(root / "tools/production_signal_policy.py")
            _fusion_smoke(root)
            print("DEPLOYED_FILE_INTEGRITY=PASS")
            print("CRONTAB_THREE_PAIR_POLICY=PASS")
            print("PERSISTENT_WATCHER_LAUNCHER=PASS")
            print("FUSION_INTEGRATION=PASS")
        except (DeploymentError, OSError, ValueError) as exc:
            print(f"TRANSACTION_GATE=FAIL|reason={type(exc).__name__}:{exc}")
            if mutated:
                _rollback(root, backup)
            print("DEPLOYMENT_INSTALLED=NO")
            print("MONDAY_READINESS=FAIL")
            return 1

    print("TRANSACTION_GATE=PASS")
    print("DEPLOYMENT_INSTALLED=YES")
    refreshed = _refresh(root)
    cache_ok = _validate_cache(root) if refreshed else False
    print("MARKET_DATA_REFRESH=" + ("PASS" if refreshed else "FAIL"))
    print("THREE_PAIR_CACHE_VALIDATION=" + ("PASS" if cache_ok else "FAIL"))
    if not (refreshed and cache_ok):
        _marker(root, backup, "DEGRADED_DATA_REFRESH")
        print("BOTA_WATCHER_RESTART=DEFERRED")
        print("HISTORICAL_REPLAY_DATA_TOUCHED=NO")
        print("MONDAY_READINESS=DEGRADED_DATA_REFRESH")
        return 2
    try:
        _restart_watcher()
    except DeploymentError as exc:
        print(f"WATCHER_ACTIVATION=FAIL|reason={exc}")
        _rollback(root, backup)
        print("DEPLOYMENT_INSTALLED=NO")
        print("MONDAY_READINESS=FAIL")
        return 1
    _marker(root, backup, "PASS")
    print("PERSISTENT_WATCHER_THREE_PAIR_SCOPE=PASS")
    print("HISTORICAL_REPLAY_DATA_TOUCHED=NO")
    print("TELEGRAM_VALIDATION_SEND=NO")
    print("MONDAY_READINESS=PASS")
    print("===================================================================")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy final reviewed BotA weekend production candidate")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    return self_check() if args.self_check else deploy()


if __name__ == "__main__":
    raise SystemExit(main())
