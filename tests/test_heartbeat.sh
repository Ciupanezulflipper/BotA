#!/usr/bin/env bash
# tests/test_heartbeat.sh
# Offline test suite for tools/heartbeat.sh.
# Uses a PATH-injected fake curl — no real network requests are made.
#
# Run: bash tests/test_heartbeat.sh
# Exit code: 0 if all tests pass, 1 if any fail.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HEARTBEAT="${REPO_ROOT}/tools/heartbeat.sh"
SYSTEM_PATH="${PATH}"

PASS_COUNT=0
FAIL_COUNT=0
FAIL_NAMES=()
TEST_NUM=0

# Per-call fake curl overrides (cleared between tests via run_heartbeat reset)
FAKE_CURL_RESPONSE_1=""
FAKE_CURL_HTTP_CODE_1=""
FAKE_CURL_EXIT_CODE_1=""
FAKE_CURL_RESPONSE_2=""
FAKE_CURL_HTTP_CODE_2=""
FAKE_CURL_EXIT_CODE_2=""

# ── Helpers ────────────────────────────────────────────────────────────────────

pass() {
  PASS_COUNT=$(( PASS_COUNT + 1 ))
  printf '  [PASS] %s\n' "$1"
}

fail() {
  FAIL_COUNT=$(( FAIL_COUNT + 1 ))
  FAIL_NAMES+=("$1")
  printf '  [FAIL] %s\n' "$1"
}

assert_contains() {
  local label="$1" haystack="$2" needle="$3"
  if printf '%s' "${haystack}" | grep -qF "${needle}"; then
    pass "${label}"
  else
    fail "${label} — expected '${needle}' not found"
  fi
}

assert_not_contains() {
  local label="$1" haystack="$2" needle="$3"
  if ! printf '%s' "${haystack}" | grep -qF "${needle}"; then
    pass "${label}"
  else
    fail "${label} — unexpected '${needle}' found"
  fi
}

assert_file_exists() {
  local label="$1" path="$2"
  if [[ -f "${path}" ]]; then pass "${label}"; else fail "${label} — file missing: ${path}"; fi
}

assert_file_missing() {
  local label="$1" path="$2"
  if [[ ! -f "${path}" ]]; then pass "${label}"; else fail "${label} — file should not exist: ${path}"; fi
}

start_test() {
  TEST_NUM=$(( TEST_NUM + 1 ))
  printf '\nTest %02d: %s\n' "${TEST_NUM}" "$1"
}

# ── Environment setup ──────────────────────────────────────────────────────────
# Each test creates its own isolated BOTA_ROOT under a temp dir.
# A shared fake_curl dir holds the fake curl binary; behaviour is controlled
# via env vars FAKE_CURL_RESPONSE, FAKE_CURL_HTTP_CODE, FAKE_CURL_EXIT_CODE
# (default for all calls) and FAKE_CURL_RESPONSE_1/2, FAKE_CURL_HTTP_CODE_1/2,
# FAKE_CURL_EXIT_CODE_1/2 (per-call overrides: 1=first call, 2=second call).

FAKE_DIR="$(mktemp -d)"
FAKE_CURL="${FAKE_DIR}/curl"

cat > "${FAKE_CURL}" << 'FAKECURL'
#!/usr/bin/env bash
# Fake curl: parses --output FILE from args, writes response body there,
# writes HTTP code to stdout (captured by --write-out), exits with
# configured exit code.  Also records call count and env dump for tests.
#
# Per-call overrides (FAKE_CURL_RESPONSE_1/2, etc.) take priority over
# the global FAKE_CURL_RESPONSE/HTTP_CODE/EXIT_CODE defaults.

COUNTER_FILE="${FAKE_CURL_DIR}/call_count"
ENV_DUMP_FILE="${FAKE_CURL_DIR}/env_dump"

count=$(cat "${COUNTER_FILE}" 2>/dev/null || printf '0')
count=$(( count + 1 ))
printf '%d\n' "${count}" > "${COUNTER_FILE}"

# Dump environment for scope-leak inspection
env > "${ENV_DUMP_FILE}"

