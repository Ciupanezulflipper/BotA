# BotA — PR #134 Post-Deploy Runtime Proof

Date: **2026-09-15 UTC**
Status: **NATURAL RUNTIME PASS / DAILY TELEGRAM SUMMARY SEND NOT YET PROVEN**

## Scope

This record captures the read-only Hetzner evidence collected after deployment of PR #134 head `d81c0a3da3363089ed200e264ae066fdf15fb5ba`.

No deployment, merge, forced signal, strategy change, threshold change, pair/timeframe change, or production mutation was performed by the proof command.

## GitHub PR state checked 2026-09-15

```text
PR=134
STATE=OPEN
DRAFT=YES
MERGED=NO
MERGEABLE=YES
HEAD_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
BASE_SHA=e9e6bc31b1a0bba74a9947060372f7bd19ddaac3
```

PR #134 remains unmerged. Deployment authorization did not authorize merge.

## Deployed identity proof

```text
CURRENT_RELEASE=/opt/bota/releases/d81c0a3da3363089ed200e264ae066fdf15fb5ba
CURRENT_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
DEPLOYED_SHA_GATE=PASS
MANIFEST_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
MANIFEST_TREE=c083de54f407061d6b744b26b51e1f3fab4212a2
MANIFEST_CONFIG_FINGERPRINT=c9b636e1597743df11daa439f37b311e2434c7bc2ce7589e306739b6207e1b7b
MANIFEST_SHA_GATE=PASS
MANIFEST_TREE_GATE=PASS
```

## Service and orchestrator proof

```text
BOTA_SERVICE=active
ActiveState=active
SubState=running
MainPID=1099297
ExecMainStatus=0
SERVICE_GATE=PASS

HEALTH_RELEASE_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
HEALTH_LIFECYCLE=RUNNING
HEALTH_PROCESS_LIVENESS=True
HEALTH_RUNTIME_INSTANCE_ID=97a288fa-1606-4d89-9049-b4e96a6770f9
HEALTH_LAST_LOOP_PROGRESS_UTC=2026-09-15T11:36:41.066934Z
ORCHESTRATOR_SHA_GATE=PASS
ORCHESTRATOR_LIFECYCLE_GATE=PASS
ORCHESTRATOR_LIVENESS_GATE=PASS
```

## Natural market-open proof

Evidence window begins at the FX reopen anchor `2026-09-13T21:05:00Z`.

```text
POST_REOPEN_EVENTS=2390
MALFORMED_LEDGER_ROWS=0
MARKET_OPEN_COMPLETED_CYCLES=212
MARKET_OPEN_TERMINAL_OUTCOMES={"EVALUATED_REJECTED":212}
EURUSD_M15_DECISIONS=212
GBPUSD_M15_DECISIONS=212
USDJPY_M15_DECISIONS=212
THREE_PAIR_COMPLETE_CYCLES=212
THREE_PAIR_SCAN_GATE=PASS
NATURAL_RUNTIME_GATE=PASS
TELEGRAM_RESULTS={"not_attempted":636}
SUPABASE_RESULTS={"not_attempted":636}
POST_REOPEN_NON_FILTER_REJECTED=0
```

Latest observed decision timestamp for all three pairs was `2026-09-15T11:35:00Z` using provider `engine_a3`.

Interpretation:

- natural market-open watcher execution is proven under the exact deployed PR #134 head;
- all three configured M15 pairs are being evaluated together;
- the ledger contains no malformed rows in the inspected post-reopen window;
- every observed post-reopen decision was rejected by policy, so Telegram and Supabase delivery were correctly not attempted;
- zero qualified signals in this window is not evidence of a delivery failure;
- natural qualified-signal delivery, duplicate suppression, and crash-consistent Telegram/Supabase behavior remain conditionally unproven until a genuine qualifying setup occurs.

## Daily report render proof

A read-only render for `2026-09-15` produced:

```text
Runtime: ONLINE
Market-open watcher cycles: 56
EUR/USD: 56 scans, 0 qualified
GBP/USD: 56 scans, 0 qualified
USD/JPY: 56 scans, 0 qualified
Qualified setups: 0
Telegram confirmed: 0
All 3 pairs observed: YES
Runtime issues: None observed
BOTA STATUS: NORMAL
TELEGRAM_SEND=SKIPPED
```

Therefore the modern daily-report renderer is functioning against live production evidence without sending Telegram during the proof command.

## Daily summary gate finding

No `daily_summary_sent_*.ok` marker was present.

The production gate log showed:

```text
2026-09-12 20:10 UTC GATE_DRY_RUN would_send=YES
2026-09-13 20:10 UTC GATE_DRY_RUN would_send=YES
2026-09-14 20:10 UTC GATE_DRY_RUN would_send=YES
```

The deployed `tools/daily_summary_server_gate.sh` only emits `GATE_DRY_RUN` when ambient `DAILY_SUMMARY_GATE_DRY_RUN=1` is present. The versioned `config/production-vps.env` does not define that key. The VPS orchestrator inherits ambient process environment before overlaying the frozen strategy-policy allowlist.

Therefore:

```text
DAILY_REPORT_RENDER=PASS
DAILY_REPORT_GATE_TIMING=PASS
DAILY_REPORT_ACTUAL_TELEGRAM_SEND=NOT_PROVEN
DAILY_SUMMARY_SENT_MARKER=ABSENT
DAILY_SUMMARY_RUNTIME_MODE=DRY_RUN
DRY_RUN_ORIGIN=RUNTIME_AMBIENT_ENVIRONMENT_NOT_YET_LOCATED
```

This is a presentation/reporting-path issue, not a strategy/scoring defect.

## Current operating state

```text
BOTA_EDGE_STATUS=UNVALIDATED
PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=PROVEN_ACTIVE
PR134_DEPLOYED=YES
PR134_MERGED=NO
NATURAL_MARKET_OPEN_RUNTIME_GATE=PASS
THREE_PAIR_M15_SCAN_GATE=PASS
DAILY_REPORT_RENDER=PASS
DAILY_REPORT_ACTUAL_SEND=PENDING
STRATEGY_TUNING=NO
THRESHOLD_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO
MODE=COLLECT_AND_REPORT
```

## Exact next proof step

Locate the production source of `DAILY_SUMMARY_GATE_DRY_RUN=1` using read-only runtime evidence. Do not change or remove it until its provenance and intended safety role are established.

After provenance is established, any mutation that enables real daily Telegram sending requires an explicit production-change authorization.

Do not force a qualifying signal. Genuine qualified-signal delivery/dedup/crash-consistency proof must remain natural.