from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]


def run_path_check(script: str, code: Path, mutable: Path, *, configured: bool = True) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(code.parent)
    env["BOTA_CODE_ROOT"] = str(code)
    env["BOTA_ROOT"] = str(code)
    env["BOTA_PATH_CONTRACT_CHECK"] = "1"
    if configured:
        env["BOTA_MUTABLE_ROOT"] = str(mutable)
    else:
        env.pop("BOTA_MUTABLE_ROOT", None)
    result = subprocess.run(
        ["bash", str(REPO / "tools" / script)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


@pytest.mark.parametrize(
    "script",
    [
        "indicators_updater.sh",
        "data_fetch_candles.sh",
        "run_shadow_manager.sh",
        "run_signal_closer_live.sh",
        "signal_watcher_core.sh",
        "run_signal_watcher_with_ledger.sh",
        "run_runtime_health_push.sh",
        "heartbeat.sh",
    ],
)
def test_real_shell_entrypoints_separate_code_and_mutable_roots(
    tmp_path: Path, script: str
) -> None:
    code = tmp_path / "release"
    mutable = tmp_path / "runtime"
    values = run_path_check(script, code, mutable)

    assert values["CODE_ROOT"] == str(code)
    assert values["MUTABLE_ROOT"] == str(mutable)
    for key in ("TOOLS", "SCRIPT", "CONTROLLER", "CONFIG"):
        if key in values:
            assert Path(values[key]).is_relative_to(code)
    for key in ("CACHE", "DATA", "LOGS", "STATE", "LOCK", "PAUSE"):
        if key in values:
            assert Path(values[key]).is_relative_to(mutable)
    assert not code.exists()
    assert not mutable.exists()


def test_unset_mutable_root_preserves_legacy_code_root_behavior(tmp_path: Path) -> None:
    code = tmp_path / "legacy-root"
    values = run_path_check("indicators_updater.sh", code, tmp_path / "unused", configured=False)
    assert values["MUTABLE_ROOT"] == str(code)
    assert Path(values["CACHE"]) == code / "cache"
    assert Path(values["DATA"]) == code / "data"
    assert Path(values["LOCK"]) == code / "state" / "indicators_updater.lock"


def python_json(source: str, code: Path, mutable: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        BOTA_CODE_ROOT=str(code),
        BOTA_ROOT=str(code),
        BOTA_MUTABLE_ROOT=str(mutable),
        PYTHONPATH=str(REPO),
    )
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO,
        env=env,
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    return json.loads(result.stdout.splitlines()[-1])


def test_real_python_workers_resolve_mutable_paths_and_code_tools(tmp_path: Path) -> None:
    code = tmp_path / "release"
    mutable = tmp_path / "runtime"
    values = python_json(
        """
import json
from tools import be_shadow_manager, market_pulse_v2, pipeline_ledger, profitlab_delivery, signal_closer, supabase_publish, sync_d1_trend_cache
a, s, lock, publisher = profitlab_delivery.paths()
print(json.dumps({
  'pipeline_state': str(pipeline_ledger.state_path()),
  'pipeline_events': str(pipeline_ledger.events_path()),
  'pulse_state': str(market_pulse_v2.pulse_state_dir()),
  'profitlab_alerts': str(a), 'profitlab_state': str(s), 'profitlab_lock': str(lock),
  'publisher': str(publisher), 'supabase_root': str(supabase_publish.root_path()),
  'closer_cache': str(signal_closer.CACHE_DIR), 'closer_log': str(signal_closer.LOG_FILE),
  'd1_cache': str(sync_d1_trend_cache.CACHE_DIR),
  'shadow_log': str(be_shadow_manager.LOG_PATH),
  'shadow_heartbeat': str(be_shadow_manager.HEARTBEAT_PATH),
}))
""",
        code,
        mutable,
    )
    for key, raw in values.items():
        path = Path(raw)
        if key == "publisher":
            assert path == code / "tools" / "supabase_publish.py"
        else:
            assert path.is_relative_to(mutable), (key, path)


def test_heartbeat_real_cycle_writes_only_to_mutable_root(tmp_path: Path) -> None:
    code = tmp_path / "release"
    mutable = tmp_path / "runtime"
    values = python_json(
        """
import json
from tools import heartbeat_runtime
heartbeat_runtime.authoritative_server_epoch = lambda: (None, 0)
rc = heartbeat_runtime.run_cycle(__import__('pathlib').Path(__import__('os').environ['BOTA_MUTABLE_ROOT']))
print(json.dumps({'rc': rc}))
""",
        code,
        mutable,
    )
    assert values["rc"] == 0
    assert (mutable / "state" / "heartbeat_delivery.lock").exists()
    assert (mutable / "logs" / "cron.heartbeat.log").exists()
    assert not code.exists()
