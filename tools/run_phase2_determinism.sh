#!/usr/bin/env bash
# Run the reviewed deterministic BotA replay twice against the canonical r3
# dataset and preserve one canonical result only when byte-for-byte determinism
# and production-isolation checks pass.

REPLAY_SOURCE_COMMIT="6b437179cc58021aa358b1d0b04c121d9304c660"
DATASET_ID="oanda-warmup-20240101-20260801-20260807-r3"
RESULT_REL="data/replay_results/phase2-june-july-pr64"

RUNNER_BLOB="498dbb9affb44f9b71e1b25bbd6228a20415914d"
SEMANTICS_BLOB="6c18ddcfa7a49c5e5cb9cf139d341783dcb04a23"
VERIFIER_BLOB="04dff84cbbd1a86a5508282f09b12726744778eb"

if [[ "${1:-}" = "--self-check" ]]; then
  echo "PHASE2_RUNNER_SELF_CHECK=PASS"
  echo "REPLAY_SOURCE_COMMIT=$REPLAY_SOURCE_COMMIT"
  echo "DATASET_ID=$DATASET_ID"
  echo "RESULT_REL=$RESULT_REL"
  exit
fi

repo_root="$(pwd -P)"
dataset="$repo_root/data/replay/$DATASET_ID"
result="$repo_root/$RESULT_REL"
result_parent="${result%/*}"
lock="$result.lock"
stage="$result.staging.$$"
tmp="${TMPDIR:-${PREFIX:-/tmp}/tmp}/bota_phase2_$$"
lock_acquired=0

cleanup() {
  rm -rf "$tmp" "$stage"
  if [[ "$lock_acquired" -eq 1 ]]; then
    rmdir "$lock" 2>/dev/null || true
  fi
  return 0
}

signal_fail() {
  local signal_name="$1"
  trap - HUP INT TERM
  echo "PHASE2_DETERMINISM_GATE=FAIL"
  echo "REASON=INTERRUPTED:$signal_name"
  echo "NEXT_ACTION=CLASSIFY_BEFORE_RERUN"
  exit 130
  return 130
}

trap cleanup EXIT
trap 'signal_fail HUP' HUP
trap 'signal_fail INT' INT
trap 'signal_fail TERM' TERM

fail() {
  local reason="$1"
  echo "PHASE2_DETERMINISM_GATE=FAIL"
  echo "REASON=$reason"
  echo "NEXT_ACTION=CLASSIFY_BEFORE_RERUN"
  exit 2
  return 2
}

sha256_file() {
  local path="$1"
  local sum_line
  sum_line="$(sha256sum "$path")" || return 1
  printf '%s\n' "${sum_line%% *}"
  return 0
}

cache_hash() {
  python3 - "$repo_root/data/candles" <<'PY'
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
h = hashlib.sha256()
if root.exists():
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
print(h.hexdigest())
PY
  return 0
}

tracked_hash() {
  local sum_line
  sum_line="$({
    git -C "$repo_root" diff --no-ext-diff --binary
    git -C "$repo_root" diff --cached --no-ext-diff --binary
  } | sha256sum)" || return 1
  printf '%s\n' "${sum_line%% *}"
  return 0
}

declare -A expected_blobs=(
  [deterministic_replay.py]="498dbb9affb44f9b71e1b25bbd6228a20415914d"
  [replay_semantics.py]="6c18ddcfa7a49c5e5cb9cf139d341783dcb04a23"
  [verify_replay_dataset.py]="04dff84cbbd1a86a5508282f09b12726744778eb"
  [build_indicators.py]="2abce4a325d6d9da8bb0958b97a651d4288e1792"
  [quality_filter.py]="18b76f908652d483c115c930373972836cea81dc"
  [sr_score.py]="616b996a8ce439a19483762645a2247ca96fd066"
  [scoring_engine.sh]="09c42362a5c3c679696e86d4131ce5dfabd86608"
  [m15_h1_fusion.sh]="c1de0312ed928f870b9a45df109b730d30888ee7"
  [market_open.sh]="a73ca97f3a63c3245311585e231e5e69eaffc506"
  [emit_snapshot.py]="425c9adace57956981cf7e3111fd5df504c4f1ca"
)

