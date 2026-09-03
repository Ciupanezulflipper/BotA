# BotA Chat Handoff

Last updated: **2026-09-04 UTC**

Read this first in any new AI session before proposing BotA work.

## Current grounded answer

```text
BOTA_EDGE_STATUS=UNVALIDATED
BOTA_SHADOW_RESEARCH=REOPENED_BY_OWNER
HISTORICAL_RETROSPECTIVE_VALIDATION_PROJECT=CLOSED
HISTORICAL_CORPUS_GATE_RESULT=FAIL_195_LT_400
LIVE_MONEY_TRADING=NO
COMMERCIAL_PROFITLAB=NO
PRIVATE_PROFITLAB_ANALYTICS=YES
PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=UNPROVEN
ANDROID_ACTIVE_SCANNER=NO
NEXT_PHASE=STAGE_0_MEASUREMENT_PILOT
PILOT_STARTED=NO
STRATEGY_TUNING_DURING_PILOT=NO
NEXT_ACTION=READ_ONLY_HETZNER_FORENSIC_INSPECTION
FURTHER_BROAD_AI_REVIEW=STOP
```

Canonical current record:

`audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`

Historical closure record:

`audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## What changed on 2026-09-04

The owner clarified that the project intent was to debug BotA until it runs reliably and continue collecting prospective signals so the strategy can be evaluated from future evidence. The prior closure was too broad because it turned a failed historical corpus-sufficiency gate into a permanent stop on future shadow collection.

The historical result remains intact:

```text
POLICY_B_ACCEPTED=195
PRE_REGISTERED_KILL_THRESHOLD=400
HISTORICAL_CORPUS_GATE=FAIL
```

But current action is now:

```text
SHADOW_RESEARCH=AUTHORIZED
LIVE_TRADING=NO
CONFIRMATORY_TEST_NOW=NO
MEASUREMENT_PILOT_FIRST=YES
```

## Final audit findings that must survive handoff

The final role-specific audit cycle used Claude, Gemini, Grok, DeepSeek and Perplexity.

Do not re-run the broad audit loop unless a concrete contradiction is found.

Durable conclusions:

- a new frozen single-hypothesis prospective test is statistically legitimate;
- historical Bonferroni is not automatically carried into a completely new prospective dataset;
- no fixed N of 400, 500, 682 or 1446 is currently justified;
- Net R after realistic execution costs is the preferred future scientific endpoint, not raw win rate;
- exact sequential success/futility boundaries are not yet derived;
- model price, fixed 1-pip costs and binary +2R/-1R assumptions are insufficient for final confirmation;
- EURUSD/GBPUSD and temporally overlapping trades may be dependent;
- M15 same-candle TP/SL ordering is ambiguous without lower-timeframe evidence;
- Telegram API success does not prove a human saw the message;
- measurement integrity must be proven before confirmatory collection;
- the external review stage is complete.

## Repository cross-check

Do not blindly repeat DeepSeek's claim that BotA lacks all observability infrastructure.

Current repository evidence already includes:

- bounded watcher-cycle reconciliation via `tools/watcher_cycle_ledger.py`;
- append-only pipeline event evidence via `tools/pipeline_ledger.py`;
- UUID event IDs;
- process-shared `flock`;
- UTC plus monotonic/boot-aware timing;
- atomic compact state updates;
- fail-closed stale-candle checks in the watcher.

Do not assume a rewrite is required.

Repository evidence also confirms same-candle TP-first behavior exists and is documented as potentially optimistic.

## Stage 0 contract

Allowed: measurement/logging/evidence hardening only.

Not allowed:

- change Policy B;
- change ADX/RSI/score thresholds;
- change pair/timeframe scope;
- change higher-timeframe confirmation logic;
- change TP/SL strategy rules;
- tune the baseline from weekly performance.

Pilot data does **not** count toward the future confirmatory sample.

Pilot completion is based on proof of completeness, identity, closed-bar integrity, provider/config stability, execution-price evidence, publication timing, resolver integrity, ambiguity handling, idempotency and reconciliation — not on an arbitrary signal count.

## Hetzner

Historical evidence:

```text
R5=NO_SIDE_EFFECT_SHADOW_ENGINEERING
PRODUCTION_CUTOVER=NOT_COMPLETED
```

Current physical host state:

```text
UNPROVEN
```

Do not infer runtime state from GitHub.

## Android

The phone must not become a second active scanner.

```text
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
```

## ProfitLab

```text
PUBLIC_PRODUCT=NO
PRIVATE_ANALYTICS=YES
SOURCE_OF_TRUTH=BOTA_EVIDENCE
```

## Exactly one next action

Perform one bounded **read-only Hetzner forensic inspection** covering host/time, repository/commit, services/processes, execution authorities, R5 state, non-secret config fingerprints, provider wiring, Telegram/Supabase/ProfitLab wiring, evidence files and last-run history.

No restart, deployment, config edit, database mutation, Telegram test send, Android reactivation, strategy change or live-money action is authorized until the inspection is reconciled.