# Resolve per-call overrides, falling back to global defaults
case "${count}" in
  1)
    effective_response="${FAKE_CURL_RESPONSE_1:-}"
    effective_http_code="${FAKE_CURL_HTTP_CODE_1:-}"
    effective_exit_code="${FAKE_CURL_EXIT_CODE_1:-}"
    ;;
  2)
    effective_response="${FAKE_CURL_RESPONSE_2:-}"
    effective_http_code="${FAKE_CURL_HTTP_CODE_2:-}"
    effective_exit_code="${FAKE_CURL_EXIT_CODE_2:-}"
    ;;
  *)
    effective_response=""
    effective_http_code=""
    effective_exit_code=""
    ;;
esac
if [[ -z "${effective_response}" ]]; then
  effective_response="${FAKE_CURL_RESPONSE:-}"
  [[ -z "${effective_response}" ]] && effective_response='{"ok":true}'
fi
[[ -z "${effective_http_code}" ]] && effective_http_code="${FAKE_CURL_HTTP_CODE:-200}"
[[ -z "${effective_exit_code}" ]] && effective_exit_code="${FAKE_CURL_EXIT_CODE:-0}"

# Parse --output <file> from positional args
output_file=""
prev=""
for arg in "$@"; do
  if [[ "${prev}" == "--output" ]]; then
    output_file="${arg}"
  fi
  prev="${arg}"
done

# Write response body to --output file
if [[ -n "${output_file}" ]]; then
  printf '%s' "${effective_response}" > "${output_file}"
fi

# Write HTTP code to stdout (mirrors --write-out '%{http_code}')
printf '%s' "${effective_http_code}"

exit "${effective_exit_code}"
FAKECURL
chmod +x "${FAKE_CURL}"

export FAKE_CURL_DIR="${FAKE_DIR}"

cleanup_all() {
  rm -rf "${FAKE_DIR}"
}
trap cleanup_all EXIT

# ── Per-test helpers ───────────────────────────────────────────────────────────

new_bota_root() {
  local td
  td="$(mktemp -d)"
  mkdir -p "${td}/BotA/logs/state"
  printf '%s' "${td}/BotA"
}

write_env_runtime() {
  local root="$1"
  cat > "${root}/.env.runtime" << 'ENV'
TELEGRAM_BOT_TOKEN=TESTTOKEN_FAKE123
TELEGRAM_CHAT_ID=TESTCHATID_FAKE456
EXTRA_SECRET=SHOULDNOTEXPORT999
ENV
}

write_stale_shadow() {
  local root="$1"
  local stale_ts
  stale_ts="$(python3 -c "
import datetime
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)
print(t.strftime('%Y-%m-%dT%H:%M:%S+00:00'))
")"
  printf '%s|bota|stale_test\n' "${stale_ts}" > "${root}/logs/shadow_manager_heartbeat.txt"
}

write_fresh_shadow() {
  local root="$1"
  local fresh_ts
  fresh_ts="$(python3 -c "
import datetime
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
print(t.strftime('%Y-%m-%dT%H:%M:%S+00:00'))
")"
  printf '%s|bota|fresh_test\n' "${fresh_ts}" > "${root}/logs/shadow_manager_heartbeat.txt"
}

# Writes a shadow file with the exact format produced by be_shadow_manager.py:
#   datetime.now(timezone.utc).astimezone(timezone.utc).isoformat()
# → YYYY-MM-DDTHH:MM:SS.ffffff+00:00
write_canonical_shadow() {
  local root="$1"
  local ts
  ts="$(python3 -c "
import datetime
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
print(t.astimezone(datetime.timezone.utc).isoformat())
")"
  printf '%s | OK | canonical_test\n' "${ts}" > "${root}/logs/shadow_manager_heartbeat.txt"
}

write_invalid_shadow() {
  local root="$1"
  printf 'NOT_A_TIMESTAMP|bota|invalid_test\n' > "${root}/logs/shadow_manager_heartbeat.txt"
}

write_future_shadow() {
  local root="$1"
  local seconds_ahead="${2:-600}"
  local future_ts
  future_ts="$(python3 -c "
import datetime
t = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=${seconds_ahead})
print(t.strftime('%Y-%m-%dT%H:%M:%S+00:00'))
")"
  printf '%s|bota|future_test\n' "${future_ts}" > "${root}/logs/shadow_manager_heartbeat.txt"
}

write_empty_timestamp_shadow() {
  local root="$1"
  printf '|bota|empty_timestamp_test\n' > "${root}/logs/shadow_manager_heartbeat.txt"
}