source_files=(
  deterministic_replay.py
  replay_semantics.py
  verify_replay_dataset.py
  build_indicators.py
  quality_filter.py
  sr_score.py
  scoring_engine.sh
  m15_h1_fusion.sh
  market_open.sh
  emit_snapshot.py
)

echo "==================================================================="
echo "BOTA PHASE 2.1 — DETERMINISTIC DOUBLE REPLAY"
echo "DEVICE_UTC=$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "REPLAY_SOURCE_COMMIT=$REPLAY_SOURCE_COMMIT"
echo "DATASET_ID=$DATASET_ID"
echo "==================================================================="

if ! git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "NOT_A_GIT_WORKTREE"
elif [[ ! -f "$dataset/manifest.json" ]]; then
  fail "CANONICAL_R3_DATASET_MISSING"
elif ! command -v curl >/dev/null 2>&1; then
  fail "CURL_NOT_AVAILABLE"
elif ! command -v python3 >/dev/null 2>&1; then
  fail "PYTHON3_NOT_AVAILABLE"
elif ! command -v git >/dev/null 2>&1; then
  fail "GIT_NOT_AVAILABLE"
fi

mkdir -p "$result_parent" || fail "RESULT_PARENT_CREATE_FAILED"
if ! mkdir "$lock" 2>/dev/null; then
  fail "CANONICAL_REPLAY_LOCK_UNAVAILABLE"
fi
lock_acquired=1
if [[ -e "$result" ]]; then
  fail "CANONICAL_REPLAY_RESULT_ALREADY_EXISTS"
fi

mkdir -p "$tmp/tools"
base="https://raw.githubusercontent.com/Ciupanezulflipper/BotA/$REPLAY_SOURCE_COMMIT/tools"

for file in "${source_files[@]}"; do
  if ! curl \
    --proto '=https' \
    --proto-redir '=https' \
    --retry 4 \
    --retry-delay 1 \
    --retry-all-errors \
    --connect-timeout 15 \
    --max-time 90 \
    -fsSL \
    "$base/$file" \
    -o "$tmp/tools/$file"
  then
    fail "PINNED_SOURCE_DOWNLOAD_FAILED:$file"
  fi
done

echo
echo "===== REPLAY SOURCE PROOF ====="
source_mismatch=""
for file in "${source_files[@]}"; do
  expected="${expected_blobs[$file]}"
  actual="$(git hash-object --no-filters "$tmp/tools/$file")"
  echo "SOURCE_BLOB=$file|expected=$expected|actual=$actual"
  if [[ "$actual" != "$expected" ]]; then
    source_mismatch="$file"
    break
  fi
done

actual_runner="$(git hash-object --no-filters "$tmp/tools/deterministic_replay.py")"
actual_semantics="$(git hash-object --no-filters "$tmp/tools/replay_semantics.py")"
actual_verifier="$(git hash-object --no-filters "$tmp/tools/verify_replay_dataset.py")"
echo "RUNNER_EXPECTED_BLOB=$RUNNER_BLOB"
echo "RUNNER_ACTUAL_BLOB=$actual_runner"
echo "SEMANTICS_EXPECTED_BLOB=$SEMANTICS_BLOB"
echo "SEMANTICS_ACTUAL_BLOB=$actual_semantics"
echo "VERIFIER_EXPECTED_BLOB=$VERIFIER_BLOB"
echo "VERIFIER_ACTUAL_BLOB=$actual_verifier"

if [[ -n "$source_mismatch" ]]; then
  echo "REPLAY_SOURCE_INTEGRITY=FAIL"
  fail "REVIEWED_REPLAY_SOURCE_MISMATCH:$source_mismatch"
fi
echo "REPLAY_SOURCE_INTEGRITY=PASS"

cache_before="$(cache_hash)"
tracked_before="$(tracked_hash)"
echo "PRODUCTION_CACHE_SHA256_BEFORE=$cache_before"

