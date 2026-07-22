#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# FILE: tools/indicators_updater.sh
# PURPOSE:
#   Fetch raw candles, build indicators, and emit useful-progress evidence.
#   Actual provider requests are accounted at the network boundary by
#   data_fetch_candles.sh. Strategy, pairs, timeframes, and indicators are
#   unchanged.
###############################################################################

set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

ROOT="${HOME}/BotA"
TOOLS="${ROOT}/tools"
CACHE="${ROOT}/cache"
LOGS="${ROOT}/logs"

PAIRS="${PAIRS:-"EURUSD GBPUSD XAUUSD USDJPY EURJPY"}"
TIMEFRAMES="${TIMEFRAMES:-"M15 H1 H4 D1"}"

FETCH_RETRIES="${FETCH_RETRIES:-5}"
FETCH_BACKOFF_BASE="${FETCH_BACKOFF_BASE:-10}"
FETCH_BACKOFF_MAX="${FETCH_BACKOFF_MAX:-180}"
FETCH_MIN_GAP_SECS="${FETCH_MIN_GAP_SECS:-3}"

mkdir -p "${LOGS}" "${ROOT}/state"

log() { printf '%s\n' "$*" >&2; }

cycle_id="$({ cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown; } | tr -d '\n'):$({ python3 -c 'import time; c=getattr(time,"CLOCK_BOOTTIME",None); print(time.clock_gettime_ns(c) if c is not None else time.monotonic_ns())' 2>/dev/null || echo 0; })"
ledger_finalized=0

ledger_component() {
  local status="$1" details="${2:-}"
  python3 "${TOOLS}/pipeline_ledger.py" component \
    --component updater \
    --status "${status}" \
    --cycle-id "${cycle_id}" \
    --details "${details}" \
    >/dev/null 2>>"${LOGS}/error.log" || true
}

trap 'rc=$?; if [[ "${ledger_finalized}" != 1 ]]; then ledger_component failed "exit_code=${rc}"; fi; trap - EXIT; exit "${rc}"' EXIT

need_file() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    log "[UPDATER] ERROR: missing file: ${file}"
    return 1
  fi
}

need_exec() {
  local file="$1"
  if [[ ! -x "${file}" ]]; then
    log "[UPDATER] ERROR: not executable: ${file}"
    return 1
  fi
}

build_indicators_cli_args() {
  local pair="$1" tf="$2" in_path="$3" out_path="$4"
  local help=""
  help="$(python3 "${TOOLS}/build_indicators.py" --help 2>&1 || python3 "${TOOLS}/build_indicators.py" -h 2>&1 || true)"
  if [[ -z "${help}" ]]; then
    echo "no_cli"
    return 0
  fi

  supports() { grep -qF -- "$1" <<<"${help}"; }
  if supports "--pair"; then
    printf '%s\n' "--pair" "${pair}"
  elif supports "--symbol"; then
    printf '%s\n' "--symbol" "${pair}"
  fi
  if supports "--tf"; then
    printf '%s\n' "--tf" "${tf}"
  elif supports "--timeframe"; then
    printf '%s\n' "--timeframe" "${tf}"
  elif supports "--interval"; then
    printf '%s\n' "--interval" "${tf}"
  fi
  if supports "--in"; then
    printf '%s\n' "--in" "${in_path}"
  elif supports "--input"; then
    printf '%s\n' "--input" "${in_path}"
  elif supports "--json"; then
    printf '%s\n' "--json" "${in_path}"
  fi
  if supports "--out"; then
    printf '%s\n' "--out" "${out_path}"
  elif supports "-o"; then
    printf '%s\n' "-o" "${out_path}"
  fi
}

find_latest_backup_updater() {
  TOOLS_DIR="${TOOLS}" python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ["TOOLS_DIR"])
files = [path for path in root.glob("indicators_updater.sh.bak_pre16k_*") if path.is_file()]
if files:
    print(max(files, key=lambda path: (path.stat().st_mtime_ns, path.name)))
PY
}