run_heartbeat() {
  local root="$1"
  HEARTBEAT_STDOUT=""
  HEARTBEAT_STDERR=""
  HEARTBEAT_EXIT=0
  HEARTBEAT_LOG=""

  rm -f "${FAKE_DIR}/call_count" "${FAKE_DIR}/env_dump"

  local stderr_file
  stderr_file="$(mktemp)"

  local _fcr; _fcr="${FAKE_CURL_RESPONSE:-}"
  [[ -z "${_fcr}" ]] && _fcr='{"ok":true}'

  set +e
  HEARTBEAT_STDOUT="$(
    BOTA_ROOT="${root}" \
    HOME="${root%/BotA}" \
    FAKE_CURL_RESPONSE="${_fcr}" \
    FAKE_CURL_HTTP_CODE="${FAKE_CURL_HTTP_CODE:-200}" \
    FAKE_CURL_EXIT_CODE="${FAKE_CURL_EXIT_CODE:-0}" \
    FAKE_CURL_RESPONSE_1="${FAKE_CURL_RESPONSE_1:-}" \
    FAKE_CURL_HTTP_CODE_1="${FAKE_CURL_HTTP_CODE_1:-}" \
    FAKE_CURL_EXIT_CODE_1="${FAKE_CURL_EXIT_CODE_1:-}" \
    FAKE_CURL_RESPONSE_2="${FAKE_CURL_RESPONSE_2:-}" \
    FAKE_CURL_HTTP_CODE_2="${FAKE_CURL_HTTP_CODE_2:-}" \
    FAKE_CURL_EXIT_CODE_2="${FAKE_CURL_EXIT_CODE_2:-}" \
    FAKE_CURL_DIR="${FAKE_DIR}" \
    PATH="${FAKE_DIR}:${SYSTEM_PATH}" \
    bash "${HEARTBEAT}" 2>"${stderr_file}"
  )"
  HEARTBEAT_EXIT=$?
  set -e

  HEARTBEAT_STDERR="$(cat "${stderr_file}" 2>/dev/null || true)"
  rm -f "${stderr_file}"
  HEARTBEAT_LOG="$(cat "${root}/logs/cron.heartbeat.log" 2>/dev/null || true)"
}

# ── Tests ──────────────────────────────────────────────────────────────────────

# Test 01 — Successful Telegram response + fresh shadow → PASS + HEALTHY
start_test "Successful Telegram response with fresh shadow"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_fresh_shadow "${BR}"
  FAKE_CURL_RESPONSE='{"ok":true,"result":{}}' \
  FAKE_CURL_HTTP_CODE=200 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "stdout contains HEARTBEAT_RESULT=PASS" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "log contains HEARTBEAT_RESULT=PASS"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_RESULT=HEALTHY in stdout"      "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=HEALTHY"
  assert_contains "DEADMAN_RESULT=HEALTHY in log"         "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=HEALTHY"
  rm -rf "${BR%/BotA}"
}

# Test 02 — Telegram API rejection → HEARTBEAT_RESULT=FAIL_TELEGRAM_API
start_test "Telegram API rejection (ok:false)"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='{"ok":false,"error_code":400,"description":"Bad Request"}' \
  FAKE_CURL_HTTP_CODE=200 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "stdout FAIL_TELEGRAM_API" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  assert_contains "log FAIL_TELEGRAM_API"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  rm -rf "${BR%/BotA}"
}

# Test 03 — HTTP rejection (401) → HEARTBEAT_RESULT=FAIL_HTTP
start_test "HTTP rejection (HTTP 401)"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='Unauthorized' \
  FAKE_CURL_HTTP_CODE=401 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "stdout FAIL_HTTP" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_HTTP"
  assert_contains "log FAIL_HTTP"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_HTTP"
  rm -rf "${BR%/BotA}"
}

# Test 04 — Transport failure (curl rc=7) → HEARTBEAT_RESULT=FAIL_TRANSPORT
start_test "Transport failure (curl exit 7)"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='' \
  FAKE_CURL_HTTP_CODE=000 \
  FAKE_CURL_EXIT_CODE=7 \
  run_heartbeat "${BR}"
  assert_contains "stdout FAIL_TRANSPORT" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TRANSPORT"
  assert_contains "log FAIL_TRANSPORT"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_TRANSPORT"
  rm -rf "${BR%/BotA}"
}

