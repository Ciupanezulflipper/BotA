# BotA Current Continuity State

Last updated: **2026-09-27 UTC**

This is the current operational handoff. Historical audits and strategy records remain preserved as dated evidence. Forward recovery scope is governed by `docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md`.

## Current authoritative status

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
PROFITLAB_SIGNAL_DISPLAY_REQUIRED=YES
PROFITLAB_COMMERCIAL_EXPANSION=NO
DUAL_DELIVERY_REQUIRED=TELEGRAM+PROFITLAB
PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=ACTIVE_SCANNING_BUT_USER_DELIVERY_BLOCKED
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
MODE=EXECUTION_RECOVERY
PR134_DEPLOYED=YES
PR134_MERGED=NO
THREE_PAIR_M15_SCAN=RUNNING
MARKET_DATA=UPDATING
PIPELINE=UPDATING
BOTA_R5_SHADOW=1
BOTA_REQUIRE_R5_SHADOW=1
REAL_TELEGRAM_SIGNAL_DELIVERY=BLOCKED_BY_SHADOW_BOUNDARY
REAL_PROFITLAB_SIGNAL_DELIVERY=BLOCKED_BY_SHADOW_BOUNDARY
REAL_DAILY_REPORT_DELIVERY=BLOCKED_BY_SHADOW_BOUNDARY
SUPABASE_SIDE_EFFECTS=SUPPRESSED_BY_SHADOW_BOUNDARY
STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO
RECOVERY_PRD=docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md
NEXT_ACTION=CLAUDE_CODE_SINGLE_WRITER_DUAL_DELIVERY_RECOVERY_THEN_ONE_ASTRA_CODEX_RED_TEAM
```

## Latest direct Hetzner proof — 2026-09-23 UTC

Read-only Termux→Hetzner evidence proved:

```text
CURRENT_RELEASE=/opt/bota/releases/d81c0a3da3363089ed200e264ae066fdf15fb5ba
BOTA_SERVICE=active
ActiveState=active
SubState=running
ExecMainStatus=0
NRestarts=0
ORCHESTRATOR_LIFECYCLE=RUNNING
ORCHESTRATOR_LIVENESS=True
RUNTIME_INSTANCE_ID=7a0284b0-7406-4a1b-91a8-eba0548e6169
LAST_LOOP_PROGRESS_UTC=2026-09-23T18:53:18.366554Z
FILES_UPDATED_SINCE_SEP19=64
ALERTS_CSV=UPDATING
PIPELINE_EVENTS=UPDATING
PROVIDER_DATA=UPDATING
BOTA_R5_SHADOW=1
BOTA_REQUIRE_R5_SHADOW=1
```

Therefore Hetzner is not dead and the scanner is not generally stopped.

## Proven delivery blocker

`r5_bootstrap/sitecustomize.py` is active when `BOTA_R5_SHADOW=1`. It:

- replaces sensitive Telegram/Supabase credentials with the R5 sentinel;
- suppresses Telegram and Supabase external side effects;
- returns deterministic synthetic success responses for intercepted paths;
- forces `HEARTBEAT_DRY_RUN=1`;
- forces `DAILY_SUMMARY_GATE_DRY_RUN=1`;
- forces `DAILY_SUMMARY_SEND=0`;
- forces `RUNTIME_HEALTH_PUSH_DRY_RUN=1`.

```text
DRY_RUN_ORIGIN=PROVEN_R5_SHADOW_BOOTSTRAP
DAILY_REPORT_CODE_DEFECT=NOT_PROVEN
HETZNER_RUNTIME_DEAD=NO
REAL_USER_DELIVERY_WORKING=NO
```

## Telegram credential state

A later attempted collect/report cutover stopped before runtime mutation because a recovered historical Telegram token failed Telegram `getMe` authentication.

```text
CUTOVER_COMPLETED=NO
R5_SHADOW_REMOVED=NO
RECOVERED_TELEGRAM_TOKEN=INVALID_OR_STALE
VALID_CURRENT_TELEGRAM_CREDENTIAL=UNRESOLVED
```

## ProfitLab path — verified 2026-09-27

The existing second delivery path does not need a new dashboard build.

Repository/Lovable inspection proved:

- `tools/profitlab_delivery.py` independently consumes accepted GREEN rows from `logs/alerts.csv` using its own durable cursor and retries publication;
- `tools/supabase_publish.py` writes ACTIVE signals into the shared Supabase `public.signals` table with deduplication;
- deployed `vps_orchestrator.py` schedules `profitlab_delivery.py` every minute;
- `tools/signal_closer.py` updates signal lifecycle/result fields in Supabase;
- the published Lovable ProfitLab project uses the same Supabase project, supports EURUSD/GBPUSD/USDJPY, subscribes to `signals` INSERT/UPDATE changes, and renders ACTIVE/CLOSED/CANCELLED outcomes.

Historical Package 7 evidence also proves the ProfitLab cursor/reconciliation mechanism operated successfully before the later R5 shadow cutover.

The current defect is therefore not “ProfitLab does not exist.” The current defect is that R5 shadow suppresses the real Supabase network path, while Telegram is also suppressed.

## Dual-delivery recovery decision — 2026-09-27

A qualified signal must fan out to **both** user-visible sinks:

```text
qualified signal
   ├─→ Telegram
   └─→ Supabase public.signals → ProfitLab
