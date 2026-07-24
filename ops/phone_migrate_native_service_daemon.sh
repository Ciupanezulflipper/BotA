#!/data/data/com.termux/files/usr/bin/bash
# Hash-pinned, non-interactive BotA native-manager migration executor.
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
            printf 'MIGRATION_ABORTED=UNKNOWN_ARGUMENT:%s\n' "$1"
            exit 2
            ;;
    esac
    shift
done

cat "${ROOT}/audits/ERROR_LOG.md"
printf '%s\n' \
    'ERROR_LOG_REVIEWED=YES' \
    'CIRCULAR_ERROR_CHECK=PASS' \
    'TARGET_PROJECT=BotA' \
    "TARGET_PATH=${ROOT}"

[[ ${APPLY} -eq 1 ]] || {
    printf 'MIGRATION_ABORTED=APPLY_FLAG_REQUIRED\n'
    exit 3
}
[[ ${SOURCE_COMMIT} =~ ^[0-9a-f]{40}$ ]] || {
    printf 'MIGRATION_ABORTED=INVALID_SOURCE_COMMIT\n'
    exit 4
}

cd "${ROOT}"
git cat-file -e "${SOURCE_COMMIT}^{commit}" 2>/dev/null || {
    printf 'MIGRATION_ABORTED=SOURCE_COMMIT_NOT_FETCHED:%s\n' "${SOURCE_COMMIT}"
    exit 5
}

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
AUDIT="${ROOT}/audits/native_manager_migration_${STAMP}"
STAGE="${AUDIT}/stage"
BACKUP="${AUDIT}/backup"
BOOT="${HOME}/.termux/boot/00-termux-services.sh"
mkdir -p "${STAGE}/tools" "${BACKUP}/tools"
BACKUP_READY=0

PATHS=(
    tools/native_service_daemon_watchdog.py
    tools/start_native_service_daemon_watchdog.sh
    tools/native_service_daemon_migration.py
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

trap 'rc=$?; if ((rc)) && ((BACKUP_READY)); then restore_files; printf "FILE_ROLLBACK=PASS\n"; fi' EXIT

for path in "${PATHS[@]}"; do
    git cat-file -e "${SOURCE_COMMIT}:${path}" || {
        printf 'MIGRATION_ABORTED=SOURCE_PATH_MISSING:%s\n' "${path}"
        exit 6
    }
    git show "${SOURCE_COMMIT}:${path}" > "${STAGE}/${path}"
    EXPECTED_BLOB="$(git rev-parse "${SOURCE_COMMIT}:${path}")"
    ACTUAL_BLOB="$(git hash-object "${STAGE}/${path}")"
    [[ "${ACTUAL_BLOB}" == "${EXPECTED_BLOB}" ]] || {
        printf 'MIGRATION_ABORTED=BLOB_MISMATCH:%s\n' "${path}"
        exit 7
    }
done

[[ -f "${BOOT}" ]] || {
    printf 'MIGRATION_ABORTED=BOOT_FILE_MISSING:%s\n' "${BOOT}"
    exit 8
}
OLD_COUNT="$(grep -Foc 'start_runsvdir_guard.sh' "${BOOT}" || true)"
NEW_COUNT="$(grep -Foc 'start_native_service_daemon_watchdog.sh' "${BOOT}" || true)"
[[ "${OLD_COUNT}" == 1 && "${NEW_COUNT}" == 0 ]] || {
    printf 'MIGRATION_ABORTED=BOOT_LAUNCHER_COUNTS:OLD=%s:NEW=%s\n' \
        "${OLD_COUNT}" "${NEW_COUNT}"
    exit 9
}

cp -p "${BOOT}" "${BACKUP}/00-termux-services.sh"
for path in "${PATHS[@]}"; do
    name="${path##*/}"
    [[ -f "${ROOT}/tools/${name}" ]] &&
        cp -p "${ROOT}/tools/${name}" "${BACKUP}/tools/${name}"
done
BACKUP_READY=1

install -m 0755 "${STAGE}/tools/native_service_daemon_watchdog.py" \
    "${ROOT}/tools/native_service_daemon_watchdog.py"
install -m 0755 "${STAGE}/tools/start_native_service_daemon_watchdog.sh" \
    "${ROOT}/tools/start_native_service_daemon_watchdog.sh"
install -m 0755 "${STAGE}/tools/native_service_daemon_migration.py" \
    "${ROOT}/tools/native_service_daemon_migration.py"

BOOT_NEW="${AUDIT}/00-termux-services.sh.new"
sed 's/start_runsvdir_guard\.sh/start_native_service_daemon_watchdog.sh/' \
    "${BOOT}" > "${BOOT_NEW}"
[[ "$(grep -Foc 'start_native_service_daemon_watchdog.sh' "${BOOT_NEW}" || true)" == 1 ]] ||
    {
        printf 'MIGRATION_ABORTED=BOOT_REWRITE_FAILED\n'
        exit 10
    }
install -m 0755 "${BOOT_NEW}" "${BOOT}"

python3 "${ROOT}/tools/native_service_daemon_migration.py" \
    --apply \
    --audit-dir "${AUDIT}"

trap - EXIT
printf 'BOOT_LAUNCHER_MIGRATION=PASS\n'
printf 'AUDIT_DIRECTORY=%s\n' "${AUDIT}"
printf 'RUNTIME_MUTATION_PERFORMED=NATIVE_MANAGER_CUTOVER_AND_WATCHDOG_START\n'