# Test 05 — Missing .env.runtime → FAIL_ENV_RUNTIME_MISSING, no network attempt
start_test "Missing .env.runtime"
{
  BR="$(new_bota_root)"
  # Do NOT write .env.runtime
  run_heartbeat "${BR}"
  assert_contains "stdout FAIL_ENV_RUNTIME_MISSING" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_ENV_RUNTIME_MISSING"
  assert_contains "log FAIL_ENV_RUNTIME_MISSING"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_ENV_RUNTIME_MISSING"
  t05_call_count="$(cat "${FAKE_DIR}/call_count" 2>/dev/null || printf '0')"
  if [[ "${t05_call_count}" == "0" ]]; then pass "curl not called when env missing"
  else fail "curl was called despite missing env (count=${t05_call_count})"; fi
  rm -rf "${BR%/BotA}"
}

# Test 06 — Missing TELEGRAM_BOT_TOKEN → FAIL_TELEGRAM_VARIABLES_MISSING, no network
start_test "Missing TELEGRAM_BOT_TOKEN"
{
  BR="$(new_bota_root)"
  printf 'TELEGRAM_CHAT_ID=ONLYCHATID\n' > "${BR}/.env.runtime"
  run_heartbeat "${BR}"
  assert_contains "stdout FAIL_TELEGRAM_VARIABLES_MISSING" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TELEGRAM_VARIABLES_MISSING"
  t06_call_count="$(cat "${FAKE_DIR}/call_count" 2>/dev/null || printf '0')"
  if [[ "${t06_call_count}" == "0" ]]; then pass "curl not called when token missing"
  else fail "curl was called despite missing token"; fi
  rm -rf "${BR%/BotA}"
}

# Test 07 — Missing TELEGRAM_CHAT_ID → FAIL_TELEGRAM_VARIABLES_MISSING, no network
start_test "Missing TELEGRAM_CHAT_ID"
{
  BR="$(new_bota_root)"
  printf 'TELEGRAM_BOT_TOKEN=ONLYTOKEN\n' > "${BR}/.env.runtime"
  run_heartbeat "${BR}"
  assert_contains "stdout FAIL_TELEGRAM_VARIABLES_MISSING" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TELEGRAM_VARIABLES_MISSING"
  t07_call_count="$(cat "${FAKE_DIR}/call_count" 2>/dev/null || printf '0')"
  if [[ "${t07_call_count}" == "0" ]]; then pass "curl not called when chat_id missing"
  else fail "curl was called despite missing chat_id"; fi
  rm -rf "${BR%/BotA}"
}

# Test 08 — Stale shadow heartbeat → DEADMAN_RESULT=ALERT_SENT, flag created
start_test "Stale shadow heartbeat triggers deadman alert"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_stale_shadow "${BR}"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "DEADMAN_RESULT=ALERT_SENT in stdout" "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=ALERT_SENT"
  assert_contains "DEADMAN_RESULT=ALERT_SENT in log"    "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=ALERT_SENT"
  assert_file_exists "deadman.flag created" "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 09 — Repeated stale invocation → DEADMAN_RESULT=ALREADY_ALERTED, no duplicate
start_test "Repeated stale invocation suppresses duplicate deadman"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_stale_shadow "${BR}"
  # Pre-create the deadman flag
  printf 'prior deadman alert\n' > "${BR}/logs/state/deadman.flag"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "DEADMAN_RESULT=ALREADY_ALERTED in stdout" "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=ALREADY_ALERTED"
  assert_contains "DEADMAN_RESULT=ALREADY_ALERTED in log"    "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=ALREADY_ALERTED"
  assert_file_exists "deadman.flag still exists (no removal)" "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 10 — Recovery: fresh shadow + existing flag → DEADMAN_RESULT=RECOVERY_SENT, flag removed
start_test "Recovery: fresh shadow removes deadman flag"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_fresh_shadow "${BR}"
  printf 'old deadman alert\n' > "${BR}/logs/state/deadman.flag"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "DEADMAN_RESULT=RECOVERY_SENT in stdout" "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=RECOVERY_SENT"
  assert_contains "DEADMAN_RESULT=RECOVERY_SENT in log"    "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=RECOVERY_SENT"
  assert_file_missing "deadman.flag removed" "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 11 — Healthy state: fresh shadow, no prior deadman → DEADMAN_RESULT=HEALTHY
