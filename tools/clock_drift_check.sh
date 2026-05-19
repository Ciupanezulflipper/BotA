#!/data/data/com.termux/files/usr/bin/bash
# FILE: tools/clock_drift_check.sh
# ROLE: Safe wrapper for BotA clock drift observability.
# This is reporting-only. It does not alter trading logic or thresholds.

set -euo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
cd "${ROOT}" || { echo "FAIL: cannot cd to ${ROOT}" >&2; exit 1; }

python3 "${ROOT}/tools/clock_drift_check.py" --plain --write-state "$@"
