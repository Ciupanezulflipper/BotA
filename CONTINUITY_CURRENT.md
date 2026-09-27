# BotA Current Continuity State

Last updated: **2026-09-27 UTC**

This is the current operational handoff. Historical audits and strategy records remain preserved as dated evidence. Forward recovery scope is governed by `docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md`.

## Current authoritative status

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
COMMERCIAL_PROFITLAB=NO
PRIVATE_PROFITLAB_ANALYTICS=YES
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
REAL_DAILY_REPORT_DELIVERY=BLOCKED_BY_SHADOW_BOUNDARY
SUPABASE_SIDE_EFFECTS=SUPPRESSED_BY_SHADOW_BOUNDARY
STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO
RECOVERY_PRD=docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md
NEXT_ACTION=CURSOR_CLAUDE_IMPLEMENT_MINIMUM_RECOVERY_PATH_THEN_ONE_ASTRA_CODEX_RED_TEAM
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

The old statement `DRY_RUN_ORIGIN=UNKNOWN` is superseded.

```text
DRY_RUN_ORIGIN=PROVEN_R5_SHADOW_BOOTSTRAP
DAILY_REPORT_CODE_DEFECT=NOT_PROVEN
HETZNER_RUNTIME_DEAD=NO
REAL_USER_DELIVERY_WORKING=NO
```

## Telegram credential state

A later attempted collect/report cutover was designed but did not complete. It stopped before runtime mutation because a recovered historical Telegram token failed Telegram `getMe` authentication.

```text
CUTOVER_COMPLETED=NO
R5_SHADOW_REMOVED=NO
RECOVERED_TELEGRAM_TOKEN=INVALID_OR_STALE
VALID_CURRENT_TELEGRAM_CREDENTIAL=UNRESOLVED
```

Do not treat that failed cutover as a production change.

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

No genuine qualified signal occurred in that sampled window. This is separate from the current delivery blocker: even a zero-signal day must still deliver a real daily report under the recovery PRD.

## Recovery decision — 2026-09-27

Do not continue broad archaeology or preserve nonessential architecture by default.

The product objective is now bounded to:

```text
EURUSD / GBPUSD / USDJPY
→ M15 scan
→ frozen strategy decision
→ auditable terminal decision
→ genuine qualified setup → real Telegram
→ SL/TP closure → real Telegram
→ real daily report
```

Everything outside this path must justify its existence.

## Acceptance gate

BotA is not finished until all are proven:

1. three-pair M15 scanning;
2. fresh/timeframe-correct market data;
3. auditable decision every scan;
4. genuine qualified signal reaches real Telegram;
5. SL/TP closure reaches real Telegram;
6. zero-signal daily report reaches real Telegram;
7. clean restart recovery;
8. duplicate suppression;
9. no forced production signal required;
10. GitHub + Obsidian match deployed runtime.

## AI execution rule

```text
CHATGPT=CONTROL_PLANE_AND_EVIDENCE_RECONCILER
CURSOR_CLAUDE_CODE=PRIMARY_IMPLEMENTATION_LANE
ASTRA_CODEX=ONE_BOUNDED_FINAL_RED_TEAM_REVIEW
CONCURRENT_IMPLEMENTATION_WRITERS=NO
```

No AI carousel. If Astra finds a concrete defect, return one bounded repair to Cursor and re-run only the affected proof.

## Canonical records

Current forward contract:

- `docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md`

Still-valid historical/current evidence:

- `audits/BOTA_OPERATING_SCOPE_AND_TELEGRAM_PRESENTATION_2026-09-11.md`
- `audits/BOTA_PR134_POST_DEPLOY_RUNTIME_PROOF_2026-09-15.md`
- `audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`
- `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Exactly one next action

Use Cursor/Claude Code against the current repository and latest Hetzner evidence to implement the **minimum recovery path required by the 2026-09-27 PRD**. Do not tune strategy, add pairs, merge PR #134 merely for cleanup, or create another broad audit cycle.