start_test "Healthy state with fresh shadow and no prior deadman"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_fresh_shadow "${BR}"
  # No deadman flag
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS"    "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_RESULT=HEALTHY stdout" "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=HEALTHY"
  assert_contains "DEADMAN_RESULT=HEALTHY log"    "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=HEALTHY"
  assert_file_missing "no deadman flag created" "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 12 — Secret safety: token/chatid/unrelated vars absent from logs and env
start_test "Secret safety: token and chat ID not in logs or stdout/stderr"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"

  # Token must not appear in log, stdout, or stderr
  assert_not_contains "token absent from log"    "${HEARTBEAT_LOG}"    "TESTTOKEN_FAKE123"
  assert_not_contains "token absent from stdout" "${HEARTBEAT_STDOUT}" "TESTTOKEN_FAKE123"
  assert_not_contains "token absent from stderr" "${HEARTBEAT_STDERR}" "TESTTOKEN_FAKE123"

  # Chat ID must not appear in log
  assert_not_contains "chat_id absent from log" "${HEARTBEAT_LOG}" "TESTCHATID_FAKE456"

  # EXTRA_SECRET from .env.runtime must not be in fake curl's environment
  t12_env_dump="$(cat "${FAKE_DIR}/env_dump" 2>/dev/null || true)"
  assert_not_contains "EXTRA_SECRET not in curl env" "${t12_env_dump}" "SHOULDNOTEXPORT999"

  rm -rf "${BR%/BotA}"
}

# Test 13 — Shell syntax: bash -n passes
start_test "Shell syntax validation (bash -n)"
{
  t13_rc=0
  t13_out="$(bash -n "${HEARTBEAT}" 2>&1)" || t13_rc=$?
  if [[ "${t13_rc}" -eq 0 ]]; then
    pass "bash -n exit 0"
  else
    fail "bash -n failed: ${t13_out}"
  fi
}

# Test 14 — Regression: v3.2 features and security constraints present in source
start_test "Regression: v3.2 features and security constraints present in source"
{
  t14_src="$(cat "${HEARTBEAT}")"
  if printf '%s' "${t14_src}" | grep -qF 'DEADMAN_RESULT=ALERT_SENT'; then
    pass "DEADMAN_RESULT=ALERT_SENT present"
  else
    fail "DEADMAN_RESULT=ALERT_SENT missing from source"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'DEADMAN_RESULT=RECOVERY_SENT'; then
    pass "DEADMAN_RESULT=RECOVERY_SENT present"
  else
    fail "DEADMAN_RESULT=RECOVERY_SENT missing from source"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'DEADMAN_FLAG'; then
    pass "DEADMAN_FLAG referenced in source"
  else
    fail "DEADMAN_FLAG missing from source"
  fi
  if printf '%s' "${t14_src}" | grep -qF '_load_telegram_creds'; then
    pass "scoped credential loader present"
  else
    fail "scoped credential loader missing"
  fi
  if ! printf '%s' "${t14_src}" | grep -qF 'set -a'; then
    pass "set -a (env export leak) absent"
  else
    fail "set -a found — scoped loading may not be in effect"
  fi
  if ! printf '%s' "${t14_src}" | grep -qF 'config/tele.env'; then
    pass "obsolete config/tele.env path absent"
  else
    fail "obsolete config/tele.env path still present"
  fi
  if printf '%s' "${t14_src}" | grep -qF '_send_telegram'; then
    pass "_send_telegram shared function present"
  else
    fail "_send_telegram shared function missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'TGSEND_PASS'; then
    pass "TGSEND_PASS result marker present"
  else
    fail "TGSEND_PASS result marker missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'DEADMAN_DELIVERY_FAILED'; then
    pass "DEADMAN_DELIVERY_FAILED marker present"
  else
    fail "DEADMAN_DELIVERY_FAILED marker missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'RECOVERY_DELIVERY_FAILED'; then
    pass "RECOVERY_DELIVERY_FAILED marker present"
  else
    fail "RECOVERY_DELIVERY_FAILED marker missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'INVALID_SHADOW_TIMESTAMP'; then
    pass "INVALID_SHADOW_TIMESTAMP marker present"
  else
    fail "INVALID_SHADOW_TIMESTAMP marker missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'FUTURE_SHADOW_TIMESTAMP'; then
    pass "FUTURE_SHADOW_TIMESTAMP marker present"
  else
    fail "FUTURE_SHADOW_TIMESTAMP marker missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'CLOCK_JITTER_TOLERANCE_SEC'; then
    pass "CLOCK_JITTER_TOLERANCE_SEC constant present"
  else
    fail "CLOCK_JITTER_TOLERANCE_SEC constant missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'parse_mode=HTML'; then
    pass "parse_mode=HTML present in source"
  else
    fail "parse_mode=HTML missing from source"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'disable_web_page_preview'; then
    pass "disable_web_page_preview present in source"
  else
    fail "disable_web_page_preview missing from source"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'SHADOW_HEARTBEAT_MISSING'; then
    pass "SHADOW_HEARTBEAT_MISSING marker present"
  else
    fail "SHADOW_HEARTBEAT_MISSING marker missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF 'SHADOW_TIMESTAMP_MISSING'; then
    pass "SHADOW_TIMESTAMP_MISSING marker present"
  else
    fail "SHADOW_TIMESTAMP_MISSING marker missing"
  fi
  if printf '%s' "${t14_src}" | grep -qF "json.load"; then
    pass "json.load (deterministic JSON parser) present"
  else
    fail "json.load missing — JSON ok validation may be unreliable"
  fi
  if ! printf '%s' "${t14_src}" | grep -qF "grep -qF '\"ok\":true'"; then
    pass "grep-based ok check removed"
  else
    fail "grep-based ok check still present"
  fi
}

