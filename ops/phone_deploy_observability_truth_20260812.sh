#!/data/data/com.termux/files/usr/bin/bash
# Deploy the reviewed BotA observability-truth runtime slice without touching
# strategy/config/history. The dirty phone checkout is preserved intentionally.
set -Eeuo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
SOURCE_COMMIT="735b329cf9524748b7fd24cf7ec5fc5136f2272d"
APPLY=0
WAIT_SECONDS="${BOTA_DEPLOY_WAIT_SECONDS:-720}"

while (($#)); do
  case "$1" in
    --apply) APPLY=1 ;;
    --wait-seconds)
      shift
      WAIT_SECONDS="${1:-}"
      ;;
    *) printf 'DEPLOY_ABORTED=UNKNOWN_ARGUMENT:%s\n' "$1"; exit 2 ;;
  esac
  shift
done

[[ "${WAIT_SECONDS}" =~ ^[0-9]+$ ]] || { printf 'DEPLOY_ABORTED=INVALID_WAIT_SECONDS\n'; exit 2; }

PATHS=(
  tools/run_signal_watcher_with_ledger.sh
  tools/watcher_cycle_ledger.py
  tools/supabase_publish.py
)
TEST_PATHS=(
  tests/test_watcher_cycle_observability.py
  tests/test_supabase_cycle_evidence.py
)

cd "${ROOT}" || { printf 'DEPLOY_ABORTED=ROOT_MISSING:%s\n' "${ROOT}"; exit 3; }

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
AUDIT="${ROOT}/audits/observability_truth_deploy_${STAMP}"
STAGE="${AUDIT}/stage"
BACKUP="${AUDIT}/backup"
mkdir -p "${STAGE}/tools" "${STAGE}/tests" "${BACKUP}/tools"
exec > >(tee -a "${AUDIT}/deploy.log") 2>&1

printf '%s\n' \
  'TARGET_PROJECT=BotA' \
  "TARGET_PATH=${ROOT}" \
  "SOURCE_COMMIT=${SOURCE_COMMIT}" \
  "AUDIT_DIRECTORY=${AUDIT}" \
  "APPLY_REQUESTED=${APPLY}"

printf '\n=== PRE-MUTATION REPOSITORY STATE ===\n'
git rev-parse HEAD || true
git status --short || true

# Fetch only Git objects when needed. Never checkout/reset/clean/pull the dirty phone tree.
if ! git cat-file -e "${SOURCE_COMMIT}^{commit}" 2>/dev/null; then
  printf 'SOURCE_COMMIT_LOCAL=NO\n'
  git fetch --no-tags origin "${SOURCE_COMMIT}" || {
    printf 'DEPLOY_ABORTED=SOURCE_COMMIT_FETCH_FAILED\n'
    exit 4
  }
fi
git cat-file -e "${SOURCE_COMMIT}^{commit}" || {
  printf 'DEPLOY_ABORTED=SOURCE_COMMIT_UNAVAILABLE\n'
  exit 4
}
printf 'SOURCE_COMMIT_AVAILABLE=YES\n'

# Stage exact Git objects and verify object identity before any phone mutation.
for path in "${PATHS[@]}" "${TEST_PATHS[@]}"; do
  mkdir -p "${STAGE}/$(dirname "${path}")"
  git cat-file -e "${SOURCE_COMMIT}:${path}" || {
    printf 'DEPLOY_ABORTED=SOURCE_PATH_MISSING:%s\n' "${path}"
    exit 5
  }
  git show "${SOURCE_COMMIT}:${path}" > "${STAGE}/${path}"
  expected_blob="$(git rev-parse "${SOURCE_COMMIT}:${path}")"
  actual_blob="$(git hash-object "${STAGE}/${path}")"
  [[ "${expected_blob}" == "${actual_blob}" ]] || {
    printf 'DEPLOY_ABORTED=STAGE_BLOB_MISMATCH:%s\n' "${path}"
    exit 6
  }
  printf 'STAGE_BLOB_PASS=%s:%s\n' "${path}" "${expected_blob}"
done

printf '\n=== ISOLATED SOURCE VALIDATION ===\n'
bash -n "${STAGE}/tools/run_signal_watcher_with_ledger.sh"
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); compile(p.read_text(encoding="utf-8"), str(p), "exec")' \
  "${STAGE}/tools/watcher_cycle_ledger.py"
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); compile(p.read_text(encoding="utf-8"), str(p), "exec")' \
  "${STAGE}/tools/supabase_publish.py"
(
  cd "${STAGE}"
  PYTHONDONTWRITEBYTECODE=1 python3 tests/test_watcher_cycle_observability.py
  PYTHONDONTWRITEBYTECODE=1 python3 tests/test_supabase_cycle_evidence.py
)
printf 'STAGED_REGRESSION_TESTS=PASS\n'

