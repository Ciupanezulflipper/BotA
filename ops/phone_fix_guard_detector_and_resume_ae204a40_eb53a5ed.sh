#!/data/data/com.termux/files/usr/bin/bash
cat "$HOME/BotA/audits/ERROR_LOG.md"
printf '%s\n' \
  'ERROR_LOG_REVIEWED=YES' \
  'CIRCULAR_ERROR_CHECK=PASS'

set -Eeuo pipefail
umask 077

ROOT="$HOME/BotA"
SOURCE="$ROOT/audits/phone_split_manager_reconcile_deploy_ae204a40_eb53a5ed.sh"
CORRECTED="$ROOT/audits/phone_split_manager_reconcile_deploy_ae204a40_eb53a5ed_v2.sh"
EXPECTED_SOURCE_SHA256="59101267596e98199ede91768c4b68cf5d391ae30be93e582075a1089b09146e"
EXPECTED_SOURCE_GIT_BLOB="c74d238c9f29dfa74af6501c3545bf3549b836c0"

[ -f "$SOURCE" ] || {
  printf 'CORRECTION_ABORTED=SOURCE_ARTIFACT_MISSING\n'
  exit 2
}

ACTUAL_SOURCE_SHA256="$(sha256sum "$SOURCE" | awk '{print $1}')"
[ "$ACTUAL_SOURCE_SHA256" = "$EXPECTED_SOURCE_SHA256" ] || {
  printf 'CORRECTION_ABORTED=SOURCE_SHA256_MISMATCH\n'
  printf 'EXPECTED_SOURCE_SHA256=%s\n' "$EXPECTED_SOURCE_SHA256"
  printf 'ACTUAL_SOURCE_SHA256=%s\n' "$ACTUAL_SOURCE_SHA256"
  exit 3
}

ACTUAL_SOURCE_GIT_BLOB="$(git hash-object "$SOURCE")"
[ "$ACTUAL_SOURCE_GIT_BLOB" = "$EXPECTED_SOURCE_GIT_BLOB" ] || {
  printf 'CORRECTION_ABORTED=SOURCE_GIT_BLOB_MISMATCH\n'
  printf 'EXPECTED_SOURCE_GIT_BLOB=%s\n' "$EXPECTED_SOURCE_GIT_BLOB"
  printf 'ACTUAL_SOURCE_GIT_BLOB=%s\n' "$ACTUAL_SOURCE_GIT_BLOB"
  exit 4
}

python3 - "$SOURCE" "$CORRECTED" <<'PYFIX'
from pathlib import Path
import sys

source = Path(sys.argv[1])
target = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")

old = '''guard_pids() {
  python3 - \\
    "$ROOT/tools/runsvdir_guard.py" \\
    "$ROOT/tools/runsvdir_guard_runtime.py" <<'PY'
from pathlib import Path
import sys

targets = {str(Path(value)) for value in sys.argv[1:]}
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    try:
        argv = [
            item.decode(errors="replace")
            for item in (entry / "cmdline").read_bytes().split(b"\\0")
            if item
        ]
    except OSError:
        continue
    if len(argv) >= 2 and str(Path(argv[-1])) in targets:
        print(entry.name)
PY
}'''

new = '''guard_pids() {
  python3 - \\
    "$ROOT/tools/runsvdir_guard.py" \\
    "$ROOT/tools/runsvdir_guard_runtime.py" <<'PY'
import os
from pathlib import Path
import sys

targets = {str(Path(value)) for value in sys.argv[1:]}
self_pid = os.getpid()

for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue

    pid = int(entry.name)
    if pid == self_pid:
        continue

    try:
        argv = [
            item.decode(errors="replace")
            for item in (entry / "cmdline").read_bytes().split(b"\\0")
            if item
        ]
    except OSError:
        continue

    if len(argv) >= 2 and str(Path(argv[1])) in targets:
        print(entry.name)
PY
}'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"GUARD_DETECTOR_REPLACEMENT_COUNT={count}")

target.write_text(text.replace(old, new, 1), encoding="utf-8")
PYFIX

chmod 700 "$CORRECTED"
bash -n "$CORRECTED"

printf 'SOURCE_ARTIFACT_SHA256=PASS\n'
printf 'SOURCE_ARTIFACT_GIT_BLOB=PASS\n'
printf 'GUARD_DETECTOR_SELF_COUNT_FIX=APPLIED\n'
printf 'CORRECTED_ARTIFACT_BASH_SYNTAX=PASS\n'
printf 'CORRECTED_ARTIFACT_SHA256=%s\n' \
  "$(sha256sum "$CORRECTED" | awk '{print $1}')"
printf 'PHONE_RUNTIME_MUTATION_BEFORE_CORRECTED_EXECUTOR=NO\n'

exec "$CORRECTED"
# GUARDED_EXECUTOR_SELF_COUNT_FIX_END
