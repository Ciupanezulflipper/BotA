# BotA Current Continuity State

Last updated: **2026-10-06 UTC**

This is the current operational handoff. Historical audits and strategy records remain preserved as dated evidence. The latest production activation proof is `audits/BOTA_HETZNER_PRODUCTION_ACTIVATION_2026-10-06.md`.

## Current authoritative status

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
PROFITLAB_SIGNAL_DISPLAY_REQUIRED=YES
PROFITLAB_COMMERCIAL_EXPANSION=NO
DUAL_DELIVERY_REQUIRED=TELEGRAM+PROFITLAB
PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=ACTIVE_ON_4424518
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
MODE=EXECUTION_RECOVERY_ACCEPTANCE

DEPLOYED_RELEASE=4424518e7b42ecf2a070967d626a9ac86bf04d53
DEPLOYED_TREE=9e76b0b37012a2276cd36301e3e7267b1b6674d8
DEPLOYMENT_PHASE=COMPLETE
DEPLOYMENT_HEALTHY=YES
ROLLBACK_USED=NO
BOTA_SERVICE=active
BOTA_SERVICE_ENABLED=enabled
TARGET_RUNTIME_INSTANCE_ID=71c3cc1e-a1be-4bc6-8a23-3738eb70ba35

THREE_PAIR_M15_SCAN=RUNNING
MARKET_DATA=UPDATING
PROVIDER_CONTRACT=YAHOO
SIGNAL_CLOSER=RUNNING
PROFITLAB_DELIVERY_WORKER=RUNNING_AND_CAUGHT_UP_AT_SAMPLED_CHECKPOINT
LIVE_DELIVERY_CONTRACT=PASS

TELEGRAM_CREDENTIAL_VALIDATED=YES
SUPABASE_SERVICE_CREDENTIAL_VALIDATED=YES
REAL_TELEGRAM_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
REAL_PROFITLAB_SIGNAL_POST_ACTIVATION=NOT_YET_OBSERVED
DELIVERY_NOT_OBSERVED_REASON=NO_QUALIFIED_SIGNAL_IN_SAMPLED_POST_ACTIVATION_CYCLES

BOTA_R5_SHADOW=1
BOTA_REQUIRE_R5_SHADOW=1
PARENT_SIDE_EFFECTS_ENABLED=NO
APPROVED_CHILD_LIVE_DELIVERY=SCOPED_CREDENTIALS_ONLY

STRATEGY_TUNING=NO
PAIR_CHANGES=NO
TIMEFRAME_CHANGES=NO
FORCED_SIGNAL_GENERATION=NO
```

## Latest direct Hetzner proof — 2026-10-06 UTC

Production deployment completed successfully:

```text
PREVIOUS_RELEASE=d81c0a3da3363089ed200e264ae066fdf15fb5ba
CURRENT_RELEASE=/opt/bota/releases/4424518e7b42ecf2a070967d626a9ac86bf04d53
DEPLOYMENT_ID=60de921f-1020-4e55-b6ff-0b03d3548e63
DEPLOYMENT_PHASE=COMPLETE
HEALTHY=true
SERVICE_ACTIVE=active
SERVICE_ENABLED=enabled
MAINPID=4104125
```

The release is live on Hetzner and configured to start automatically after reboot.

## Provider/lifecycle proof

The provider/lifecycle repair is active with Yahoo as the production candle provider.

Post-activation evidence showed fresh Yahoo cache/candle/indicator updates for EURUSD, GBPUSD and USDJPY across M15/H1/H4/D1, plus advancing provider-accounting state.

The signal closer ran after activation with:

```text
provider=yahoo
dry_run=False
ACTIVE_SIGNALS=0
TELEGRAM_RETRY_CANDIDATES=0
```

No historical pending Telegram closure retry files were present immediately before activation.

## Watcher proof

Natural market-open watcher cycles completed at 08:45, 08:50 and 08:55 UTC on 2026-10-06.

Each sampled cycle evaluated:

- EURUSD M15
- GBPUSD M15
- USDJPY M15

Each sampled cycle completed with:

```text
run_rc=0
terminal_outcome=EVALUATED_REJECTED
```

No sampled candidate qualified under the frozen strategy, so the ledger correctly recorded:

```text
telegram_result=not_attempted
supabase_result=not_attempted
```

This is not a delivery failure. It means there was no qualified signal to send.

## Telegram and ProfitLab delivery state

Credential validation and runtime contract:

```text
TELEGRAM_API_TOKEN_VALIDATED=YES
TELEGRAM_CHAT_ROUTE_VALIDATED=YES
SUPABASE_SERVICE_KEY_VALIDATED=YES
LIVE_DELIVERY_FILE=/etc/bota/live-delivery.env
LIVE_DELIVERY_FILE_MODE=600
LIVE_DELIVERY_FILE_OWNER=bota:bota
LIVE_DELIVERY_CONTRACT=PASS
```

The ProfitLab delivery cursor advanced after activation and was caught up to the source at the sampled checkpoint:

```json
{"offset": 2896918, "schema_version": "1.0", "source_size": 2896918}
```

Current interpretation:

```text
TELEGRAM_DELIVERY_PATH=ARMED
PROFITLAB_DELIVERY_PATH=ARMED
REAL_POST_ACTIVATION_TELEGRAM_SIGNAL_PROVEN=NO
REAL_POST_ACTIVATION_PROFITLAB_SIGNAL_PROVEN=NO
WHY=NO_QUALIFIED_SIGNAL_OCCURRED_YET
```

Do not claim end-to-end delivery is proven until one real qualified signal or one supported non-trading dual-sink smoke test is observed through both sinks.

## R5 shadow interpretation

The parent orchestrator remains R5-shadowed and reports `side_effects_enabled=false`. This is intentional.

The repaired design keeps the parent fail-closed while only the approved live jobs receive scoped credentials:

- watcher
- profitlab_delivery
- closer
- daily_summary_server_gate

Therefore `r5_shadow=true` at the parent is not evidence that those approved child delivery paths are disabled.

## Dual-delivery recovery contract

A qualified signal must fan out to both user-visible sinks:

```text
qualified signal
   ├─→ Telegram
   └─→ Supabase public.signals → ProfitLab