```

Failure isolation is part of acceptance:

```text
TELEGRAM_FAILURE_MUST_NOT_BLOCK_PROFITLAB=YES
PROFITLAB_FAILURE_MUST_NOT_BLOCK_TELEGRAM=YES
PROFITLAB_RETRY_MUST_NOT_DUPLICATE_TELEGRAM=YES
BOTH_HEALTHY_EXACTLY_ONCE_PER_SINK=YES
```

## Historical natural signal evidence

The September 15 natural-runtime proof remains valid for that inspected window:

```text
MARKET_OPEN_COMPLETED_CYCLES=212
EURUSD_M15_DECISIONS=212
GBPUSD_M15_DECISIONS=212
USDJPY_M15_DECISIONS=212
THREE_PAIR_COMPLETE_CYCLES=212
POST_REOPEN_NON_FILTER_REJECTED=0
TELEGRAM_RESULTS={not_attempted:636}
SUPABASE_RESULTS={not_attempted:636}
```

No genuine qualified signal occurred in that sampled window. Even a zero-signal day must still deliver the real daily Telegram report after recovery.

## Acceptance gate

BotA is not finished until all are proven:

1. three-pair M15 scanning;
2. fresh/timeframe-correct market data;
3. auditable decision every scan;
4. genuine qualified signal reaches real Telegram;
5. the same qualified signal becomes visible in ProfitLab;
6. either sink can fail without blocking the other;
7. ProfitLab catch-up does not duplicate Telegram;
8. SL/TP lifecycle/result is visible in ProfitLab and Telegram closure is delivered;
9. zero-signal daily report reaches real Telegram;
10. clean restart recovery and independent deduplication;
11. no forced production signal required for natural acceptance;
12. GitHub + Obsidian match deployed runtime.

## AI execution rule

```text
CHATGPT=CONTROL_PLANE_AND_EVIDENCE_RECONCILER
CLAUDE_CODE=PRIMARY_IMPLEMENTATION_WRITER
CURSOR=EDITOR_VIEWER_OR_EXPLICIT_FALLBACK_WRITER
ASTRA_CODEX=ONE_BOUNDED_FINAL_RED_TEAM_REVIEW
CONCURRENT_IMPLEMENTATION_WRITERS=NO
```

Claude Code is selected because this repair spans Python, Bash, R5 network/credential interception, systemd/orchestrator behavior, Telegram, Supabase and crash/failure semantics across two sinks. Cursor must not concurrently rewrite the same candidate.

## Canonical records

Current forward contract:

- `docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md`

Still-valid historical/current evidence:

- `audits/BOTA_OPERATING_SCOPE_AND_TELEGRAM_PRESENTATION_2026-09-11.md`
- `audits/BOTA_PR134_POST_DEPLOY_RUNTIME_PROOF_2026-09-15.md`
- `audits/PACKAGE7_RUNTIME_AND_PROFITLAB_CLOSURE_2026-08-17.md`
- `audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`
- `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Exactly one next action

Create a fresh local recovery workspace from the exact deployed PR #134 head `d81c0a3da3363089ed200e264ae066fdf15fb5ba`, then launch **Claude Code** there as the sole implementation writer for the dual-delivery recovery. Do not use the broken `Cursor-BotA-Audit/BotA` checkout, do not tune strategy, and do not mutate Hetzner until an exact candidate is reviewed and explicitly authorized.