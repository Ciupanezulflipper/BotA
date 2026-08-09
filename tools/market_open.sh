#!/data/data/com.termux/files/usr/bin/bash
# shellcheck shell=bash
# FILE: tools/market_open.sh
# DESC: v2.2.0 trusted-clock FX market gate — London + NY sessions only
# Active window: 07:00-20:00 UTC Mon-Fri
# Output: "Open" or "Closed" only on stdout
# Exit: 0 when Open, 1 when Closed
#
# Machine-readable reason codes (Phase 1 Monday-readiness):
#   Open:   MARKET_OPEN
#   Closed: MARKET_CLOSED_SATURDAY
#           MARKET_CLOSED_SUNDAY
#           MARKET_CLOSED_FRIDAY_POST_2000
#           MARKET_CLOSED_ASIAN_PRE_0700
#           MARKET_CLOSED_POST_NY
#           CLOCK_UNAVAILABLE   (fewer than 2 responsive time sources, or spread > 120s)
#           MARKET_GATE_ERROR   (unexpected internal error — fail-closed)
#
# When MARKET_OPEN_REASON_FILE is set, the reason code is atomically written
# to that path (one line, no trailing newline noise beyond '\n'). This lets
# callers distinguish "market truly closed" from "we could not determine the
# time" without weakening the fail-closed trading behavior.
#
# When BOTA_SERVER_EPOCH_FILE is set AND trusted time is available, the epoch
# integer is written to that path. If BOTA_SERVER_EPOCH already contains a
# structurally valid trusted epoch, it is reused and no network clock probe is
# performed. Otherwise the existing multi-source HTTP Date probe is used.
#
# Why trusted server time:
# On cruise/ship mode, Android local time/UTC can drift when ship time is
# changed manually. Market/session semantics must not trust device wall time.

set -euo pipefail

_final_reason=""

debug() {
  if [[ "${MARKET_OPEN_DEBUG:-0}" = "1" ]]; then
    echo "[MARKET_OPEN] $*" >&2
  fi
}

write_reason_file() {
  local reason="$1"
  local target="${MARKET_OPEN_REASON_FILE:-}"
  if [[ -z "$target" ]]; then
    return 0
  fi
  local tmp="${target}.tmp.$$"
  if printf '%s\n' "$reason" >"$tmp" 2>/dev/null; then
    mv -f "$tmp" "$target" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
  fi
}

write_server_epoch_file() {
  local epoch="$1"
  local target="${BOTA_SERVER_EPOCH_FILE:-}"
  if [[ -z "$target" || -z "$epoch" || "$epoch" = "0" ]]; then
    return 0
  fi
  local tmp="${target}.tmp.$$"
  if printf '%s\n' "$epoch" >"$tmp" 2>/dev/null; then
    mv -f "$tmp" "$target" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
  fi
}

emit_open() {
  _final_reason="MARKET_OPEN"
  debug "reason=${_final_reason}"
  write_reason_file "$_final_reason"
  echo "Open"
  exit 0
}

emit_closed() {
  local reason="$1"
  _final_reason="$reason"
  debug "reason=${_final_reason}"
  write_reason_file "$_final_reason"
  echo "Closed"
  exit 1
}

# DeepSource does not follow the indirect reference from `trap on_error ERR`.
# This handler is intentionally invoked only by the ERR trap below.
# skipcq
on_error() {  # skipcq
  local exit_code=$?
  if [[ -n "$_final_reason" ]]; then
    return 0
  fi
  debug "unexpected shell error exit_code=${exit_code} -> MARKET_GATE_ERROR"
  write_reason_file "MARKET_GATE_ERROR"
  echo "Closed"
  exit 1
}

trap on_error ERR

compute_server_utc_fields() {
  local inherited_epoch="${BOTA_SERVER_EPOCH:-}"

  # A parent gated watcher cycle already paid the network cost and established
  # trusted time. Reuse that exact epoch so every nested scorer observes one
  # coherent instant and cannot be affected by Android wall-clock drift.
  if [[ "$inherited_epoch" =~ ^[0-9]+$ ]] && (( inherited_epoch > 1000000000 )); then
    BOTA_TRUSTED_EPOCH="$inherited_epoch" python3 - <<'PY'
import os
from datetime import datetime, timezone

epoch = int(os.environ["BOTA_TRUSTED_EPOCH"])
dt = datetime.fromtimestamp(epoch, timezone.utc)
print(
    f"{dt.isoweekday()} "
    f"{dt.strftime('%H%M')} "
    f"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')} "
    f"1 0 {epoch}"
)
PY
    return 0
  fi

  python3 - <<'PY'
import urllib.request
import urllib.error
import email.utils
import statistics
from datetime import datetime, timezone

urls = [
    "https://www.google.com",
    "https://api-fxpractice.oanda.com",
    "https://query1.finance.yahoo.com",
    "https://www.cloudflare.com",
]

epochs = []

for url in urls:
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "Mozilla/5.0"},
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                date_header = r.headers.get("Date")
        except urllib.error.HTTPError as e:
            # HTTP 403/429/500 can still carry a valid Date header.
            date_header = e.headers.get("Date")

        if not date_header:
            continue

        dt = email.utils.parsedate_to_datetime(date_header)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        epochs.append(int(dt.timestamp()))
    except Exception:
        continue

