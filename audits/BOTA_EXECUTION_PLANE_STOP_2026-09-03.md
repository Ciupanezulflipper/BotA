# BotA Execution Plane Stop — 2026-09-03

## Purpose

Final operational decommission record for the closed BotA project. This action stops execution only; it does not delete code, logs, evidence, strategy history, or change strategy logic.

## Pre-stop inventory

Six BotA runit services were confirmed active:

- `bota-closer`
- `bota-heartbeat`
- `bota-shadow`
- `bota-supervisor`
- `bota-updater`
- `bota-watcher`

The crontab still contained the BotA runtime block plus the one-minute native watchdog guard capable of ensuring/restarting BotA services. A separate `dividend-capture-scanner` cron block was present and explicitly outside BotA scope.

## Decommission order

The stop was performed in this order:

1. Back up the existing crontab.
2. Remove only the BotA runtime cron block and BotA native watchdog guard block.
3. Verify the separate dividend-capture-scanner cron entry remained present.
4. Verify zero active BotA cron commands remained.
5. Terminate any in-flight BotA native watchdog guard.
6. Create runit `down` sentinels for all six BotA services and stop them.
7. Run a final read-only proof of runit, cron, process, and dividend-scanner state.

## Final observed proof

```text
bota-closer=DOWN
bota-heartbeat=DOWN
bota-shadow=DOWN
bota-supervisor=DOWN
bota-updater=DOWN
bota-watcher=DOWN

ALL_SIX_DOWN_SENTINELS=PRESENT
ACTIVE_BOTA_CRON=0
BOTA_WORKLOAD_PROCESSES=0
DIVIDEND_SCANNER_CRON_PRESERVED=YES

BOTA_EXECUTION_PLANE=STOPPED
BOTA_FILES_DELETED=NO
BOTA_STRATEGY_CHANGED=NO
```

Local evidence was also preserved on the phone at:

`audits/BOTA_EXECUTION_PLANE_STOP_2026-09-03.txt`

## Scope and interpretation

This record proves BotA's Android/Termux execution plane was stopped at the time of the final verification. It does not claim the Android wall-clock defect was corrected; that remains a separate device/OS issue. It does not authorize any further BotA strategy validation, runtime investigation, delivery archaeology, deployment, or threshold changes.

The separate dividend-capture-scanner was intentionally preserved and must not be treated as part of BotA decommissioning.

## Final state

```text
BOTA_STRATEGY_PROJECT=CLOSED
BOTA_OPERATIONAL_FORENSICS=CLOSED
BOTA_EXECUTION_PLANE=STOPPED
DELIVERY_ROW_ARCHAEOLOGY=STOP
FURTHER_BOTA_RUNTIME_INVESTIGATION=NO
STRATEGY_REOPENING=NO
```