# Require exact currently healthy ownership before touching a live watcher.
CONTROL_JSON="$(python3 "${ROOT}/tools/control_plane_status.py")" || {
  printf 'DEPLOY_ABORTED=CONTROL_PLANE_STATUS_FAILED\n'
  exit 7
}
printf '%s\n' "${CONTROL_JSON}" > "${AUDIT}/control_plane_pre.json"
printf '%s' "${CONTROL_JSON}" | python3 -c '
import json,sys
x=json.load(sys.stdin)
assert x.get("manager_count")==1, x
assert x.get("owned")==7 and x.get("required")==7, x
assert x.get("running")==7, x
assert x.get("orphaned")==0, x
assert x.get("duplicate_service_rows")==0, x
assert len(x.get("live_crond",[]))==1, x
' || {
  printf 'DEPLOY_ABORTED=CONTROL_PLANE_NOT_EXACT_1_7_7_0_0\n'
  exit 8
}
printf 'CONTROL_PLANE_PREFLIGHT=PASS\n'

# Preserve exact live files and hashes before mutation.
for path in "${PATHS[@]}"; do
  [[ -f "${ROOT}/${path}" ]] || {
    printf 'DEPLOY_ABORTED=TARGET_PATH_MISSING:%s\n' "${path}"
    exit 9
  }
  cp -p "${ROOT}/${path}" "${BACKUP}/tools/${path##*/}"
  printf 'PRE_SHA256='; sha256sum "${ROOT}/${path}"
done

BASELINE_CYCLE="$(python3 - "${ROOT}/state/pipeline_progress.json" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1])
try:
    s=json.loads(p.read_text())
except Exception:
    print("")
else:
    x=s.get("last_terminal_outcome") or {}
    print(x.get("cycle_id") or "")
PY
)"
printf 'BASELINE_WATCHER_CYCLE=%s\n' "${BASELINE_CYCLE}"

if (( APPLY == 0 )); then
  printf '%s\n' \
    'PREFLIGHT_ONLY=PASS' \
    'RUNTIME_MUTATION_PERFORMED=NO' \
    'NEXT=RUN_SAME_SCRIPT_WITH_--apply'
  exit 0
fi

SERVICE="${PREFIX}/var/service/bota-watcher"
[[ -d "${SERVICE}" ]] || { printf 'DEPLOY_ABORTED=WATCHER_SERVICE_MISSING:%s\n' "${SERVICE}"; exit 10; }

MUTATED=0
WATCHER_DOWN=0
ROLLBACK_DONE=0

restore_files() {
  local path name tmp mode
  for path in "${PATHS[@]}"; do
    name="${path##*/}"
    if [[ -f "${BACKUP}/tools/${name}" ]]; then
      mode="$(stat -c '%a' "${BACKUP}/tools/${name}")"
      tmp="${ROOT}/${path}.rollback.$$"
      cp -p "${BACKUP}/tools/${name}" "${tmp}"
      chmod "${mode}" "${tmp}"
      mv -f "${tmp}" "${ROOT}/${path}"
    fi
  done
  ROLLBACK_DONE=1
}

on_exit() {
  local rc=$?
  if (( rc != 0 && MUTATED == 1 )); then
    printf 'DEPLOY_FAILURE_RC=%s\n' "${rc}"
    restore_files || true
    sv up "${SERVICE}" >/dev/null 2>&1 || true
    printf 'FILE_ROLLBACK=PASS\n'
  elif (( WATCHER_DOWN == 1 )); then
    sv up "${SERVICE}" >/dev/null 2>&1 || true
  fi
  exit "${rc}"
}
trap on_exit EXIT

printf '\n=== QUIESCE WATCHER ONLY ===\n'
sv down "${SERVICE}"
WATCHER_DOWN=1
for _ in $(seq 1 20); do
  if sv status "${SERVICE}" 2>&1 | grep -q '^down:'; then
    break
  fi
  sleep 1
done
sv status "${SERVICE}" 2>&1 | grep -q '^down:' || {
  printf 'DEPLOY_ABORTED=WATCHER_DID_NOT_QUIESCE\n'
  exit 11
}
printf 'WATCHER_QUIESCED=PASS\n'

atomic_replace() {
  local path="$1" src="${STAGE}/${path}" dst="${ROOT}/${path}" tmp mode
  mode="$(stat -c '%a' "${dst}")"
  tmp="${dst}.deploy.$$"
  cp "${src}" "${tmp}"
  chmod "${mode}" "${tmp}"
  mv -f "${tmp}" "${dst}"
}

for path in "${PATHS[@]}"; do
  atomic_replace "${path}"
done
MUTATED=1

