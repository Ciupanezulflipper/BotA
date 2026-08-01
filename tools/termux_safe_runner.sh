#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/BotA"
PACKAGE="${1:-}"

cd "$ROOT" || {
  echo "SAFE_RUNNER_RESULT=FAIL_CANNOT_CD_BOTA"
  exit 20
}

cat "$ROOT/audits/ERROR_LOG.md"

if [ -z "$PACKAGE" ] || [ ! -f "$PACKAGE" ]; then
  echo "SAFE_RUNNER_RESULT=FAIL_PACKAGE_MISSING"
  exit 21
fi

case "$PACKAGE" in
  "$ROOT"/audits/packages/*.sh) ;;
  *)
    echo "SAFE_RUNNER_RESULT=FAIL_PACKAGE_OUTSIDE_ALLOWED_DIRECTORY"
    exit 22
    ;;
esac

bash -n "$PACKAGE"
SYNTAX_RC=$?

if [ "$SYNTAX_RC" -ne 0 ]; then
  echo "SAFE_RUNNER_RESULT=FAIL_PACKAGE_SYNTAX"
  exit 23
fi

bash "$PACKAGE"
PACKAGE_RC=$?

cd "$ROOT" || true
echo "PACKAGE_EXIT_CODE=$PACKAGE_RC"
echo "BOTA_ADDRESS=$PWD"
echo "TERMUX_PARENT_SESSION_PRESERVED=YES"

if [ "$PACKAGE_RC" -eq 0 ]; then
  echo "SAFE_RUNNER_RESULT=PASS"
else
  echo "SAFE_RUNNER_RESULT=PACKAGE_REPORTED_FAILURE"
fi

exit "$PACKAGE_RC"
