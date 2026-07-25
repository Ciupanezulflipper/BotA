# Phase 5 Watcher Output Routing — 2026-07-22

## Status

Gate A ownership passed. The watcher service is running and manager-owned.

```text
WATCHER_ROUTING_PREFLIGHT=PASS
MANAGER_COUNT=1
MANAGER_PID=24052
WATCHER_RUNSV_COUNT=1
WATCHER_RUNSV_PID=24058
WATCHER_RUNSV_PPID=24052
WATCHER_WRAPPER_PID=24075
WATCHER_STATUS=run
```

## Routing evidence

The watcher service has no runit `log/` subservice:

```text
bota-watcher/log PRESENT=NO
bota-watcher/log/run PRESENT=NO
```

The watcher wrapper and current sleep child have stdout and stderr connected to `/dev/null`:

```text
PROCESS_FD1=/dev/null
PROCESS_FD2=/dev/null
WATCHER_OUTPUT_ROUTING=DEV_NULL
```

The run script explicitly writes service evidence to:

`$HOME/BotA/logs/cron.signals.log`

through:

```bash
LOG="${ROOT}/logs/cron.signals.log"
log() { printf ... | tee -a "${LOG}"; }
```

## Interpretation

- The watcher is not dead.
- The absence of a runit logger is intentional in the current service design.
- `/dev/null` stdout/stderr does not by itself prove evidence loss because the run script has an explicit file-log path.
- The exact watcher evidence candidate is `logs/cron.signals.log`.
- The earlier Phase 5 mistake was treating historical content from that file as current, not identifying the wrong file.
- Current evidence must come from a small tail anchored by the latest trusted-server marker.
- This is not classified as a new runtime error unless the exact file is absent, not advancing, or lacks current cycle evidence.

## Safety

- read-only audit;
- no service restart;
- no runtime mutation;
- no strategy or threshold change;
- no CSV or cache inspection.

## Next action

Read a compact current tail of `$HOME/BotA/logs/cron.signals.log` after Gate A. Return only the latest trusted-clock state and current EURUSD/GBPUSD evidence.
