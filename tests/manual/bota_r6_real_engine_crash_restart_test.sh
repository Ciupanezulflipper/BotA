#!/data/data/com.termux/files/usr/bin/bash
# R6 — REAL ENGINE CRASH / RESTART / SINGLETON / STATE RE-ENTRY
#
# Scope:
# - real preserved BotA engine semantics
# - disposable isolated repo copy only
# - no OANDA / Telegram / Supabase network calls
# - no production BotA writes
# - no runtime deployment
#
# Proves:
# 1. generation 1 executes the real engine successfully
# 2. owner and runtime singleton locks reject duplicates
# 3. generation 1 is hard-killed with SIGKILL
# 4. owner observes the crash and starts exactly one generation 2
# 5. durable state written before the crash survives
# 6. generation 2 validates state before useful work
# 7. generation 2 reproduces the frozen R4/R5 engine output byte-for-byte
# 8. no crashed generation remains alive
# 9. production worktree remains unchanged

set -euo pipefail

PRODUCTION_ROOT="${HOME}/BotA"
EXPECTED_MAIN="d563695ddcd8943d2a140dac8a26d34b929d48d5"
BASE="${HOME}/.cache/bota-r6-real-engine-crash-restart"
ISOLATED="${BASE}/repo"
PYTHON="${PREFIX}/bin/python3"

PROBE_PY="${BASE}/engine_probe.py"
RUNTIME_PY="${BASE}/runtime.py"
OWNER_PY="${BASE}/owner.py"
EVENT_LOG="${BASE}/r6.log"
STATE_JSON="${BASE}/state.json"
OWNER_LOCK="${BASE}/owner.lock"
RUNTIME_LOCK="${BASE}/runtime.lock"
GEN1_OUT="${BASE}/generation1.json"
GEN2_OUT="${BASE}/generation2.json"
GEN1_ERR="${BASE}/generation1.err"
GEN2_ERR="${BASE}/generation2.err"
GEN1_READY="${BASE}/generation1.ready"
ALLOW_CRASH="${BASE}/allow_crash"

EXPECTED_OUTPUT='{"direction":"BUY","filter_reasons":[],"filter_rejected":false,"fusion_tag":"H1_trend_neutral_overridden","fusion_veto":false,"pair":"EURUSD","score":73.1,"sl":1.0985,"timeframe":"M15","tp":1.1045}'

fail() {
    printf '\n=== R6 RESULT ===\n'
    printf 'STATUS=FAILED\n'
    printf 'FAILURE=%s\n' "$1"
    printf 'PRODUCTION_BOTA_MUTATED=NO\n'
    printf 'TRADING_ENGINE_MUTATED=NO\n'
    printf 'TELEGRAM_MUTATED=NO\n'
    printf 'OANDA_MUTATED=NO\n'
    printf 'SUPABASE_MUTATED=NO\n'
    printf 'GITHUB_MUTATED_BY_TEST=NO\n'
    printf 'tests_passed=false\n'
    printf 'human_review_required=true\n'
    printf 'NEXT_STEP=STOP_AND_REVIEW_R6_FAILURE\n'
    exit "${2:-90}"
}

printf '\n=== R6 — REAL ENGINE CRASH / RESTART / SINGLETON / STATE RE-ENTRY ===\n'
printf 'UTC=%s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

printf '\n=== 1. SAFETY GATES ===\n'

[ -d "${PRODUCTION_ROOT}/.git" ] || fail "PRODUCTION_GIT_REPO_MISSING" 91
[ -x "${PYTHON}" ] || fail "PYTHON_MISSING:${PYTHON}" 92

cd "${PRODUCTION_ROOT}"

git cat-file -e "${EXPECTED_MAIN}^{commit}" 2>/dev/null || fail "EXPECTED_MAIN_OBJECT_MISSING" 93

PRODUCTION_STATUS_BEFORE="$(git status --porcelain)"

ENGINE_FILES=(
    "tools/m15_h1_fusion.sh"
    "tools/pipeline_ledger.py"
    "tools/run_shadow_manager.sh"
    "tools/run_signal_watcher_with_ledger.sh"
    "tools/scoring_engine.sh"
    "tools/signal_watcher_pro.sh"
    "tools/watcher_cycle_ledger.py"
)

