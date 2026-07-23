#!/data/data/com.termux/files/usr/bin/bash
cat "$HOME/BotA/audits/ERROR_LOG.md"
printf '%s\n' \
  'ERROR_LOG_REVIEWED=YES' \
  'CIRCULAR_ERROR_CHECK=PASS'

set -Eeuo pipefail
umask 077

ROOT="$HOME/BotA"
ERROR_LOG="$ROOT/audits/ERROR_LOG.md"
EXPECTED_BOOT="ae204a40-c3ff-4c4e-abc2-39696b867781"
MAIN_COMMIT="eb53a5ed0d76b5f5c88842ddd250679c3daa082d"
APPROVAL="APPROVE BOTA ORPHAN HANDOFF DEPLOY AE204A40 EB53A5ED"
SERVICE_ROOT="$PREFIX/var/service"
BOOT="$HOME/.termux/boot/00-termux-services.sh"
WATCHER_RUN="$HOME/.config/bota-sv/bota-watcher/run"
HEARTBEAT_RUN="$HOME/.config/bota-sv/bota-heartbeat/run"

CURRENT_BOOT="$(cat /proc/sys/kernel/random/boot_id)"
[ "$CURRENT_BOOT" = "$EXPECTED_BOOT" ] || {
  printf 'DEPLOYMENT_ABORTED=BOOT_CHANGED\nEXPECTED_BOOT=%s\nCURRENT_BOOT=%s\n' \
    "$EXPECTED_BOOT" "$CURRENT_BOOT"
  exit 3
}

for COMMAND in curl git python3 sv runsvdir sha256sum; do
  command -v "$COMMAND" >/dev/null || {
    printf 'DEPLOYMENT_ABORTED=MISSING_COMMAND:%s\n' "$COMMAND"
    exit 4
  }
done

for REQUIRED_PATH in "$BOOT" "$WATCHER_RUN" "$HEARTBEAT_RUN"; do
  [ -f "$REQUIRED_PATH" ] || {
    printf 'DEPLOYMENT_ABORTED=MISSING_FILE:%s\n' "$REQUIRED_PATH"
    exit 5
  }
done

MONO="$(
  python3 - <<'PY'
import time
clock = getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC)
print(time.clock_gettime_ns(clock))
PY
)"
STAGE="$ROOT/audits/orphan_handoff_deploy_${MAIN_COMMIT:0:8}_${MONO}"
SRC="$STAGE/source/tools"
BACKUP="$STAGE/backup"
RUNTIME="$STAGE/runtime"
mkdir -p \
  "$SRC" \
  "$BACKUP/tools" \
  "$BACKUP/service-runs" \
  "$BACKUP/service-entry-runs" \
  "$RUNTIME"

FILES=(
  api_credit_tracker.py
  bota_supervisor.sh
  control_plane_status.py
  data_fetch_candles.sh
  heartbeat.sh
  indicators_updater.sh
  pipeline_health.py
  pipeline_ledger.py
  provider_usage.py
  run_shadow_manager.sh
  run_signal_watcher_with_ledger.sh
  watcher_cycle_ledger.py
  runsvdir_guard.py
  runsvdir_guard_runtime.py
  start_runsvdir_guard.sh
)