fetch_with_retry() {
  local pair="$1" tf="$2" in_path="$3"
  local attempt=1 rc=0

  while (( attempt <= FETCH_RETRIES )); do
    if bash "${TOOLS}/data_fetch_candles.sh" "${pair}" "${tf}" >/dev/null 2>>"${LOGS}/error.log"; then
      sleep "${FETCH_MIN_GAP_SECS}" 2>/dev/null || true
      if [[ -s "${in_path}" ]]; then
        return 0
      fi
      log "[UPDATER] FETCH FAIL ${pair} ${tf} input_missing_or_empty=${in_path} attempt=${attempt}/${FETCH_RETRIES}"
      rc=1
    else
      rc=$?
      log "[UPDATER] FETCH FAIL ${pair} ${tf} rc=${rc} attempt=${attempt}/${FETCH_RETRIES}"
      if [[ "${rc}" -eq 3 ]]; then
        log "[UPDATER] Yahoo rate-limited — skipping retries for ${pair} ${tf}"
        return 3
      fi
    fi

    local pow=$(( attempt - 1 ))
    local backoff=$(( FETCH_BACKOFF_BASE * (1 << pow) ))
    (( backoff > FETCH_BACKOFF_MAX )) && backoff="${FETCH_BACKOFF_MAX}"
    local jitter=$(( RANDOM % 5 ))
    local sleep_s=$(( backoff + jitter ))
    (( attempt == FETCH_RETRIES )) && break
    log "[UPDATER] RETRY SLEEP ${pair} ${tf} sleep_s=${sleep_s}"
    sleep "${sleep_s}" 2>/dev/null || true
    attempt=$(( attempt + 1 ))
  done
  return "${rc:-1}"
}

refresh_d1_trend_cache() {
  source "${ROOT}/.env" 2>/dev/null || true
  source "${ROOT}/config/strategy.env" 2>/dev/null || true
  export OANDA_API_TOKEN OANDA_API_URL ROOT TOOLS

  python3 <<'PYEOF'
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["ROOT"])
tools = Path(os.environ["TOOLS"])
token = os.environ.get("OANDA_API_TOKEN", "")
base = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com").rstrip("/")
pairs = [("EURUSD", "EUR_USD"), ("GBPUSD", "GBP_USD")]