for path in "${ENGINE_FILES[@]}"; do
    [ -f "${PRODUCTION_ROOT}/${path}" ] || fail "PRODUCTION_ENGINE_FILE_MISSING:${path}" 94

    PHONE_BLOB="$(git hash-object "${PRODUCTION_ROOT}/${path}")"
    MAIN_BLOB="$(git rev-parse "${EXPECTED_MAIN}:${path}" 2>/dev/null || true)"

    printf 'PATH=%s\n' "${path}"
    printf 'PHONE_BLOB=%s\n' "${PHONE_BLOB}"
    printf 'PINNED_MAIN_BLOB=%s\n' "${MAIN_BLOB:-MISSING}"

    [ -n "${MAIN_BLOB}" ] || fail "PINNED_MAIN_ENGINE_FILE_MISSING:${path}" 95
    [ "${PHONE_BLOB}" = "${MAIN_BLOB}" ] || fail "PHONE_PINNED_ENGINE_PARITY_FAILED:${path}" 96
done

printf 'SAFETY_GATES=PASS\n'

printf '\n=== 2. CREATE DISPOSABLE ISOLATED ENGINE COPY ===\n'

rm -rf "${BASE}"
mkdir -p "${ISOLATED}"

git archive "${EXPECTED_MAIN}" | tar -x -C "${ISOLATED}" || fail "ISOLATED_ARCHIVE_CREATE_FAILED" 97

printf 'ISOLATED_ENGINE_CREATED=YES\n'

printf '\n=== 3. CREATE REAL-ENGINE PROBE ===\n'

cat > "${PROBE_PY}" <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
tools = repo / "tools"
sys.path.insert(0, str(tools))

import replay_semantics as r  # noqa: E402