# Test 15 — Deadman delivery failure: flag NOT created when alert curl fails
start_test "Deadman delivery failure: flag not created on send failure"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_stale_shadow "${BR}"
  # Call 1 (heartbeat): success; Call 2 (deadman alert): transport failure
  FAKE_CURL_RESPONSE_1='{"ok":true}' \
  FAKE_CURL_HTTP_CODE_1=200 \
  FAKE_CURL_EXIT_CODE_1=0 \
  FAKE_CURL_RESPONSE_2='' \
  FAKE_CURL_HTTP_CODE_2=000 \
  FAKE_CURL_EXIT_CODE_2=7 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"          "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_DELIVERY_FAILED in stdout"        "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=DEADMAN_DELIVERY_FAILED"
  assert_contains "DEADMAN_DELIVERY_FAILED in log"           "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=DEADMAN_DELIVERY_FAILED"
  assert_file_missing "deadman.flag not created on failure"  "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 16 — Deadman retry after prior delivery failure: flag created on success
start_test "Deadman retry succeeds: flag created when both calls succeed"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_stale_shadow "${BR}"
  # No pre-existing flag (prior run had DEADMAN_DELIVERY_FAILED)
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"   "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_RESULT=ALERT_SENT stdout"  "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=ALERT_SENT"
  assert_file_exists "deadman.flag created on retry"  "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 17 — Recovery delivery failure: flag retained when recovery curl fails
start_test "Recovery delivery failure: flag retained on send failure"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_fresh_shadow "${BR}"
  printf 'prior deadman alert\n' > "${BR}/logs/state/deadman.flag"
  # Call 1 (heartbeat): success; Call 2 (recovery): transport failure
  FAKE_CURL_RESPONSE_1='{"ok":true}' \
  FAKE_CURL_HTTP_CODE_1=200 \
  FAKE_CURL_EXIT_CODE_1=0 \
  FAKE_CURL_RESPONSE_2='' \
  FAKE_CURL_HTTP_CODE_2=000 \
  FAKE_CURL_EXIT_CODE_2=7 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"           "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "RECOVERY_DELIVERY_FAILED in stdout"        "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=RECOVERY_DELIVERY_FAILED"
  assert_contains "RECOVERY_DELIVERY_FAILED in log"           "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=RECOVERY_DELIVERY_FAILED"
  assert_file_exists "deadman.flag retained on failure"       "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 18 — Recovery retry after prior failure: flag removed on success
start_test "Recovery retry succeeds: flag removed when both calls succeed"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_fresh_shadow "${BR}"
  # Flag still exists from prior RECOVERY_DELIVERY_FAILED run
  printf 'prior deadman alert\n' > "${BR}/logs/state/deadman.flag"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"    "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_RESULT=RECOVERY_SENT"       "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=RECOVERY_SENT"
  assert_file_missing "deadman.flag removed on retry"  "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 19 — Invalid shadow timestamp: INVALID_SHADOW_TIMESTAMP, no flag, one curl call