if len(epochs) < 2:
    # count<2 => clock unavailable
    print("0 0000 NA %d 999999 0" % len(epochs))
    raise SystemExit(0)

spread = max(epochs) - min(epochs)
if spread > 120:
    # spread too wide => clock unavailable
    print("0 0000 NA %d %d 0" % (len(epochs), spread))
    raise SystemExit(0)

server_epoch = int(statistics.median(epochs))
dt = datetime.fromtimestamp(server_epoch, timezone.utc)

# Output fields for bash:
# dow hm iso count spread server_epoch
print(
    f"{dt.isoweekday()} "
    f"{dt.strftime('%H%M')} "
    f"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')} "
    f"{len(epochs)} "
    f"{spread} "
    f"{server_epoch}"
)
PY
}

_gate_line="$(compute_server_utc_fields 2>/dev/null || true)"
if [[ -z "$_gate_line" ]]; then
  debug "clock probe returned no output -> CLOCK_UNAVAILABLE"
  emit_closed "CLOCK_UNAVAILABLE"
fi

read -r _utc_dow _utc_hm _server_iso _server_count _server_spread _server_epoch <<<"$_gate_line"

_utc_dow="${_utc_dow:-0}"
_utc_hm="${_utc_hm:-0000}"
_server_count="${_server_count:-0}"
_server_spread="${_server_spread:-NA}"
_server_epoch="${_server_epoch:-0}"

# Validate trusted time structurally instead of treating HHMM=0000 as a
# sentinel. Midnight UTC is valid and must reach the Asian-session gate.
_clock_fields_valid=1
case "$_utc_dow" in
  1|2|3|4|5|6|7) ;;
  *) _clock_fields_valid=0 ;;
esac
case "$_utc_hm" in
  [0-1][0-9][0-5][0-9]|2[0-3][0-5][0-9]) ;;
  *) _clock_fields_valid=0 ;;
esac
case "$_server_epoch" in
  ''|*[!0-9]*) _clock_fields_valid=0 ;;
  *)
    if (( _server_epoch <= 1000000000 )); then
      _clock_fields_valid=0
    fi
    ;;
esac

if (( _clock_fields_valid == 0 )); then
  # Preserves the historical "server_clock_unavailable ... Closed fail_closed"
  # phrase so existing fail-closed source-regression tests keep tripping if
  # anyone tries to weaken this branch.
  debug "server_clock_unavailable count=${_server_count} spread=${_server_spread} -> Closed fail_closed CLOCK_UNAVAILABLE"
  emit_closed "CLOCK_UNAVAILABLE"
fi

write_server_epoch_file "$_server_epoch"

_utc_int="$((10#$_utc_hm))"

debug "trusted_utc=${_server_iso} dow=${_utc_dow} hm=${_utc_hm} count=${_server_count} spread=${_server_spread} epoch=${_server_epoch}"

# Saturday UTC: closed all day
if [[ "$_utc_dow" -eq 6 ]]; then
  debug "Saturday UTC -> MARKET_CLOSED_SATURDAY"
  emit_closed "MARKET_CLOSED_SATURDAY"
fi

# Sunday UTC: closed all day
if [[ "$_utc_dow" -eq 7 ]]; then
  debug "Sunday UTC -> MARKET_CLOSED_SUNDAY"
  emit_closed "MARKET_CLOSED_SUNDAY"
fi

# Friday UTC: close at 20:00 UTC
if [[ "$_utc_dow" -eq 5 && "$_utc_int" -ge 2000 ]]; then
  debug "Friday after 20:00 UTC -> MARKET_CLOSED_FRIDAY_POST_2000"
  emit_closed "MARKET_CLOSED_FRIDAY_POST_2000"
fi

# Skip session filter override.
# Preserves original behavior: bypasses Asian/post-NY filter only,
# not weekend or Friday close.
if [[ "${SKIP_SESSION_FILTER:-0}" = "1" ]]; then
  debug "SKIP_SESSION_FILTER=1 -> MARKET_OPEN"
  emit_open
fi

# Block Asian session: 00:00-07:00 UTC
if [[ "$_utc_int" -lt 700 ]]; then
  debug "before 07:00 UTC -> MARKET_CLOSED_ASIAN_PRE_0700"
  emit_closed "MARKET_CLOSED_ASIAN_PRE_0700"
fi

# Block post-NY: 20:00-24:00 UTC
if [[ "$_utc_int" -ge 2000 ]]; then
  debug "after 20:00 UTC -> MARKET_CLOSED_POST_NY"
  emit_closed "MARKET_CLOSED_POST_NY"
fi

debug "within 07:00-20:00 UTC Mon-Fri -> MARKET_OPEN"
emit_open