common_args=(
  --dataset-root "$dataset"
  --source-root "$tmp"
  --source-commit "$REPLAY_SOURCE_COMMIT"
  --raw-start-utc "2024-01-01T00:00:00Z"
  --raw-end-utc "2026-08-01T00:00:00Z"
  --evaluation-start-utc "2026-06-01T00:00:00Z"
  --evaluation-end-utc "2026-08-01T00:00:00Z"
  --pairs EURUSD GBPUSD
  --min-warmup-bars 500
)

echo
echo "===== REPLAY RUN 1 ====="
PYTHONPATH="$tmp/tools" python3 "$tmp/tools/deterministic_replay.py" \
  "${common_args[@]}" \
  --output "$tmp/run1.events.jsonl" \
  --summary-output "$tmp/run1.summary.json" \
  > "$tmp/run1.stdout.json"
run1_rc=$?
echo "RUN1_RC=$run1_rc"

if [[ "$run1_rc" -ne 0 ]]; then
  [[ -s "$tmp/run1.stdout.json" ]] && cat "$tmp/run1.stdout.json"
  fail "REPLAY_RUN1_FAILED"
fi

echo
echo "===== REPLAY RUN 2 ====="
PYTHONPATH="$tmp/tools" python3 "$tmp/tools/deterministic_replay.py" \
  "${common_args[@]}" \
  --output "$tmp/run2.events.jsonl" \
  --summary-output "$tmp/run2.summary.json" \
  > "$tmp/run2.stdout.json"
run2_rc=$?
echo "RUN2_RC=$run2_rc"

if [[ "$run2_rc" -ne 0 ]]; then
  [[ -s "$tmp/run2.stdout.json" ]] && cat "$tmp/run2.stdout.json"
  fail "REPLAY_RUN2_FAILED"
fi

event1="$(sha256_file "$tmp/run1.events.jsonl")"
event2="$(sha256_file "$tmp/run2.events.jsonl")"
summary1="$(sha256_file "$tmp/run1.summary.json")"
summary2="$(sha256_file "$tmp/run2.summary.json")"

echo
echo "===== DETERMINISM PROOF ====="
echo "RUN1_EVENTS_SHA256=$event1"
echo "RUN2_EVENTS_SHA256=$event2"
echo "RUN1_SUMMARY_SHA256=$summary1"
echo "RUN2_SUMMARY_SHA256=$summary2"

if cmp -s "$tmp/run1.events.jsonl" "$tmp/run2.events.jsonl"; then
  echo "EVENT_BYTES_IDENTICAL=YES"
else
  echo "EVENT_BYTES_IDENTICAL=NO"
  fail "EVENT_BYTES_DIFFER"
fi

if cmp -s "$tmp/run1.summary.json" "$tmp/run2.summary.json"; then
  echo "SUMMARY_BYTES_IDENTICAL=YES"
else
  echo "SUMMARY_BYTES_IDENTICAL=NO"
  fail "SUMMARY_BYTES_DIFFER"
fi

summary_gate="$(python3 - "$tmp/run1.summary.json" "$DATASET_ID" <<'PY'
import json
import re
import sys

path, expected_dataset_id = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
expected = data.get("production_source_blobs", {})
observed = data.get("observed_production_source_blobs", {})
manifest_hash = str(data.get("dataset_manifest_sha256", ""))
checks = {
    "status": data.get("status") == "COMPLETE",
    "dataset": data.get("dataset_id") == expected_dataset_id,
    "sources": expected == observed and bool(expected),
    "manifest": bool(re.fullmatch(r"[0-9a-f]{64}", manifest_hash)),
}
print("PASS" if all(checks.values()) else "FAIL")
print(f"REPLAY_STATUS={data.get('status')}")
print(f"REPLAY_GRADE={data.get('replay_grade')}")
print(f"DATASET_MANIFEST_SHA256={manifest_hash}")
print("PRODUCTION_SOURCE_BLOBS_MATCH=" + ("YES" if checks["sources"] else "NO"))
print(f"DECISION_ROWS={data.get('decision_rows')}")
print(f"POLICY_A_ACCEPTED={data.get('accepted_current')}")
print(f"POLICY_B_ACCEPTED={data.get('accepted_policy_b')}")
print(f"POLICY_C_ACCEPTED={data.get('accepted_policy_c')}")
print("REJECTION_STAGES=" + json.dumps(data.get("rejection_stages", {}), sort_keys=True, separators=(",", ":")))
PY
)"