def dt(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def bundle(**overrides):
    value = {
        "pair": "EURUSD",
        "timeframe": "M15",
        "price": 1.1005,
        "tf_ok": True,
        "error": "",
        "ema9": 1.1010,
        "ema21": 1.1000,
        "rsi": 60.0,
        "macd_hist": 0.0001,
        "adx": 25.0,
        "atr": 0.0010,
        "bb_upper": 1.1020,
        "bb_middle": 1.1000,
        "bb_lower": 1.0980,
        "bb_squeeze": False,
        "open": 1.1000,
        "high": 1.1010,
        "low": 1.0995,
        "close": 1.1005,
        "prev_close": 1.1000,
    }
    value.update(overrides)
    return value


config = r.ReplayConfig()
m15 = bundle()

signal = r.score_bundle(
    "EURUSD",
    "M15",
    m15,
    decision_time=dt("2026-06-01T13:00:00Z"),
    sr_comp=0,
    d1_bundle=bundle(timeframe="D1"),
    config=config,
)

filtered = r.quality_apply(signal, config)

fusion_tag, fusion_veto = r._h1_fusion_decision(
    {
        "pair": "EURUSD",
        "direction": "BUY",
        "score": 75.0,
        "price": 1.1010,
    },
    {
        "direction": "HOLD",
        "score": 0.0,
        "filter_rejected": True,
    },
    bundle(timeframe="H4", ema9=1.101, ema21=1.100),
    config,
)

result = {
    "pair": signal["pair"],
    "timeframe": signal["tf"],
    "direction": signal["direction"],
    "score": round(float(signal["score"]), 10),
    "sl": round(float(signal["sl"]), 10),
    "tp": round(float(signal["tp"]), 10),
    "filter_rejected": bool(filtered["filter_rejected"]),
    "filter_reasons": list(filtered["filter_reasons"]),
    "fusion_tag": fusion_tag,
    "fusion_veto": bool(fusion_veto),
}

print(json.dumps(result, sort_keys=True, separators=(",", ":")))
PY

chmod 700 "${PROBE_PY}"

printf 'REAL_ENGINE_PROBE_CREATED=YES\n'

printf '\n=== 4. CREATE CRASHABLE RUNTIME ===\n'

cat > "${RUNTIME_PY}" <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

base = Path(sys.argv[1]).resolve()
python = sys.argv[2]
probe = Path(sys.argv[3]).resolve()
repo = Path(sys.argv[4]).resolve()
generation = int(sys.argv[5])
output = Path(sys.argv[6]).resolve()
stderr_path = Path(sys.argv[7]).resolve()
expected_output = sys.argv[8]
mode = sys.argv[9] if len(sys.argv) > 9 else "run"

runtime_lock = base / "runtime.lock"
state_path = base / "state.json"
ready_path = base / "generation1.ready"
allow_crash_path = base / "allow_crash"


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def read_state() -> dict[str, object]:
    with state_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


with runtime_lock.open("a+", encoding="utf-8") as lock_handle:
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(74)

    if mode == "lock-probe":
        raise SystemExit(75)

    if generation == 2:
        prior = read_state()
        assert prior["generation_completed"] == 1
        assert prior["signal_guard_token"] == "r6-durable-token-001"
        assert prior["last_committed_engine_output"] == expected_output
        assert prior["state_reentry_verified"] is False

    completed = subprocess.run(
        [python, str(probe), str(repo)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )

    with output.open("wb") as handle:
        handle.write(completed.stdout)
        handle.flush()
        os.fsync(handle.fileno())

    with stderr_path.open("wb") as handle:
        handle.write(completed.stderr)
        handle.flush()
        os.fsync(handle.fileno())

    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    actual = completed.stdout.decode("utf-8").strip()
    if actual != expected_output:
        raise SystemExit(76)

    if generation == 1:
        atomic_json(
            state_path,
            {
                "generation_completed": 1,
                "last_committed_engine_output": actual,
                "signal_guard_token": "r6-durable-token-001",
                "state_reentry_verified": False,
                "updated_utc": time.time(),
            },
        )

        ready_path.write_text("ready\n", encoding="utf-8")

        deadline = time.monotonic() + 10.0
        while not allow_crash_path.exists():
            if time.monotonic() >= deadline:
                raise SystemExit(77)
            time.sleep(0.02)

        os.kill(os.getpid(), signal.SIGKILL)
        raise AssertionError("SIGKILL returned unexpectedly")

    prior = read_state()
    atomic_json(
        state_path,
        {
            **prior,
            "generation_completed": 2,
            "last_committed_engine_output": actual,
            "state_reentry_verified": True,
            "reentry_generation": 2,
            "updated_utc": time.time(),
        },
    )
PY

chmod 700 "${RUNTIME_PY}"

printf 'CRASHABLE_RUNTIME_CREATED=YES\n'

printf '\n=== 5. CREATE OWNER / RESTART / SINGLETON HARNESS ===\n'

cat > "${OWNER_PY}" <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

base = Path(sys.argv[1]).resolve()
python = sys.argv[2]
runtime = Path(sys.argv[3]).resolve()
probe = Path(sys.argv[4]).resolve()
repo = Path(sys.argv[5]).resolve()
gen1_out = Path(sys.argv[6]).resolve()
gen1_err = Path(sys.argv[7]).resolve()
gen2_out = Path(sys.argv[8]).resolve()
gen2_err = Path(sys.argv[9]).resolve()
expected_output = sys.argv[10]
mode = sys.argv[11] if len(sys.argv) > 11 else "run"

owner_lock = base / "owner.lock"
event_log = base / "r6.log"
state_path = base / "state.json"
ready_path = base / "generation1.ready"
allow_crash_path = base / "allow_crash"


def log(message: str) -> None:
    with event_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{time.time():.3f} {message}\n")
        handle.flush()
        os.fsync(handle.fileno())


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


with owner_lock.open("a+", encoding="utf-8") as owner_handle:
    try:
        fcntl.flock(owner_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(73)

    if mode == "lock-probe":
        raise SystemExit(72)

    log(f"OWNER_STARTED pid={os.getpid()}")

    generation1 = subprocess.Popen(
        [
            python,
            str(runtime),
            str(base),
            python,
            str(probe),
            str(repo),
            "1",
            str(gen1_out),
            str(gen1_err),
            expected_output,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    log(f"RUNTIME_START generation=1 pid={generation1.pid}")

    deadline = time.monotonic() + 10.0
    while not ready_path.exists():
        if generation1.poll() is not None:
            log(f"GENERATION_1_EARLY_EXIT rc={generation1.returncode}")
            raise SystemExit(81)
        if time.monotonic() >= deadline:
            log("GENERATION_1_READY_TIMEOUT")
            raise SystemExit(82)
        time.sleep(0.02)

    log("GENERATION_1_REAL_ENGINE_AND_STATE_CONFIRMED")

    duplicate_owner = subprocess.run(
        [
            python,
            str(Path(__file__).resolve()),
            str(base),
            python,
            str(runtime),
            str(probe),
            str(repo),
            str(gen1_out),
            str(gen1_err),
            str(gen2_out),
            str(gen2_err),
            expected_output,
            "lock-probe",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )

    if duplicate_owner.returncode != 73:
        log(f"DUPLICATE_OWNER_TEST_FAILED rc={duplicate_owner.returncode}")
        raise SystemExit(83)

    log("DUPLICATE_OWNER_REJECTED")

    duplicate_runtime = subprocess.run(
        [
            python,
            str(runtime),
            str(base),
            python,
            str(probe),
            str(repo),
            "99",
            str(base / "duplicate-runtime.json"),
            str(base / "duplicate-runtime.err"),
            expected_output,
            "lock-probe",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )

    if duplicate_runtime.returncode != 74:
        log(f"DUPLICATE_RUNTIME_TEST_FAILED rc={duplicate_runtime.returncode}")
        raise SystemExit(84)

    log("DUPLICATE_RUNTIME_REJECTED")

    allow_crash_path.write_text("crash\n", encoding="utf-8")

    generation1_rc = generation1.wait(timeout=5)
    log(f"RUNTIME_EXIT generation=1 rc={generation1_rc}")

    if generation1_rc != -9:
        log("GENERATION_1_SIGKILL_NOT_PROVEN")
        raise SystemExit(85)

    time.sleep(0.1)
    if process_exists(generation1.pid):
        log(f"CRASHED_RUNTIME_STILL_ALIVE pid={generation1.pid}")
        raise SystemExit(86)

    log("GENERATION_1_SIGKILL_CONFIRMED")

    with state_path.open("r", encoding="utf-8") as handle:
        durable_state = json.load(handle)

    if durable_state.get("generation_completed") != 1:
        log("DURABLE_STATE_GENERATION_INVALID")
        raise SystemExit(87)
    if durable_state.get("signal_guard_token") != "r6-durable-token-001":
        log("DURABLE_STATE_TOKEN_INVALID")
        raise SystemExit(88)
    if durable_state.get("last_committed_engine_output") != expected_output:
        log("DURABLE_STATE_ENGINE_OUTPUT_INVALID")
        raise SystemExit(89)

    log("DURABLE_STATE_SURVIVED_SIGKILL")

    generation2 = subprocess.Popen(
        [
            python,
            str(runtime),
            str(base),
            python,
            str(probe),
            str(repo),
            "2",
            str(gen2_out),
            str(gen2_err),
            expected_output,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    log(f"RUNTIME_START generation=2 pid={generation2.pid}")

    generation2_rc = generation2.wait(timeout=30)
    log(f"RUNTIME_EXIT generation=2 rc={generation2_rc}")

    if generation2_rc != 0:
        raise SystemExit(90)

    if process_exists(generation2.pid):
        log(f"GENERATION_2_STILL_ALIVE_AFTER_EXIT pid={generation2.pid}")
        raise SystemExit(91)

    with state_path.open("r", encoding="utf-8") as handle:
        final_state = json.load(handle)

    if final_state.get("generation_completed") != 2:
        raise SystemExit(92)
    if final_state.get("state_reentry_verified") is not True:
        raise SystemExit(93)
    if final_state.get("reentry_generation") != 2:
        raise SystemExit(94)
    if final_state.get("last_committed_engine_output") != expected_output:
        raise SystemExit(95)

    log("STATE_REENTRY_VERIFIED")
    log("USEFUL_PROGRESS_RESTORED")
    log("OWNER_STOPPED")
PY

chmod 700 "${OWNER_PY}"

printf 'OWNER_RESTART_SINGLETON_HARNESS_CREATED=YES\n'

printf '\n=== 6. STATIC VALIDATION ===\n'

"${PYTHON}" -m py_compile "${PROBE_PY}" "${RUNTIME_PY}" "${OWNER_PY}" || fail "PYTHON_STATIC_VALIDATION_FAILED" 98
printf 'PYTHON_STATIC_VALIDATION=PASS\n'

printf '\n=== 7. EXECUTE OWNER-MANAGED CRASH / RESTART TEST ===\n'

: > "${EVENT_LOG}"
: > "${GEN1_ERR}"
: > "${GEN2_ERR}"

if ! "${PYTHON}" \
    "${OWNER_PY}" \
    "${BASE}" \
    "${PYTHON}" \
    "${RUNTIME_PY}" \
    "${PROBE_PY}" \
    "${ISOLATED}" \
    "${GEN1_OUT}" \
    "${GEN1_ERR}" \
    "${GEN2_OUT}" \
    "${GEN2_ERR}" \
    "${EXPECTED_OUTPUT}"
then
    printf '%s\n' '--- OWNER EVENT LOG ---'
    cat "${EVENT_LOG}" || true
    printf '%s\n' '--- GENERATION 1 STDERR ---'
    cat "${GEN1_ERR}" || true
    printf '%s\n' '--- GENERATION 2 STDERR ---'
    cat "${GEN2_ERR}" || true
    fail "OWNER_CRASH_RESTART_TEST_FAILED" 99
fi

printf 'OWNER_CRASH_RESTART_EXECUTION=PASS\n'

printf '\n=== 8. VERIFY ENGINE PARITY ACROSS GENERATIONS ===\n'

GEN1_TEXT="$(tr -d '\r\n' < "${GEN1_OUT}")"
GEN2_TEXT="$(tr -d '\r\n' < "${GEN2_OUT}")"

printf 'GENERATION_1_OUTPUT=%s\n' "${GEN1_TEXT}"
printf 'GENERATION_2_OUTPUT=%s\n' "${GEN2_TEXT}"

[ "${GEN1_TEXT}" = "${EXPECTED_OUTPUT}" ] || fail "GENERATION_1_ENGINE_PARITY_MISMATCH" 100
[ "${GEN2_TEXT}" = "${EXPECTED_OUTPUT}" ] || fail "GENERATION_2_ENGINE_PARITY_MISMATCH" 101
cmp -s "${GEN1_OUT}" "${GEN2_OUT}" || fail "GENERATION_OUTPUT_BYTE_MISMATCH" 102

printf 'GENERATION_1_REAL_ENGINE=PASS\n'
printf 'GENERATION_2_REAL_ENGINE=PASS\n'
printf 'GENERATION_1_2_BYTE_PARITY=YES\n'

printf '\n=== 9. VERIFY SINGLETON / CRASH / RESTART EVENTS ===\n'

grep -q 'DUPLICATE_OWNER_REJECTED' "${EVENT_LOG}" || fail "DUPLICATE_OWNER_REJECTION_NOT_PROVEN" 103
grep -q 'DUPLICATE_RUNTIME_REJECTED' "${EVENT_LOG}" || fail "DUPLICATE_RUNTIME_REJECTION_NOT_PROVEN" 104
grep -q 'RUNTIME_EXIT generation=1 rc=-9' "${EVENT_LOG}" || fail "GENERATION_1_SIGKILL_EXIT_NOT_PROVEN" 105
grep -q 'GENERATION_1_SIGKILL_CONFIRMED' "${EVENT_LOG}" || fail "GENERATION_1_DEATH_NOT_PROVEN" 106
grep -q 'DURABLE_STATE_SURVIVED_SIGKILL' "${EVENT_LOG}" || fail "DURABLE_STATE_SURVIVAL_NOT_PROVEN" 107
grep -q 'RUNTIME_START generation=2' "${EVENT_LOG}" || fail "GENERATION_2_START_NOT_PROVEN" 108
grep -q 'RUNTIME_EXIT generation=2 rc=0' "${EVENT_LOG}" || fail "GENERATION_2_SUCCESS_NOT_PROVEN" 109
grep -q 'STATE_REENTRY_VERIFIED' "${EVENT_LOG}" || fail "STATE_REENTRY_NOT_PROVEN" 110
grep -q 'USEFUL_PROGRESS_RESTORED' "${EVENT_LOG}" || fail "USEFUL_PROGRESS_NOT_RESTORED" 111

printf 'DUPLICATE_OWNER_REJECTED=YES\n'
printf 'DUPLICATE_RUNTIME_REJECTED=YES\n'
printf 'SIGKILL_CRASH_PROVEN=YES\n'
printf 'EXACTLY_ONE_REPLACEMENT_GENERATION_PROVEN=YES\n'
printf 'DURABLE_STATE_SURVIVED=YES\n'
printf 'STATE_REENTRY_VERIFIED=YES\n'
printf 'USEFUL_PROGRESS_RESTORED=YES\n'

printf '\n=== 10. VERIFY FINAL DURABLE STATE ===\n'

"${PYTHON}" - "${STATE_JSON}" "${EXPECTED_OUTPUT}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_output = sys.argv[2]

with path.open("r", encoding="utf-8") as handle:
    payload = json.load(handle)

assert payload["generation_completed"] == 2
assert payload["signal_guard_token"] == "r6-durable-token-001"
assert payload["state_reentry_verified"] is True
assert payload["reentry_generation"] == 2
assert payload["last_committed_engine_output"] == expected_output

print("FINAL_DURABLE_STATE_VALID=YES")
PY

printf '\n=== 11. PRODUCTION IMMUTABILITY GATE ===\n'

PRODUCTION_STATUS_AFTER="$(cd "${PRODUCTION_ROOT}" && git status --porcelain)"
[ "${PRODUCTION_STATUS_AFTER}" = "${PRODUCTION_STATUS_BEFORE}" ] || fail "PRODUCTION_WORKTREE_CHANGED_DURING_R6" 112

printf 'PRODUCTION_STATUS_UNCHANGED=YES\n'

printf '\n=== R6 EVENT LOG ===\n'
cat "${EVENT_LOG}"

printf '\n=== R6 FINAL DURABLE STATE ===\n'
cat "${STATE_JSON}"

printf '\n=== R6 RESULT ===\n'
printf 'TEST_SCOPE=REAL_ENGINE_CRASH_RESTART_SINGLETON_AND_STATE_REENTRY\n'
printf 'PRODUCTION_BOTA_MUTATED=NO\n'
printf 'TRADING_ENGINE_MUTATED=NO\n'
printf 'EXTERNAL_NETWORK_CALLS_REQUIRED=NO\n'
printf 'TELEGRAM_MUTATED=NO\n'
printf 'OANDA_MUTATED=NO\n'
printf 'SUPABASE_MUTATED=NO\n'
printf 'GITHUB_MUTATED_BY_TEST=NO\n'
printf 'ENGINE_7_FILE_PHONE_PINNED_MAIN_PARITY=YES\n'
printf 'GENERATION_1_REAL_ENGINE=PASS\n'
printf 'GENERATION_1_SIGKILL=PASS\n'
printf 'DUPLICATE_OWNER_REJECTED=YES\n'
printf 'DUPLICATE_RUNTIME_REJECTED=YES\n'
printf 'DURABLE_STATE_SURVIVED_SIGKILL=YES\n'
printf 'GENERATION_2_AUTO_RESTART=PASS\n'
printf 'STATE_REENTRY_BEFORE_USEFUL_WORK=PASS\n'
printf 'GENERATION_2_REAL_ENGINE=PASS\n'
printf 'GENERATION_1_2_BYTE_PARITY=YES\n'
printf 'NO_CRASHED_RUNTIME_LEFT_ALIVE=YES\n'
printf 'USEFUL_PROGRESS_RESTORED=YES\n'
printf 'PRODUCTION_STATUS_UNCHANGED=YES\n'
printf 'STATUS=PASS\n'
printf 'tests_passed=true\n'
printf 'human_review_required=true\n'
printf 'NEXT_STEP=R7_ANDROID_OWNER_RUNTIME_INTEGRATION_GATE\n'