start_test "Invalid shadow timestamp: no stale alert, no flag mutation"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_invalid_shadow "${BR}"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"         "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "INVALID_SHADOW_TIMESTAMP in stdout"      "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=INVALID_SHADOW_TIMESTAMP"
  assert_contains "INVALID_SHADOW_TIMESTAMP in log"         "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=INVALID_SHADOW_TIMESTAMP"
  assert_file_missing "no flag created for invalid ts"      "${BR}/logs/state/deadman.flag"
  t19_call_count="$(cat "${FAKE_DIR}/call_count" 2>/dev/null || printf '0')"
  if [[ "${t19_call_count}" == "1" ]]; then pass "exactly one curl call (heartbeat only)"
  else fail "expected 1 curl call, got ${t19_call_count}"; fi
  rm -rf "${BR%/BotA}"
}

# Test 20 — Future timestamp beyond tolerance: FUTURE_SHADOW_TIMESTAMP, flag not mutated
start_test "Future timestamp beyond tolerance: FUTURE_SHADOW_TIMESTAMP, flag unchanged"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_future_shadow "${BR}" 600   # 600s ahead, beyond 300s tolerance
  printf 'existing deadman alert\n' > "${BR}/logs/state/deadman.flag"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"         "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "FUTURE_SHADOW_TIMESTAMP in stdout"       "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=FUTURE_SHADOW_TIMESTAMP"
  assert_contains "FUTURE_SHADOW_TIMESTAMP in log"          "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=FUTURE_SHADOW_TIMESTAMP"
  assert_file_exists "deadman.flag not mutated"             "${BR}/logs/state/deadman.flag"
  t20_call_count="$(cat "${FAKE_DIR}/call_count" 2>/dev/null || printf '0')"
  if [[ "${t20_call_count}" == "1" ]]; then pass "exactly one curl call (heartbeat only)"
  else fail "expected 1 curl call, got ${t20_call_count}"; fi
  rm -rf "${BR%/BotA}"
}

# Test 21 — Future timestamp within tolerance (60s): treated as age=0, HEALTHY
start_test "Future timestamp within tolerance (60s ahead): HEALTHY, no FUTURE_SHADOW_TIMESTAMP"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_future_shadow "${BR}" 60   # 60s ahead, within 300s tolerance
  # No pre-existing flag
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"              "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_RESULT=HEALTHY in stdout"             "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=HEALTHY"
  assert_not_contains "no FUTURE_SHADOW_TIMESTAMP in stdout"     "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=FUTURE_SHADOW_TIMESTAMP"
  assert_file_missing "no flag created"                          "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 22 — Missing shadow file → SHADOW_HEARTBEAT_MISSING (not HEALTHY)
start_test "Missing shadow file: SHADOW_HEARTBEAT_MISSING, no flag mutation"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  # Deliberately no shadow file
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"              "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "SHADOW_HEARTBEAT_MISSING in stdout"           "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=SHADOW_HEARTBEAT_MISSING"
  assert_contains "SHADOW_HEARTBEAT_MISSING in log"              "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=SHADOW_HEARTBEAT_MISSING"
  assert_not_contains "not classified as HEALTHY"                "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=HEALTHY"
  assert_file_missing "no flag created"                          "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 23 — Shadow file present but timestamp field empty → SHADOW_TIMESTAMP_MISSING
start_test "Shadow file with empty timestamp: SHADOW_TIMESTAMP_MISSING, no flag mutation"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_empty_timestamp_shadow "${BR}"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"              "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "SHADOW_TIMESTAMP_MISSING in stdout"           "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=SHADOW_TIMESTAMP_MISSING"
  assert_contains "SHADOW_TIMESTAMP_MISSING in log"              "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=SHADOW_TIMESTAMP_MISSING"
  assert_not_contains "not classified as HEALTHY"                "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=HEALTHY"
  assert_file_missing "no flag created"                          "${BR}/logs/state/deadman.flag"
  rm -rf "${BR%/BotA}"
}