# Verify installed bytes are exactly the pinned Git objects.
for path in "${PATHS[@]}"; do
  expected_blob="$(git rev-parse "${SOURCE_COMMIT}:${path}")"
  actual_blob="$(git hash-object "${ROOT}/${path}")"
  [[ "${expected_blob}" == "${actual_blob}" ]] || {
    printf 'DEPLOY_ABORTED=INSTALLED_BLOB_MISMATCH:%s\n' "${path}"
    exit 12
  }
  printf 'INSTALLED_BLOB_PASS=%s:%s\n' "${path}" "${actual_blob}"
  printf 'POST_SHA256='; sha256sum "${ROOT}/${path}"
done

bash -n "${ROOT}/tools/run_signal_watcher_with_ledger.sh"
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); compile(p.read_text(encoding="utf-8"), str(p), "exec")' \
  "${ROOT}/tools/watcher_cycle_ledger.py"
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); compile(p.read_text(encoding="utf-8"), str(p), "exec")' \
  "${ROOT}/tools/supabase_publish.py"
printf 'INSTALLED_SYNTAX=PASS\n'

sv up "${SERVICE}"
WATCHER_DOWN=0
for _ in $(seq 1 20); do
  if sv status "${SERVICE}" 2>&1 | grep -q '^run:'; then
    break
  fi
  sleep 1
done
sv status "${SERVICE}" 2>&1 | grep -q '^run:' || {
  printf 'DEPLOY_ABORTED=WATCHER_DID_NOT_RESTART\n'
  exit 13
}
printf 'WATCHER_RESTART=PASS\n'

CONTROL_POST="$(python3 "${ROOT}/tools/control_plane_status.py")" || {
  printf 'DEPLOY_ABORTED=POST_CONTROL_PLANE_STATUS_FAILED\n'
  exit 14
}
printf '%s\n' "${CONTROL_POST}" > "${AUDIT}/control_plane_post.json"
printf '%s' "${CONTROL_POST}" | python3 -c '
import json,sys
x=json.load(sys.stdin)
assert x.get("manager_count")==1, x
assert x.get("owned")==7 and x.get("required")==7, x
assert x.get("running")==7, x
assert x.get("orphaned")==0, x
assert x.get("duplicate_service_rows")==0, x
' || {
  printf 'DEPLOY_ABORTED=POST_CONTROL_PLANE_NOT_EXACT\n'
  exit 15
}
printf 'CONTROL_PLANE_POST=PASS\n'

# File install is now accepted. Lack of a natural cycle is NOT a reason to
# restore known-bad observability; it remains an explicit live-proof state.
trap - EXIT
MUTATED=0
printf 'FILE_DEPLOYMENT_ACCEPTANCE=PASS\n'

printf '\n=== WAIT FOR NATURAL WATCHER CYCLE ===\n'
NEW_CYCLE=""
elapsed=0
while (( elapsed < WAIT_SECONDS )); do
  NEW_CYCLE="$(python3 - "${ROOT}/state/pipeline_progress.json" "${BASELINE_CYCLE}" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); baseline=sys.argv[2]
try:
    s=json.loads(p.read_text())
except Exception:
    print("")
else:
    x=s.get("last_terminal_outcome") or {}
    cid=x.get("cycle_id") or ""
    print(cid if cid and cid != baseline else "")
PY
)"
  [[ -n "${NEW_CYCLE}" ]] && break
  sleep 5
  elapsed=$((elapsed + 5))
done

if [[ -n "${NEW_CYCLE}" ]]; then
  printf 'NATURAL_WATCHER_CYCLE=PASS:%s\n' "${NEW_CYCLE}"
  python3 - "${ROOT}/state/pipeline_progress.json" "${NEW_CYCLE}" <<'PY'
import json, pathlib, sys
s=json.loads(pathlib.Path(sys.argv[1]).read_text()); cid=sys.argv[2]
last=s.get("last_terminal_outcome") or {}
print("NATURAL_TERMINAL_OUTCOME=" + str(last.get("terminal_outcome") or ""))
for key,value in sorted((s.get("decisions") or {}).items()):
    if value.get("cycle_id") == cid:
        print("DECISION=" + json.dumps({
            "key": key,
            "outcome": value.get("outcome"),
            "filter_rejected": value.get("filter_rejected"),
            "telegram_result": value.get("telegram_result"),
            "supabase_result": value.get("supabase_result"),
            "alerts_csv_persisted": value.get("alerts_csv_persisted"),
        }, sort_keys=True))
PY
else
  printf 'NATURAL_WATCHER_CYCLE=PENDING:no_new_terminal_cycle_within_%ss\n' "${WAIT_SECONDS}"
fi

printf '%s\n' \
  "DEPLOYED_RUNTIME_SOURCE=${SOURCE_COMMIT}" \
  'STRATEGY_CHANGED=NO' \
  'HISTORICAL_ALERTS_REWRITTEN=NO' \
  'OTHER_SERVICES_RESTARTED=NO' \
  "ROLLBACK_EXECUTED=${ROLLBACK_DONE}" \
  'OBSERVABILITY_TRUTH_PHONE_FILE_DEPLOY=PASS'
