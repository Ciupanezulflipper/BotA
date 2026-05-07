#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/market_open.sh
# DESC: v2.0.4 server-clock FX market gate — London + NY sessions only
# Active window: 07:00-20:00 UTC Mon-Fri
# Output: "Open" or "Closed" only on stdout
# Exit: 0 when Open, 1 when Closed
#
# Why server clock:
# On cruise/ship mode, Android local time/UTC can drift when ship time is
# changed manually. This gate must not trust device UTC for trading decisions.

set -euo pipefail

debug() {
  if [[ "${MARKET_OPEN_DEBUG:-0}" = "1" ]]; then
    echo "[MARKET_OPEN] $*" >&2
  fi
}

compute_server_utc_fields() {
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
    print("0 0000 NA 0 999999")
    raise SystemExit(0)

spread = max(epochs) - min(epochs)
if spread > 120:
    print("0 0000 NA %d %d" % (len(epochs), spread))
    raise SystemExit(0)

server_epoch = int(statistics.median(epochs))
dt = datetime.fromtimestamp(server_epoch, timezone.utc)

# Output fields for bash:
# dow hm iso count spread
print(
    f"{dt.isoweekday()} "
    f"{dt.strftime('%H%M')} "
    f"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')} "
    f"{len(epochs)} "
    f"{spread}"
)
PY
}

read -r _utc_dow _utc_hm _server_iso _server_count _server_spread < <(compute_server_utc_fields)

if [[ "${_utc_dow:-0}" = "0" || "${_utc_hm:-0000}" = "0000" ]]; then
  debug "server_clock_unavailable count=${_server_count:-0} spread=${_server_spread:-NA} -> Closed fail_closed"
  echo "Closed"
  exit 1
fi

_utc_int="$((10#$_utc_hm))"

debug "server_utc=${_server_iso} dow=${_utc_dow} hm=${_utc_hm} count=${_server_count} spread=${_server_spread}"

# Saturday UTC: closed all day
if [[ "$_utc_dow" -eq 6 ]]; then
  debug "Saturday UTC -> Closed"
  echo "Closed"
  exit 1
fi

# Sunday UTC: closed all day
if [[ "$_utc_dow" -eq 7 ]]; then
  debug "Sunday UTC -> Closed"
  echo "Closed"
  exit 1
fi

# Friday UTC: close at 20:00 UTC
if [[ "$_utc_dow" -eq 5 && "$_utc_int" -ge 2000 ]]; then
  debug "Friday after 20:00 UTC -> Closed"
  echo "Closed"
  exit 1
fi

# Skip session filter override.
# Preserves original behavior: bypasses Asian/post-NY filter only,
# not weekend or Friday close.
if [[ "${SKIP_SESSION_FILTER:-0}" = "1" ]]; then
  debug "SKIP_SESSION_FILTER=1 -> Open"
  echo "Open"
  exit 0
fi

# Block Asian session: 00:00-07:00 UTC
if [[ "$_utc_int" -lt 700 ]]; then
  debug "before 07:00 UTC -> Closed"
  echo "Closed"
  exit 1
fi

# Block post-NY: 20:00-24:00 UTC
if [[ "$_utc_int" -ge 2000 ]]; then
  debug "after 20:00 UTC -> Closed"
  echo "Closed"
  exit 1
fi

debug "within 07:00-20:00 UTC Mon-Fri -> Open"
echo "Open"
exit 0
