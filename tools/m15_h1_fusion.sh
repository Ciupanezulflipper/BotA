#!/usr/bin/env bash
# R5 runtime-root compatibility boundary for the legacy M15/H1 fusion stack.
#
# Production code remains immutable under BOTA_CODE_ROOT while runtime data
# lives under BOTA_MUTABLE_ROOT. The legacy fusion/scoring stack historically
# treated BOTA_ROOT as both code and data. Build a narrow symlink view under the
# mutable root so legacy reads/writes resolve to the correct generation without
# making the immutable release writable.

set -euo pipefail

CODE_ROOT="${BOTA_CODE_ROOT:-${BOTA_ROOT:-$HOME/BotA}}"
MUTABLE_ROOT="${BOTA_MUTABLE_ROOT:-${BOTA_ROOT:-${CODE_ROOT}}}"
LEGACY="${CODE_ROOT}/tools/m15_h1_fusion_legacy.sh"
VIEW="${MUTABLE_ROOT}/runtime_root"

fail() {
  printf '[R5_RUNTIME_ROOT][ERROR] %s\n' "$*" >&2
  exit 78
}

[[ -f "${LEGACY}" ]] || fail "legacy fusion missing: ${LEGACY}"

mkdir -p \
  "${MUTABLE_ROOT}/cache" \
  "${MUTABLE_ROOT}/logs" \
  "${MUTABLE_ROOT}/state" \
  "${VIEW}"

link_exact() {
  local name="$1"
  local target="$2"
  local dest="${VIEW}/${name}"

  if [[ -L "${dest}" ]]; then
    if [[ "$(readlink "${dest}")" == "${target}" ]]; then
      return 0
    fi
    rm -f "${dest}"
  elif [[ -e "${dest}" ]]; then
    fail "runtime view collision at ${dest}"
  fi

  ln -s "${target}" "${dest}"
}

# Mutable runtime surfaces.
link_exact cache "${MUTABLE_ROOT}/cache"
link_exact logs "${MUTABLE_ROOT}/logs"
link_exact state "${MUTABLE_ROOT}/state"

# Immutable generation surfaces required by the legacy stack.
link_exact tools "${CODE_ROOT}/tools"
link_exact config "${CODE_ROOT}/config"
if [[ -e "${CODE_ROOT}/data" ]]; then
  link_exact data "${CODE_ROOT}/data"
fi

exec env \
  BOTA_CODE_ROOT="${CODE_ROOT}" \
  BOTA_ROOT="${VIEW}" \
  BOTA_MUTABLE_ROOT="${MUTABLE_ROOT}" \
  bash "${LEGACY}" "$@"