# Test 24 — JSON with whitespace around boolean: {"ok": true} → PASS
start_test "JSON ok field with whitespace: {\"ok\": true} succeeds"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_fresh_shadow "${BR}"
  FAKE_CURL_RESPONSE='{"ok": true, "result": {}}' \
  FAKE_CURL_HTTP_CODE=200 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"    "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "HEARTBEAT_RESULT=PASS in log"       "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_RESULT=HEALTHY in stdout"   "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=HEALTHY"
  rm -rf "${BR%/BotA}"
}

# Test 25 — Malformed JSON response → FAIL_TELEGRAM_API
start_test "Malformed JSON response: FAIL_TELEGRAM_API"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='not json at all' \
  FAKE_CURL_HTTP_CODE=200 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "FAIL_TELEGRAM_API in stdout" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  assert_contains "FAIL_TELEGRAM_API in log"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  rm -rf "${BR%/BotA}"
}

# Test 26 — JSON missing ok field → FAIL_TELEGRAM_API
start_test "JSON missing ok field: FAIL_TELEGRAM_API"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='{"result":{},"description":"missing ok"}' \
  FAKE_CURL_HTTP_CODE=200 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "FAIL_TELEGRAM_API in stdout" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  assert_contains "FAIL_TELEGRAM_API in log"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  rm -rf "${BR%/BotA}"
}

# Test 27 — ok is string "true" (not boolean) → FAIL_TELEGRAM_API
start_test "JSON ok is string true (not boolean): FAIL_TELEGRAM_API"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='{"ok":"true"}' \
  FAKE_CURL_HTTP_CODE=200 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "FAIL_TELEGRAM_API in stdout" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  assert_contains "FAIL_TELEGRAM_API in log"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  rm -rf "${BR%/BotA}"
}

# Test 28 — ok is boolean false → FAIL_TELEGRAM_API
start_test "JSON ok is boolean false: FAIL_TELEGRAM_API"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  FAKE_CURL_RESPONSE='{"ok":false,"error_code":401,"description":"Unauthorized"}' \
  FAKE_CURL_HTTP_CODE=200 \
  FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "FAIL_TELEGRAM_API in stdout" "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  assert_contains "FAIL_TELEGRAM_API in log"    "${HEARTBEAT_LOG}"    "HEARTBEAT_RESULT=FAIL_TELEGRAM_API"
  rm -rf "${BR%/BotA}"
}

# Test 29 — Canonical shadow timestamp (Python isoformat with microseconds +00:00)
start_test "Canonical shadow timestamp YYYY-MM-DDTHH:MM:SS.ffffff+00:00 parses correctly"
{
  BR="$(new_bota_root)"
  write_env_runtime "${BR}"
  write_canonical_shadow "${BR}"
  FAKE_CURL_RESPONSE='{"ok":true}' FAKE_CURL_HTTP_CODE=200 FAKE_CURL_EXIT_CODE=0 \
  run_heartbeat "${BR}"
  assert_contains "HEARTBEAT_RESULT=PASS in stdout"       "${HEARTBEAT_STDOUT}" "HEARTBEAT_RESULT=PASS"
  assert_contains "DEADMAN_RESULT=HEALTHY in stdout"      "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=HEALTHY"
  assert_contains "DEADMAN_RESULT=HEALTHY in log"         "${HEARTBEAT_LOG}"    "DEADMAN_RESULT=HEALTHY"
  assert_not_contains "no INVALID_SHADOW_TIMESTAMP"       "${HEARTBEAT_STDOUT}" "DEADMAN_RESULT=INVALID_SHADOW_TIMESTAMP"
  rm -rf "${BR%/BotA}"
}

# ── Summary ────────────────────────────────────────────────────────────────────

printf '\n═══════════════════════════════════════════════════════════\n'
printf 'HEARTBEAT TEST SUMMARY\n'
printf '  Total tests defined: %d\n' "${TEST_NUM}"
printf '  PASS: %d\n' "${PASS_COUNT}"
printf '  FAIL: %d\n' "${FAIL_COUNT}"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
  printf '\nFailed assertions:\n'
  for name in "${FAIL_NAMES[@]}"; do
    printf '  - %s\n' "${name}"
  done
  printf '\nOFFLINE_TESTS_RESULT=FAIL\n'
  exit 1
else
  printf '\nOFFLINE_TESTS_RESULT=PASS\n'
  exit 0
fi