```

Failure isolation remains required:

```text
TELEGRAM_FAILURE_MUST_NOT_BLOCK_PROFITLAB=YES
PROFITLAB_FAILURE_MUST_NOT_BLOCK_TELEGRAM=YES
PROFITLAB_RETRY_MUST_NOT_DUPLICATE_TELEGRAM=YES
BOTH_HEALTHY_EXACTLY_ONCE_PER_SINK=YES
```

## Acceptance gate

BotA is not fully accepted until all are proven:

1. three-pair M15 scan;
2. fresh/timeframe-correct market data;
3. auditable terminal decision every scan;
4. genuine qualified signal reaches real Telegram;
5. the same qualified signal becomes visible in ProfitLab;
6. either sink can fail without blocking the other;
7. retries/restarts do not duplicate either sink;
8. closure/result appears in ProfitLab and Telegram closure is delivered;
9. zero-signal daily report reaches real Telegram;
10. clean restart recovery and independent deduplication;
11. no forced production trading signal required for natural acceptance;
12. GitHub + Obsidian match deployed runtime.

Current closure position:

```text
HETZNER_RUNTIME=PASS
PROVIDER_LIFECYCLE=PASS
CREDENTIAL_CONTRACT=PASS
NATURAL_SCAN_EXECUTION=PASS
REAL_DUAL_SINK_SIGNAL_DELIVERY=PENDING_EMPIRICAL_PROOF
```

## AI execution rule

```text
CHATGPT=CONTROL_PLANE_AND_EVIDENCE_RECONCILER
CLAUDE_CODE=PRIMARY_IMPLEMENTATION_WRITER
CURSOR=EDITOR_VIEWER_OR_EXPLICIT_FALLBACK_WRITER
ASTRA_CODEX=ONE_BOUNDED_FINAL_RED_TEAM_REVIEW
CONCURRENT_IMPLEMENTATION_WRITERS=NO
```

Do not start a new broad audit. Use one bounded acceptance check at a time.

## Canonical records

Current activation proof:

- `audits/BOTA_HETZNER_PRODUCTION_ACTIVATION_2026-10-06.md`

Recovery contract:

- `docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md`

Still-valid historical/current evidence:

- `audits/BOTA_OPERATING_SCOPE_AND_TELEGRAM_PRESENTATION_2026-09-11.md`
- `audits/BOTA_PR134_POST_DEPLOY_RUNTIME_PROOF_2026-09-15.md`
- `audits/PACKAGE7_RUNTIME_AND_PROFITLAB_CLOSURE_2026-08-17.md`
- `audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`
- `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Exactly one next action

Obtain one bounded dual-sink delivery proof without changing strategy. Prefer an existing supported non-trading delivery smoke-test path if one exists; otherwise observe the next natural qualified signal. Do not manufacture or force a production trading signal solely to satisfy acceptance.