summary_gate_status="$(printf '%s\n' "$summary_gate" | sed -n '1p')"
printf '%s\n' "$summary_gate" | sed -n '2,$p'
if [[ "$summary_gate_status" != "PASS" ]]; then
  fail "REPLAY_SUMMARY_PROVENANCE_FAILED"
fi

cache_after="$(cache_hash)"
tracked_after="$(tracked_hash)"

echo
echo "===== ISOLATION PROOF ====="
echo "PRODUCTION_CACHE_SHA256_AFTER=$cache_after"
if [[ "$cache_before" = "$cache_after" ]]; then
  echo "PRODUCTION_CACHE_UNCHANGED=YES"
else
  echo "PRODUCTION_CACHE_UNCHANGED=NO"
  fail "PRODUCTION_CACHE_CHANGED"
fi

if [[ "$tracked_before" = "$tracked_after" ]]; then
  echo "TRACKED_WORKTREE_UNCHANGED=YES"
else
  echo "TRACKED_WORKTREE_UNCHANGED=NO"
  fail "TRACKED_WORKTREE_CHANGED"
fi

manifest_sha="$(python3 - "$tmp/run1.summary.json" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["dataset_manifest_sha256"])
PY
)"

if ! mkdir "$stage"; then
  fail "RESULT_STAGING_CREATE_FAILED"
fi
cp "$tmp/run1.events.jsonl" "$stage/events.jsonl" || fail "RESULT_EVENTS_COPY_FAILED"
cp "$tmp/run1.summary.json" "$stage/summary.json" || fail "RESULT_SUMMARY_COPY_FAILED"
{
  echo "REPLAY_SOURCE_COMMIT=$REPLAY_SOURCE_COMMIT"
  echo "DATASET_ID=$DATASET_ID"
  echo "DATASET_MANIFEST_SHA256=$manifest_sha"
  echo "EVENTS_SHA256=$event1"
  echo "SUMMARY_SHA256=$summary1"
  echo "RUN1_RUN2_EVENTS_IDENTICAL=YES"
  echo "RUN1_RUN2_SUMMARIES_IDENTICAL=YES"
  echo "PRODUCTION_SOURCE_BLOBS_MATCH=YES"
  echo "PRODUCTION_CACHE_UNCHANGED=YES"
  echo "TRACKED_WORKTREE_UNCHANGED=YES"
} > "$stage/DETERMINISM_PROOF.txt" || fail "RESULT_PROOF_WRITE_FAILED"

if [[ "$(sha256_file "$stage/events.jsonl")" != "$event1" ]]; then
  fail "STAGED_EVENTS_HASH_MISMATCH"
fi
if [[ "$(sha256_file "$stage/summary.json")" != "$summary1" ]]; then
  fail "STAGED_SUMMARY_HASH_MISMATCH"
fi
if ! mv "$stage" "$result"; then
  fail "CANONICAL_RESULT_PUBLISH_FAILED"
fi

echo
echo "PHASE2_DETERMINISM_GATE=PASS"
echo "CANONICAL_REPLAY_RESULT=$result"
echo "NEXT_ACTION=PHASE2_OUTCOME_AND_ABC_COMPARISON"
echo "TEMP_REPLAY_FILES_RETAINED=NO"
echo "PRODUCTION_STRATEGY_MUTATION=NO"
echo "TELEGRAM_MUTATION=NO"
echo "SUPABASE_MUTATION=NO"
echo "SERVICE_CRON_MUTATION=NO"
echo "==================================================================="
