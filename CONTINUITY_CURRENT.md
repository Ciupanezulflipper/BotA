# BotA Current Continuity State

Last updated: **2026-09-15 UTC**

This is the current operational handoff. Historical strategy-closure and measurement-pilot records remain preserved as dated evidence; current runtime truth is established by the 2026-09-15 post-deploy proof.

## Current authoritative status

```text
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
COMMERCIAL_PROFITLAB=NO
PRIVATE_PROFITLAB_ANALYTICS=YES
PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=PROVEN_ACTIVE
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
MODE=COLLECT_AND_REPORT
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
NEXT_ACTION=LOCATE_DAILY_SUMMARY_DRY_RUN_RUNTIME_ORIGIN_READ_ONLY
FURTHER_BROAD_AI_REVIEW=STOP
```

## Current canonical records

- `audits/BOTA_OPERATING_SCOPE_AND_TELEGRAM_PRESENTATION_2026-09-11.md`
- `audits/BOTA_PR134_POST_DEPLOY_RUNTIME_PROOF_2026-09-15.md`

Historical records remain authoritative for their dated conclusions:

- `audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`
- `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## PR #134 deployment identity

PR #134 remains open, draft, mergeable, and unmerged.

```text
PR=134
HEAD_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
DEPLOYED_SHA=d81c0a3da3363089ed200e264ae066fdf15fb5ba
DEPLOYED_TREE=c083de54f407061d6b744b26b51e1f3fab4212a2
EFFECTIVE_CONFIG_FINGERPRINT=c9b636e1597743df11daa439f37b311e2434c7bc2ce7589e306739b6207e1b7b
PR134_MERGED=NO
```

Deployment and merge remain separate states. The existing deployment authorization did not authorize merging PR #134.

## Runtime proof — 2026-09-15

Read-only Hetzner evidence proved:

```text
BOTA_SERVICE=active
SERVICE_GATE=PASS
HEALTH_LIFECYCLE=RUNNING
HEALTH_PROCESS_LIVENESS=True
ORCHESTRATOR_SHA_GATE=PASS
ORCHESTRATOR_LIFECYCLE_GATE=PASS
ORCHESTRATOR_LIVENESS_GATE=PASS
POST_REOPEN_EVENTS=2390
MALFORMED_LEDGER_ROWS=0
MARKET_OPEN_COMPLETED_CYCLES=212
EURUSD_M15_DECISIONS=212
GBPUSD_M15_DECISIONS=212
USDJPY_M15_DECISIONS=212
THREE_PAIR_COMPLETE_CYCLES=212
THREE_PAIR_SCAN_GATE=PASS
NATURAL_RUNTIME_GATE=PASS
POST_REOPEN_NON_FILTER_REJECTED=0
```

All 212 natural market-open cycles in the inspected post-reopen window completed with three-pair M15 decision evidence. All terminal watcher outcomes were `EVALUATED_REJECTED`; no genuine qualifying setup occurred in the inspected window.

Therefore the old `CURRENT_HETZNER_RUNTIME_STATE=UNPROVEN` status is superseded.

## Telegram and daily-report state

The read-only daily-report renderer produced a healthy modern report for 2026-09-15:

```text
Runtime: ONLINE
Market-open watcher cycles: 56
EUR/USD: 56 scans, 0 qualified
GBP/USD: 56 scans, 0 qualified
USD/JPY: 56 scans, 0 qualified
Qualified setups: 0
All 3 pairs observed: YES
Runtime issues: None observed
TELEGRAM_SEND=SKIPPED
```

This proves report rendering, not actual Telegram delivery.

The daily-summary gate log contains:

```text
2026-09-12 20:10 UTC GATE_DRY_RUN would_send=YES
2026-09-13 20:10 UTC GATE_DRY_RUN would_send=YES
2026-09-14 20:10 UTC GATE_DRY_RUN would_send=YES
```

No `daily_summary_sent_*.ok` marker was observed.

The deployed gate enters this path only when `DAILY_SUMMARY_GATE_DRY_RUN=1` is present. That key is not part of the frozen `config/production-vps.env` strategy policy, so its runtime provenance still needs to be located.

```text
DAILY_REPORT_GATE_TIMING=PASS
DAILY_REPORT_RENDER=PASS
DAILY_REPORT_ACTUAL_TELEGRAM_SEND=NOT_PROVEN
DAILY_SUMMARY_RUNTIME_MODE=DRY_RUN
DRY_RUN_ORIGIN=UNKNOWN_PENDING_READ_ONLY_PROVENANCE_CHECK
```

Do not silently disable the dry-run setting. Enabling real daily Telegram sending is a production mutation and requires explicit owner authorization after provenance is established.

## Signal-delivery proof status

Because all 636 post-reopen pair decisions were rejected by policy:

```text
TELEGRAM_RESULTS={not_attempted:636}
SUPABASE_RESULTS={not_attempted:636}
POST_REOPEN_NON_FILTER_REJECTED=0
```

This is consistent with healthy no-signal operation. It does not yet prove the new presentation path on a genuine qualified signal, duplicate suppression under a genuine send, or crash-consistent Telegram/Supabase behavior under the deployed head.

Do not force a signal to close those gates.

## Strategy / research direction

The historical corpus result remains preserved:

```text
HISTORICAL_RETROSPECTIVE_VALIDATION_PROJECT=CLOSED
HISTORICAL_CORPUS_GATE_RESULT=FAIL_195_LT_400
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
```

BotA is now in prospective collection mode. Several months of trustworthy evidence are required before strategy tuning is reconsidered.

Primary future analysis remains based on Net R after realistic costs where measurable, pair, score band, ADX/regime, direction, session/time of day, rejection reasons, delivery reliability, missing scans, and data-quality incidents.

## Android / Termux

Android remains control/observation only and must not become a second scanner.

```text
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
PRIMARY_RUNTIME_TARGET=HETZNER
```

Termux now has successful read-only SSH access to Hetzner using the phone's existing `id_ed25519` key. This changes access capability only; it does not change BotA execution authority.

## Exactly one next action

Perform a **read-only provenance check** for `DAILY_SUMMARY_GATE_DRY_RUN=1` on the Hetzner runtime.

Do not redeploy, merge PR #134, change strategy/config, disable dry-run, or force a signal during that check.