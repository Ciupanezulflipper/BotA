#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HOME}/BotA"
cd "${ROOT}"

# Minimal, deterministic bootstrap:
# be_shadow_manager.py already auto-loads fallback env files internally.
# We source only .env.runtime here so startup matches the main BotA runtime path.
if [[ -f "${ROOT}/.env.runtime" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "${ROOT}/.env.runtime"
  set +a
fi

exec python3 "${ROOT}/tools/be_shadow_manager.py"