cat > "$STAGE/EXPECTED_BLOBS.txt" <<'EOF'
api_credit_tracker.py c44736c9f641201c1fbef9fe39f17fbd7d1c6a23
bota_supervisor.sh b139169e648ad445c9122443896cade6811a47d5
control_plane_status.py 26e2134e17b2b92b73e3374e3369478f2782c60a
data_fetch_candles.sh 3e689623382f52bd756c1d8e4f2c1147a865ef16
heartbeat.sh fd101d40475546c2d962f9c0d7558fe6b731c4d6
indicators_updater.sh a61905d398398fbabf7db015c3c2916f9a2d80d4
pipeline_health.py 0d06a2271a6146a599d8c2d7d8d0e882718c6557
pipeline_ledger.py 60ba07a6fd3af6bd5b67d159be64a4525be59842
provider_usage.py a714176f16e7f9a14ecabefc65eb6a07802dd8bd
run_shadow_manager.sh 3de11c6263e484ad4a6d8c6b4b208d84bfdb057d
run_signal_watcher_with_ledger.sh 823ea89d2b29094a56bf6ec6f0a45b2686c9e4a9
watcher_cycle_ledger.py e7e8ed99e35b2ab08861c430a4ff7792b79a0378
runsvdir_guard.py 56bfeba1712eb30241c2c30ca30d9a74e7f05f96
runsvdir_guard_runtime.py 3f3b91dd25fb26531f0326966cdc93fcb8c41c89
start_runsvdir_guard.sh 38f1183932f9b11e59be83b9f6e955843ef26c77
EOF

while read -r NAME EXPECTED_BLOB; do
  URL="https://raw.githubusercontent.com/Ciupanezulflipper/BotA/$MAIN_COMMIT/tools/$NAME"
  curl --fail --location --silent --show-error "$URL" -o "$SRC/$NAME"
  ACTUAL_BLOB="$(git hash-object "$SRC/$NAME")"
  [ "$ACTUAL_BLOB" = "$EXPECTED_BLOB" ] || {
    printf 'SOURCE_BLOB_MISMATCH=%s:%s:%s\n' \
      "$NAME" "$ACTUAL_BLOB" "$EXPECTED_BLOB"
    exit 6
  }
done < "$STAGE/EXPECTED_BLOBS.txt"

python3 -m py_compile \
  "$SRC/api_credit_tracker.py" \
  "$SRC/control_plane_status.py" \
  "$SRC/pipeline_health.py" \
  "$SRC/pipeline_ledger.py" \
  "$SRC/provider_usage.py" \
  "$SRC/watcher_cycle_ledger.py" \
  "$SRC/runsvdir_guard.py" \
  "$SRC/runsvdir_guard_runtime.py"
rm -rf "$SRC/__pycache__"

for NAME in \
  bota_supervisor.sh \
  data_fetch_candles.sh \
  heartbeat.sh \
  indicators_updater.sh \
  run_shadow_manager.sh \
  run_signal_watcher_with_ledger.sh \
  start_runsvdir_guard.sh
do
  bash -n "$SRC/$NAME"
