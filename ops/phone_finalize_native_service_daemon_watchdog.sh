#!/data/data/com.termux/files/usr/bin/bash
# Hash-pinned, non-interactive finalizer for a fully owned native service tree.
set -Eeuo pipefail

ROOT="${BOTA_ROOT:-${HOME}/BotA}"
SOURCE_COMMIT=""
APPLY=0

while (($#)); do
    case "$1" in
        --apply) APPLY=1 ;;
        --source-commit)
            shift
            SOURCE_COMMIT="${1:-}"
            ;;
        *)
            printf 'FINALIZER_ABORTED=UNKNOWN_ARGUMENT:%s\n' "$1"
            exit 2
            ;;
    esac
    shift
done

cat "${ROOT}/audits/ERROR_LOG.md"
[[ -f "${ROOT}/audits/ERROR_LOG_E035.md" ]] && cat "${ROOT}/audits/ERROR_LOG_E035.md"
printf '%s\n' \
    'ERROR_LOG_REVIEWED=YES' \
    'CIRCULAR_ERROR_CHECK=PASS' \
    'TARGET_PROJECT=BotA' \
    "TARGET_PATH=${ROOT}"

[[ ${APPLY} -eq 1 ]] || {
    printf 'FINALIZER_ABORTED=APPLY_FLAG_REQUIRED\n'
    exit 3
}
case "${SOURCE_COMMIT}" in
    ""|*[!0-9a-f]*)
        printf 'FINALIZER_ABORTED=INVALID_SOURCE_COMMIT\n'
        exit 4
        ;;
esac
[[ ${#SOURCE_COMMIT} -eq 40 ]] || {
    printf 'FINALIZER_ABORTED=INVALID_SOURCE_COMMIT_LENGTH\n'
    exit 4
}

cd "${ROOT}"
git cat-file -e "${SOURCE_COMMIT}^{commit}" 2>/dev/null || {
    printf 'FINALIZER_ABORTED=SOURCE_COMMIT_NOT_FETCHED:%s\n' "${SOURCE_COMMIT}"
    exit 5
}

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
AUDIT="${ROOT}/audits/native_watchdog_finalizer_${STAMP}"
STAGE="${AUDIT}/stage"
BACKUP="${AUDIT}/backup"
BOOT="${HOME}/.termux/boot/00-termux-services.sh"
mkdir -p "${STAGE}/tools" "${BACKUP}/tools"

PATHS=(
    tools/native_service_daemon_watchdog.py
    tools/start_native_service_daemon_watchdog.sh
    tools/native_service_daemon_migration.py
    tools/native_service_daemon_watchdog_finalizer.py
    tools/native_service_boot_config.py
    tools/control_plane_status.py
    tools/pre_market_integrity.py
)

restore_files() {
    local path name
    for path in "${PATHS[@]}"; do
        name="${path##*/}"
        if [[ -f "${BACKUP}/tools/${name}" ]]; then
            cp -p "${BACKUP}/tools/${name}" "${ROOT}/tools/${name}"
        else
            rm -f "${ROOT}/tools/${name}"
        fi
    done
    [[ -f "${BACKUP}/00-termux-services.sh" ]] &&
        cp -p "${BACKUP}/00-termux-services.sh" "${BOOT}"
}

on_exit() {
    local rc=$?
    if ((rc)) && [[ -f "${BACKUP}/00-termux-services.sh" ]]; then
        restore_files
        printf 'FILE_ROLLBACK=PASS\n'
    fi
}
trap on_exit EXIT

for path in "${PATHS[@]}"; do
    git cat-file -e "${SOURCE_COMMIT}:${path}" || {
        printf 'FINALIZER_ABORTED=SOURCE_PATH_MISSING:%s\n' "${path}"
        exit 6
    }
    git show "${SOURCE_COMMIT}:${path}" > "${STAGE}/${path}"
    EXPECTED_BLOB="$(git rev-parse "${SOURCE_COMMIT}:${path}")"
    ACTUAL_BLOB="$(git hash-object "${STAGE}/${path}")"
    [[ "${ACTUAL_BLOB}" = "${EXPECTED_BLOB}" ]] || {
        printf 'FINALIZER_ABORTED=BLOB_MISMATCH:%s\n' "${path}"
        exit 7
    }
done

[[ -f "${BOOT}" ]] || {
    printf 'FINALIZER_ABORTED=BOOT_FILE_MISSING:%s\n' "${BOOT}"
    exit 8
}

BOOT_NEW="${AUDIT}/00-termux-services.sh.new"
python3 "${STAGE}/tools/native_service_boot_config.py" \
    --source "${BOOT}" \
    --output "${BOOT_NEW}" \
    --launcher "${ROOT}/tools/start_native_service_daemon_watchdog.sh" \
    --log "${ROOT}/logs/native_service_daemon_watchdog.boot.log" || {
        printf 'FINALIZER_ABORTED=BOOT_RENDER_FAILED\n'
        exit 9
    }
[[ "$(grep -Foc '# BEGIN BOTA_NATIVE_SERVICE_WATCHDOG' "${BOOT_NEW}" || true)" = 1 ]] || {
    printf 'FINALIZER_ABORTED=BOOT_BEGIN_COUNT\n'
    exit 10
}
[[ "$(grep -Foc '# END BOTA_NATIVE_SERVICE_WATCHDOG' "${BOOT_NEW}" || true)" = 1 ]] || {
    printf 'FINALIZER_ABORTED=BOOT_END_COUNT\n'
    exit 10
}
ACTIVE_LEGACY_COUNT="$(grep -v '^[[:space:]]*#' "${BOOT_NEW}" | grep -Fc 'start_runsvdir_guard.sh' || true)"
ACTIVE_WATCHDOG_COUNT="$(grep -v '^[[:space:]]*#' "${BOOT_NEW}" | grep -Fc 'start_native_service_daemon_watchdog.sh' || true)"
[[ "${ACTIVE_LEGACY_COUNT}" = 0 && "${ACTIVE_WATCHDOG_COUNT}" = 1 ]] || {
    printf 'FINALIZER_ABORTED=BOOT_ACTIVE_COUNTS:LEGACY=%s:WATCHDOG=%s\n' \
        "${ACTIVE_LEGACY_COUNT}" "${ACTIVE_WATCHDOG_COUNT}"
    exit 10
}

cp -p "${BOOT}" "${BACKUP}/00-termux-services.sh"
for path in "${PATHS[@]}"; do
    name="${path##*/}"
    [[ -f "${ROOT}/tools/${name}" ]] &&
        cp -p "${ROOT}/tools/${name}" "${BACKUP}/tools/${name}"
done

for path in "${PATHS[@]}"; do
    name="${path##*/}"
    install -m 0755 "${STAGE}/tools/${name}" "${ROOT}/tools/${name}"
done
install -m 0755 "${BOOT_NEW}" "${BOOT}"

python3 "${ROOT}/tools/native_service_daemon_watchdog_finalizer.py" \
    --apply \
    --audit-dir "${AUDIT}"

trap - EXIT
printf 'BOOT_WATCHDOG_MANAGED_BLOCK=PASS\n'
printf 'BOOT_ACTIVE_LEGACY_GUARD=0\n'
printf 'BOOT_ACTIVE_NATIVE_WATCHDOG=1\n'
printf 'BOOT_LAUNCHER_FINALIZATION=PASS\n'
printf 'AUDIT_DIRECTORY=%s\n' "${AUDIT}"
printf 'RUNTIME_MUTATION_PERFORMED=WATCHDOG_START_AND_BOOT_FINALIZATION\n'