def record(pair: str, status: str, note: str = "") -> None:
    subprocess.run(
        [
            sys.executable,
            str(tools / "provider_usage.py"),
            "record",
            "--provider", "oanda",
            "--caller", "indicators_updater_d1",
            "--pair", pair,
            "--timeframe", "D1",
            "--status", status,
            "--credits", "0",
            "--note", note[:500],
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

for pair, instrument in pairs:
    request = urllib.request.Request(
        f"{base}/v3/instruments/{instrument}/candles?count=50&granularity=D&price=M",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read())
        record(pair, "success")
        candles = [candle for candle in data["candles"] if candle.get("complete", True)]
        closes = [float(candle["mid"]["c"]) for candle in candles]

        def ema(values, period):
            factor = 2.0 / (period + 1)
            result = sum(values[:period]) / period
            for value in values[period:]:
                result = value * factor + result * (1 - factor)
            return result

        ema9 = ema(closes, 9)
        ema21 = ema(closes, 21)
        trend = "BUY" if ema9 > ema21 else "SELL"
        bundle = {
            "pair": pair,
            "ema9": ema9,
            "ema21": ema21,
            "trend": trend,
            "weak": False,
            "error": "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        (root / "cache" / f"d1_trend_{pair}.json").write_text(
            json.dumps(bundle), encoding="utf-8"
        )
        print(f"[D1] {pair}: {trend} EMA9={ema9:.5f} EMA21={ema21:.5f}")
    except Exception as exc:
        record(pair, "failure", type(exc).__name__)
        print(f"[D1] {pair} error: {type(exc).__name__}", flush=True)
PYEOF
}

ledger_component started "pairs=${PAIRS};timeframes=${TIMEFRAMES}"

log "------------------------------------------------------------"
log "[UPDATER] start provider-boundary accounting + progress ledger"
log "[UPDATER] PAIRS=${PAIRS}"
log "[UPDATER] TIMEFRAMES=${TIMEFRAMES}"
log "------------------------------------------------------------"

need_file "${TOOLS}/build_indicators.py" || exit 1
need_file "${TOOLS}/data_fetch_candles.sh" || exit 1
need_file "${TOOLS}/provider_usage.py" || exit 1
need_file "${TOOLS}/pipeline_ledger.py" || exit 1
need_exec "${TOOLS}/data_fetch_candles.sh" || exit 1

build_fail_count=0
fetch_fail_count=0
fetch_success_count=0

for pair in ${PAIRS}; do
  for tf in ${TIMEFRAMES}; do
    in_path="${CACHE}/${pair}_${tf}.json"
    out_path="${CACHE}/indicators_${pair}_${tf}.json"
    log "[UPDATER] ---- ${pair} ${tf} ----"

    fetch_rc=0
    if fetch_with_retry "${pair}" "${tf}" "${in_path}"; then
      provider="$(CACHE_PATH="${in_path}" python3 - <<'PY' 2>/dev/null || echo unknown
import json
import os
try:
    data = json.load(open(os.environ["CACHE_PATH"], "r", encoding="utf-8"))
    meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
    print(str(meta.get("_provider") or "unknown").strip().lower() or "unknown")
except Exception:
    print("unknown")
PY
)"
      fetch_success_count=$((fetch_success_count + 1))
      log "[UPDATER] FETCH OK ${pair} ${tf} provider=${provider}"
    else
      fetch_rc=$?
      fetch_fail_count=$((fetch_fail_count + 1))
      log "[UPDATER] FETCH FAIL ${pair} ${tf} rc=${fetch_rc}; skip build"
      continue
    fi

    cli_lines="$(build_indicators_cli_args "${pair}" "${tf}" "${in_path}" "${out_path}")"
    if [[ "${cli_lines}" = "no_cli" ]]; then
      build_fail_count=$((build_fail_count + 1))
      log "[UPDATER] BUILD FAIL ${pair} ${tf} could_not_read_cli_help"
      continue
    fi

    mapfile -t ARGS <<<"${cli_lines}"
    if PAIR="${pair}" TF="${tf}" INPUT_JSON="${in_path}" OUTPUT_JSON="${out_path}" \
      python3 "${TOOLS}/build_indicators.py" "${ARGS[@]}" 2>>"${LOGS}/error.log"; then
      log "[UPDATER] BUILD OK ${pair} ${tf}"
    else
      build_fail_count=$((build_fail_count + 1))
      log "[UPDATER] BUILD ERROR ${pair} ${tf}"
      continue
    fi

    if [[ ! -s "${out_path}" ]]; then
      build_fail_count=$((build_fail_count + 1))
      log "[UPDATER] OUTPUT FAIL ${pair} ${tf} missing_or_empty=${out_path}"
    fi
  done
done

if (( build_fail_count > 0 )); then
  backup="$(find_latest_backup_updater)"
  if [[ -n "${backup}" && -f "${backup}" ]]; then
    log "[UPDATER] FALLBACK build_fail_count=${build_fail_count} backup=${backup}"
    if ! PAIRS="${PAIRS}" TIMEFRAMES="${TIMEFRAMES}" bash "${backup}" 2>>"${LOGS}/error.log"; then
      log "[UPDATER] FALLBACK FAIL"
      exit 1
    fi
  else
    log "[UPDATER] FALLBACK SKIP no backup"
    exit 1
  fi
fi

refresh_d1_trend_cache

ledger_component completed "fetch_success=${fetch_success_count};fetch_fail=${fetch_fail_count};build_fail=${build_fail_count}"
ledger_finalized=1
log "[UPDATER] DONE fetch_success_count=${fetch_success_count} fetch_fail_count=${fetch_fail_count} build_fail_count=${build_fail_count}"
exit 0