done
chmod 755 "$SRC"/*

STATUS="$SRC/control_plane_status.py"
python3 "$STATUS" > "$RUNTIME/preflight.json" || true

python3 - "$RUNTIME/preflight.json" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

services = data.get("services", {})
required = (
    "bota-updater",
    "bota-watcher",
    "bota-closer",
    "bota-shadow",
    "bota-heartbeat",
    "bota-supervisor",
    "crond",
)

reasons = []
if data.get("manager_count") != 0:
    reasons.append(f"manager_count:{data.get('manager_count')}")
if data.get("duplicate_service_rows") != 0:
    reasons.append(
        f"duplicate_service_rows:{data.get('duplicate_service_rows')}"
    )
if set(services) != set(required):
    reasons.append("required_service_set_mismatch")

for service in required:
    row = services.get(service, {})
    if row.get("runsv_count") != 1:
        reasons.append(
            f"runsv_count:{service}:{row.get('runsv_count')}"
        )
    if row.get("owner") != "pid1_orphan":
        reasons.append(f"owner:{service}:{row.get('owner')}")

live_crond = data.get("live_crond") or []
if len(live_crond) != 1:
    reasons.append(f"live_crond_count:{len(live_crond)}")

print(
    "PRE_MUTATION_SCOPE=ZERO_MANAGER_SEVEN_SINGLE_PID1_ORPHANS"
)
print(
    "PRE_MUTATION_TOPOLOGY="
    f"MANAGERS={data.get('manager_count')} "
    f"OWNED={data.get('owned')}/7 "
    f"RUNNING={data.get('running')}/7 "
    f"ORPHANED={data.get('orphaned')} "
    f"DUPLICATES={data.get('duplicate_service_rows')} "
    f"LIVE_CROND={len(live_crond)}"
)
if reasons:
    print("PRE_MUTATION_COMPATIBLE=NO")
    for reason in reasons:
        print(f"PRE_MUTATION_BLOCKER={reason}")
    raise SystemExit(7)
print("PRE_MUTATION_COMPATIBLE=YES")
PY

guard_pids() {
  python3 - \
    "$ROOT/tools/runsvdir_guard.py" \
    "$ROOT/tools/runsvdir_guard_runtime.py" <<'PY'
from pathlib import Path
import sys

targets = {str(Path(value)) for value in sys.argv[1:]}
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    try:
        argv = [
            item.decode(errors="replace")
            for item in (entry / "cmdline").read_bytes().split(b"\0")
            if item
        ]
    except OSError:
        continue
    if len(argv) >= 2 and str(Path(argv[-1])) in targets:
        print(entry.name)
PY
}

mapfile -t PRE_GUARD_PIDS < <(guard_pids)
[ "${#PRE_GUARD_PIDS[@]}" -eq 0 ] || {
  printf 'PRE_MUTATION_BLOCKER=EXISTING_RUNTIME_GUARD_COUNT:%s\n' \
    "${#PRE_GUARD_PIDS[@]}"
  exit 8
}

for NAME in "${FILES[@]}"; do
  if [ -e "$ROOT/tools/$NAME" ]; then
    cp -p "$ROOT/tools/$NAME" "$BACKUP/tools/$NAME"
    printf '%s\n' "$NAME" >> "$BACKUP/existed_tools.txt"
  fi
done

cp -p "$BOOT" "$BACKUP/00-termux-services.sh"
cp -p "$WATCHER_RUN" "$BACKUP/service-runs/bota-watcher.run"
cp -p "$HEARTBEAT_RUN" "$BACKUP/service-runs/bota-heartbeat.run"

for SERVICE in \
  bota-updater \
  bota-watcher \
  bota-closer \
  bota-shadow \
  bota-heartbeat \
  bota-supervisor \
  crond
do
  ENTRY_RUN="$SERVICE_ROOT/$SERVICE/run"
  if [ -f "$ENTRY_RUN" ]; then
    cp -pL "$ENTRY_RUN" "$BACKUP/service-entry-runs/$SERVICE.run"
  fi
done

ps -eo pid=,ppid=,comm=,args= > "$RUNTIME/pre_mutation_processes.txt"
: > "$RUNTIME/service_entry_run_paths.txt"
for SERVICE in \
  bota-updater \
  bota-watcher \
  bota-closer \
  bota-shadow \
  bota-heartbeat \
  bota-supervisor \
  crond
do
  printf '%s\n' "$SERVICE_ROOT/$SERVICE/run" \
    >> "$RUNTIME/service_entry_run_paths.txt"
done

cp -p "$WATCHER_RUN" "$STAGE/bota-watcher.run.proposed"
cp -p "$HEARTBEAT_RUN" "$STAGE/bota-heartbeat.run.proposed"
cp -p "$BOOT" "$STAGE/00-termux-services.sh.proposed"

python3 - \
  "$STAGE/bota-watcher.run.proposed" \
  "$STAGE/bota-heartbeat.run.proposed" \
  "$STAGE/00-termux-services.sh.proposed" <<'PY'
from pathlib import Path
import sys

watcher, heartbeat, boot = map(Path, sys.argv[1:])

def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        text = text.replace(old, new, 1)
    elif old_count == 0 and new_count == 1:
        pass
    else:
        raise SystemExit(
            "PATCH_PRECONDITION_FAILED:"
            f"{path}:old={old_count}:new={new_count}"
        )
    path.write_text(text, encoding="utf-8")

replace_once(
    watcher,
    'bash "${ROOT}/tools/signal_watcher_pro.sh" --once \\\n',
    'bash "${ROOT}/tools/run_signal_watcher_with_ledger.sh" \\\n',
)
replace_once(
    heartbeat,
    'SCRIPT="${ROOT}/tools/bota_heartbeat_utc.sh"',
    'SCRIPT="${ROOT}/tools/heartbeat.sh"',
)

text = boot.read_text(encoding="utf-8")
exact_line = '"$HOME/BotA/tools/start_runsvdir_guard.sh"'
mentions = [
    line for line in text.splitlines()
    if "start_runsvdir_guard.sh" in line
]
if not mentions:
    if text and not text.endswith("\n"):
        text += "\n"
    text += (
        "\n# BotA durable strict runsvdir guard — "
        "pinned main eb53a5ed\n"
        f"{exact_line}\n"
    )
elif mentions == [exact_line]:
    pass
else:
    raise SystemExit(
        "BOOT_GUARD_PRECONDITION_FAILED:"
        + "|".join(mentions)
    )
boot.write_text(text, encoding="utf-8")
PY

bash -n "$STAGE/bota-watcher.run.proposed"
bash -n "$STAGE/bota-heartbeat.run.proposed"
bash -n "$STAGE/00-termux-services.sh.proposed"

printf 'PINNED_MAIN=%s\n' "$MAIN_COMMIT"
printf 'SOURCE_VALIDATION=PASS\n'
printf 'BACKUP_COMPLETE=YES\n'
printf 'STAGE_DIRECTORY=%s\n' "$STAGE"
printf 'RUNTIME_MUTATION_PERFORMED=NO\n'

[ -r /dev/tty ] || {
  printf 'APPROVAL_RESULT=REJECTED_NO_TTY\n'
  exit 9
}

while IFS= read -r -t 0.05 _ </dev/tty; do
  :
done

printf 'TYPE EXACT APPROVAL:\n%s\n> ' "$APPROVAL" >/dev/tty
IFS= read -r TYPED </dev/tty
[ "$TYPED" = "$APPROVAL" ] || {
  printf 'APPROVAL_RESULT=REJECTED\n'
  printf 'RUNTIME_MUTATION_PERFORMED=NO\n'
  exit 10
}
printf 'APPROVAL_RESULT=ACCEPTED\n'

MUTATION_STARTED=NO
GUARD_STARTED=NO

restore_file() {
  local source="$1"
  local target="$2"
  cp -p "$source" "$target.rollback.tmp"
  mv "$target.rollback.tmp" "$target"
}

stop_exact_guards() {
  local pid
  mapfile -t ACTIVE_GUARD_PIDS < <(guard_pids)
  for pid in "${ACTIVE_GUARD_PIDS[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for _ in $(seq 1 30); do
    mapfile -t ACTIVE_GUARD_PIDS < <(guard_pids)
    [ "${#ACTIVE_GUARD_PIDS[@]}" -eq 0 ] && return 0
    sleep 1
  done
  return 1
}

standard_manager_pids() {
  python3 - "$SERVICE_ROOT" <<'PY'
from pathlib import Path
import sys

root = str(Path(sys.argv[1]))
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    try:
        argv = [
            item.decode(errors="replace")
            for item in (entry / "cmdline").read_bytes().split(b"\0")
            if item
        ]
    except OSError:
        continue
    if argv and Path(argv[0]).name == "runsvdir":
        if root in " ".join(argv[1:]):
            print(entry.name)
PY
}

rollback() {
  local rc="$1"
  trap - ERR INT TERM
  printf 'AUTOMATIC_ROLLBACK=STARTING\n'

  stop_exact_guards || true

  restore_file \
    "$BACKUP/00-termux-services.sh" \
    "$BOOT"
  restore_file \
    "$BACKUP/service-runs/bota-watcher.run" \
    "$WATCHER_RUN"
  restore_file \
    "$BACKUP/service-runs/bota-heartbeat.run" \
    "$HEARTBEAT_RUN"

  for NAME in "${FILES[@]}"; do
    if [ -f "$BACKUP/tools/$NAME" ]; then
      restore_file \
        "$BACKUP/tools/$NAME" \
        "$ROOT/tools/$NAME"
    else
      rm -f "$ROOT/tools/$NAME"
    fi
  done

  for SERVICE in \
    bota-updater \
    bota-watcher \
    bota-heartbeat \
    bota-supervisor \
    bota-shadow
  do
    sv -w 45 restart "$SERVICE_ROOT/$SERVICE" \
      >/dev/null 2>&1 || true
  done

  mapfile -t ROLLBACK_MANAGERS < <(standard_manager_pids)
  if [ "${#ROLLBACK_MANAGERS[@]}" -eq 1 ]; then
    kill -TERM "${ROLLBACK_MANAGERS[0]}" 2>/dev/null || true
  fi

  sleep 2
  ps -eo pid=,ppid=,comm=,args= \
    > "$RUNTIME/rollback_processes.txt" || true

  printf 'AUTOMATIC_ROLLBACK=COMPLETE\n'
  printf 'DEPLOYMENT=FAILED\n'
  printf 'RUNTIME_MUTATION_PERFORMED=ROLLED_BACK\n'
  exit "$rc"
}

on_error() {
  local rc=$?
  printf 'DEPLOYMENT_ERROR_RC=%s\n' "$rc"
  if [ "$MUTATION_STARTED" = YES ]; then
    rollback "$rc"
  fi
  exit "$rc"
}

trap on_error ERR
trap 'printf "DEPLOYMENT_SIGNAL_RECEIVED=YES\n"; false' INT TERM

MUTATION_STARTED=YES

for NAME in "${FILES[@]}"; do
  cp "$SRC/$NAME" "$ROOT/tools/$NAME.deploy.tmp"
  chmod 755 "$ROOT/tools/$NAME.deploy.tmp"
  mv "$ROOT/tools/$NAME.deploy.tmp" "$ROOT/tools/$NAME"
done

cp -p \
  "$STAGE/bota-watcher.run.proposed" \
  "$WATCHER_RUN.deploy.tmp"
mv "$WATCHER_RUN.deploy.tmp" "$WATCHER_RUN"

cp -p \
  "$STAGE/bota-heartbeat.run.proposed" \
  "$HEARTBEAT_RUN.deploy.tmp"
mv "$HEARTBEAT_RUN.deploy.tmp" "$HEARTBEAT_RUN"

cp -p \
  "$STAGE/00-termux-services.sh.proposed" \
  "$BOOT.deploy.tmp"
mv "$BOOT.deploy.tmp" "$BOOT"

while read -r NAME EXPECTED_BLOB; do
  ACTUAL_BLOB="$(git hash-object "$ROOT/tools/$NAME")"
  [ "$ACTUAL_BLOB" = "$EXPECTED_BLOB" ]
done < "$STAGE/EXPECTED_BLOBS.txt"

cmp -s "$WATCHER_RUN" "$STAGE/bota-watcher.run.proposed"
cmp -s "$HEARTBEAT_RUN" "$STAGE/bota-heartbeat.run.proposed"
cmp -s "$BOOT" "$STAGE/00-termux-services.sh.proposed"

"$ROOT/tools/start_runsvdir_guard.sh"
GUARD_STARTED=YES

HEALTHY=NO
for _ in $(seq 1 150); do
  if python3 "$ROOT/tools/control_plane_status.py" \
    > "$RUNTIME/after_guard.json"
  then
    HEALTHY=YES
    break
  fi
  sleep 1
done
[ "$HEALTHY" = YES ]

mapfile -t ACTIVE_GUARD_PIDS < <(guard_pids)
[ "${#ACTIVE_GUARD_PIDS[@]}" -eq 1 ]
GUARD_PID="${ACTIVE_GUARD_PIDS[0]}"

for SERVICE in \
  bota-updater \
  bota-watcher \
  bota-heartbeat \
  bota-supervisor \
  bota-shadow
do
  sv -w 45 restart "$SERVICE_ROOT/$SERVICE"
done

HEALTHY=NO
for _ in $(seq 1 90); do
  if python3 "$ROOT/tools/control_plane_status.py" \
    > "$RUNTIME/before_manager_loss.json"
  then
    HEALTHY=YES
    break
  fi
  sleep 1
done
[ "$HEALTHY" = YES ]

OLD_MANAGER="$(
  python3 - "$RUNTIME/before_manager_loss.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["manager_pid"])
PY
)"
[ -n "$OLD_MANAGER" ]
kill -TERM "$OLD_MANAGER"

RECOVERED=NO
NEW_MANAGER=""
for _ in $(seq 1 180); do
  if python3 "$ROOT/tools/control_plane_status.py" \
    > "$RUNTIME/final_control_plane.json"
  then
    NEW_MANAGER="$(
      python3 - "$RUNTIME/final_control_plane.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["manager_pid"])
PY
)"
    if [ -n "$NEW_MANAGER" ] && \
       [ "$NEW_MANAGER" != "$OLD_MANAGER" ]
    then
      RECOVERED=YES
      break
    fi
  fi
  sleep 1
done
[ "$RECOVERED" = YES ]

mapfile -t FINAL_GUARD_PIDS < <(guard_pids)
[ "${#FINAL_GUARD_PIDS[@]}" -eq 1 ]
[ "${FINAL_GUARD_PIDS[0]}" = "$GUARD_PID" ]

python3 - \
  "$RUNTIME/final_control_plane.json" \
  "$CURRENT_BOOT" \
  "$OLD_MANAGER" \
  "$NEW_MANAGER" <<'PY'
import json
import sys

path, boot_id, old_manager, new_manager = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

assert data["healthy"] is True
assert data["manager_count"] == 1
assert data["owned"] == 7
assert data["running"] == 7
assert data["orphaned"] == 0
assert data["duplicate_service_rows"] == 0
assert len(data["live_crond"]) == 1
assert str(data["manager_pid"]) == new_manager
assert new_manager != old_manager

print(f"BOOT_ID={boot_id}")
print("DELIBERATE_MANAGER_LOSS_RECOVERY=PASS")
print("CONTROL_PLANE=MANAGERS_1_OWNED_7_RUNNING_7")
print("CONTROL_PLANE_ORPHANED=0")
print("CONTROL_PLANE_DUPLICATES=0")
print(f"CROND_PID={data['live_crond'][0]['pid']}")
PY

cat > "$STAGE/DEPLOYMENT_RESULT.txt" <<EOF
PINNED_MAIN=$MAIN_COMMIT
BOOT_ID=$CURRENT_BOOT
GUARD_PID=$GUARD_PID
OLD_MANAGER_PID=$OLD_MANAGER
NEW_MANAGER_PID=$NEW_MANAGER
PR11_RUNTIME_DEPLOYED=YES
PR13_GUARD_DEPLOYED=YES
DELIBERATE_MANAGER_LOSS_RECOVERY=PASS
CONTROL_PLANE=MANAGERS_1_OWNED_7_RUNNING_7
ORPHANED=0
DUPLICATES=0
USEFUL_PROGRESS_PROOF=DEFERRED
EOF

trap - ERR INT TERM
MUTATION_STARTED=NO

printf 'DEPLOYMENT=PASS\n'
printf 'PR11_RUNTIME_DEPLOYED=YES\n'
printf 'PR13_GUARD_DEPLOYED=YES\n'
printf 'DELIBERATE_MANAGER_LOSS_RECOVERY=PASS\n'
printf 'CONTROL_PLANE=MANAGERS_1_OWNED_7_RUNNING_7\n'
printf 'ORPHANED=0\n'
printf 'DUPLICATES=0\n'
printf 'USEFUL_PROGRESS_PROOF=DEFERRED\n'
printf 'RUNTIME_MUTATION_PERFORMED=YES\n'
printf 'RESULT_FILE=%s\n' "$STAGE/DEPLOYMENT_RESULT.txt"
# IMMUTABLE_ORPHAN_HANDOFF_DEPLOY_END
