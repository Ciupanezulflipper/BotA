#!/data/data/com.termux/files/usr/bin/bash
# Hash-pinned, non-interactive BotA partial-orphan native-manager migration executor.
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
case "${SOURCE_COMMIT}" in
    ""|*[!0-9a-f]*)
        printf 'MIGRATION_ABORTED=INVALID_SOURCE_COMMIT\n'
        exit 4
        ;;
esac
[[ ${#SOURCE_COMMIT} -eq 40 ]] || {
    printf 'MIGRATION_ABORTED=INVALID_SOURCE_COMMIT_LENGTH\n'
    exit 4
}

cd "${ROOT}"
git cat-file -e "${SOURCE_COMMIT}^{commit}" 2>/dev/null || {
    printf 'MIGRATION_ABORTED=SOURCE_COMMIT_NOT_FETCHED:%s\n' "${SOURCE_COMMIT}"
    exit 5
}

STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
AUDIT="${ROOT}/audits/native_manager_partial_migration_${STAMP}"
STAGE="${AUDIT}/stage"
BACKUP="${AUDIT}/backup"
BOOT="${HOME}/.termux/boot/00-termux-services.sh"
STATE_DIR="${ROOT}/state/native_manager_migration"
JOURNAL="${STATE_DIR}/active.json"
mkdir -p "${STAGE}/tools" "${BACKUP}/tools" "${STATE_DIR}"

PATHS=(
    tools/native_service_daemon_watchdog.py
    tools/start_native_service_daemon_watchdog.sh
    tools/native_service_daemon_migration.py
    tools/native_service_daemon_partial_migration.py
)

write_journal() {
    local phase="$1"
    local tmp="${JOURNAL}.tmp.$$"
    printf '{"schema":1,"phase":"%s","source_commit":"%s","audit":"%s","updated_utc":"%s"}\n' \
        "${phase}" "${SOURCE_COMMIT}" "${AUDIT}" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
        > "${tmp}"
    mv -f "${tmp}" "${JOURNAL}"
}

archive_journal() {
    local reason="$1"
    [[ -f "${JOURNAL}" ]] || return 0
    mv -f "${JOURNAL}" "${STATE_DIR}/${STAMP}.${reason}.json"
}

runtime_recovery_gate() {
    python3 - "${ROOT}" <<'PY'
import os
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from tools import native_service_daemon_watchdog as w

prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
service_root = prefix / "var/service"
sv = prefix / "bin/sv"
pidfile = prefix / "var/run/service-daemon.pid"

def snapshot():
    table = w.process_table()
    state = w.topology(table, service_root)
    try:
        pidfile_value = int(pidfile.read_text().strip())
    except Exception:
        pidfile_value = None
    down = [s for s in w.SERVICES if not w.running(sv, service_root, s)]
    safe = (
        state["manager_count"] == 1
        and state["manager_pid"] == pidfile_value
        and state["owned"] + state["orphaned"] == len(w.SERVICES)
        and state["invalid"] == 0
        and state["duplicates"] == 0
        and not down
        and all(
            state["services"][service]["runsv_count"] == 1
            and state["services"][service]["owner"] in {"manager", "pid1_orphan"}
            for service in w.SERVICES
        )
    )
    return state, down, safe

deadline = time.monotonic() + 90
while True:
    state, down, safe = snapshot()
    if safe:
        print(
            "RECOVERY_TOPOLOGY=SAFE:"
            f"owned={state['owned']}/7;orphaned={state['orphaned']};"
            f"invalid={state['invalid']};duplicates={state['duplicates']};"
            f"running={7-len(down)}/7"
        )
        raise SystemExit(0)
    if time.monotonic() >= deadline:
        print(
            "RECOVERY_TOPOLOGY=UNSAFE:"
            f"managers={state['manager_count']};owned={state['owned']}/7;"
            f"orphaned={state['orphaned']};invalid={state['invalid']};"
            f"duplicates={state['duplicates']};running={7-len(down)}/7;"
            f"down={','.join(down) if down else 'NONE'}"
        )
        raise SystemExit(1)
    time.sleep(2)
PY
}

if [[ -f "${JOURNAL}" ]]; then
    printf 'INCOMPLETE_MIGRATION_JOURNAL=%s\n' "${JOURNAL}"
    if runtime_recovery_gate; then
        archive_journal recovered_safe
        printf 'INCOMPLETE_MIGRATION_RECOVERY=SAFE_TO_RESUME\n'
    else
        printf 'MIGRATION_ABORTED=INCOMPLETE_MIGRATION_RECOVERY_REQUIRED\n'
        exit 11
    fi
fi

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
        write_journal rollback_files_restored
        archive_journal rollback
        printf 'FILE_ROLLBACK=PASS\n'
    fi
}
trap on_exit EXIT
trap 'printf "MIGRATION_INTERRUPTED=SIGNAL\n"; exit 128' HUP INT TERM

for path in "${PATHS[@]}"; do
    git cat-file -e "${SOURCE_COMMIT}:${path}" || {
        printf 'MIGRATION_ABORTED=SOURCE_PATH_MISSING:%s\n' "${path}"
        exit 6
    }
    git show "${SOURCE_COMMIT}:${path}" > "${STAGE}/${path}"
    EXPECTED_BLOB="$(git rev-parse "${SOURCE_COMMIT}:${path}")"
    ACTUAL_BLOB="$(git hash-object "${STAGE}/${path}")"
    [[ "${ACTUAL_BLOB}" = "${EXPECTED_BLOB}" ]] || {
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
[[ "${OLD_COUNT}" = 1 && "${NEW_COUNT}" = 0 ]] || {
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
write_journal backups_complete

for path in "${PATHS[@]}"; do
    name="${path##*/}"
    install -m 0755 "${STAGE}/tools/${name}" "${ROOT}/tools/${name}"
done
write_journal files_installed

BOOT_NEW="${AUDIT}/00-termux-services.sh.new"
sed 's/start_runsvdir_guard\.sh/start_native_service_daemon_watchdog.sh/' \
    "${BOOT}" > "${BOOT_NEW}"
[[ "$(grep -Foc 'start_native_service_daemon_watchdog.sh' "${BOOT_NEW}" || true)" = 1 ]] || {
    printf 'MIGRATION_ABORTED=BOOT_REWRITE_FAILED\n'
    exit 10
}
install -m 0755 "${BOOT_NEW}" "${BOOT}"
write_journal boot_rewritten

write_journal runtime_cutover_started
python3 "${ROOT}/tools/native_service_daemon_partial_migration.py" \
    --apply \
    --audit-dir "${AUDIT}"
write_journal runtime_cutover_complete

trap - EXIT HUP INT TERM
archive_journal success
printf 'BOOT_LAUNCHER_MIGRATION=PASS\n'
printf 'AUDIT_DIRECTORY=%s\n' "${AUDIT}"
printf 'RUNTIME_MUTATION_PERFORMED=NATIVE_MANAGER_PARTIAL_CUTOVER_AND_WATCHDOG_START\n'
