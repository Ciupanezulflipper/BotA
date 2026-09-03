# BotA Shadow Research Reopen — Measurement Pilot Decision

Date: **2026-09-04 UTC**

## Purpose

This record supersedes the **current-action** portion of the 2026-09-03 strategy closure while preserving the historical closure evidence unchanged.

The owner has explicitly clarified the intended project objective:

> Debug BotA until it runs reliably, keep collecting prospective shadow signals, and evaluate whether a real edge exists. Do not claim the strategy is validated and do not use live money until evidence supports it.

This is a human governance override. It does **not** retroactively invalidate the 2026-09-03 corpus result.

## Historical closure that remains true

The frozen deterministic replay still produced:

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
REPLAY_SOURCE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
EVALUATION_START_UTC=2025-12-03T22:00:00Z
EVALUATION_END_UTC_EXCLUSIVE=2026-08-01T00:00:00Z
DECISION_ROWS=32641
POLICY_A_ACCEPTED=478
POLICY_B_ACCEPTED=195
POLICY_C_ACCEPTED=164
PRE_REGISTERED_KILL_THRESHOLD=400
CORPUS_GATE=FAIL
```

The valid interpretation remains:

```text
HISTORICAL_RETROSPECTIVE_VALIDATION_PROJECT=CLOSED
EXISTING_FROZEN_CORPUS_SUFFICIENT_FOR_PRIOR_GATE=NO
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
```

The prior closure was a sample-sufficiency/governance decision. It was not proof that BotA cannot have an edge.

## New owner-authorized scope

```text
BOTA_SHADOW_RESEARCH=REOPENED
LIVE_MONEY_TRADING=NO
COMMERCIAL_PROFITLAB=NO
PRIVATE_PROFITLAB_ANALYTICS=YES
TELEGRAM_EXPERIMENTAL_SIGNALS=YES
PRIMARY_RUNTIME_TARGET=HETZNER
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
```

The first new phase is **not** the confirmatory statistical trial.

```text
NEXT_PHASE=STAGE_0_MEASUREMENT_PILOT
PILOT_COUNTS_TOWARD_CONFIRMATORY_SAMPLE=NO
STRATEGY_TUNING_DURING_PILOT=NO
MEASUREMENT_HARDENING_DURING_PILOT=YES
```

## Five-review adversarial synthesis

The final review cycle used Claude, Gemini, Grok, DeepSeek and Perplexity for different failure surfaces. Their agreement is not treated as independent statistical evidence; the durable value is the specific errors and controls they surfaced.

### Claude — statistical/governance correction

Claude initially carried a historical multiple-testing penalty into a genuinely new prospective test. Claude explicitly withdrew that claim.

Current durable correction:

```text
NEW_SINGLE_PRE_REGISTERED_PROSPECTIVE_HYPOTHESIS_ALPHA_0_05=STATISTICALLY_VALID_IN_PRINCIPLE
HISTORICAL_BONFERRONI_AUTOMATICALLY_CARRIED_FORWARD=NO
PRIOR_N_1446_REQUIREMENT=WITHDRAWN
```

Claude's later ~682 observation estimate still depends on a simplified fixed-payoff/binomial model and is therefore **not** a final BotA sample-size requirement.

### Gemini — endpoint and sequential design

Useful findings:

- Net economic return in R is a better primary scientific endpoint than raw win rate.
- EURUSD and GBPUSD observations can be dependent.
- A sequential design can reduce time-to-truth.

Rejected as final design:

- fixed N=100 futility and N=200 success rules were not rigorously derived;
- binomial sample sizes were inconsistent with the stated Net-R primary endpoint.

### Grok — execution realism

Useful findings:

- decision/model price is not automatically an executable subscriber price;
- bid/ask, spread, latency and slippage matter;
- theoretical strategy performance and subscriber-executable performance answer different questions;
- M15 OHLC cannot order TP and SL if both are touched within the same candle;
- correlated EURUSD/GBPUSD exposure can represent one USD macro event.

Repository cross-check confirms that same-candle TP-first logic exists historically/currently in BotA shadow tooling and is explicitly documented as potentially optimistic.

### DeepSeek — evidence pipeline

DeepSeek correctly identified the classes of evidence required for a trustworthy prospective experiment: run identity, signal identity, configuration fingerprinting, scan completeness, provider identity, resolver versioning and reconciliation.

However, several claims that BotA had none of these controls were overstated because DeepSeek did not have complete repository/runtime evidence.

Repository cross-check proves BotA already contains substantial relevant infrastructure:

- `tools/watcher_cycle_ledger.py` reconciles a bounded watcher cycle and records terminal pair/timeframe decisions;
- `tools/pipeline_ledger.py` is an append-only event ledger with UUID event IDs, process-shared `flock`, UTC display timestamps, monotonic/boot-aware timing and atomic state replacement;
- current watcher logic already includes fail-closed stale-candle handling.

Therefore:

```text
FULL_REWRITE_REQUIRED=NO_EVIDENCE
PREFERRED_PATH=INCREMENTAL_MEASUREMENT_HARDENING
```

### Perplexity — external fact check

Perplexity's externally grounded conclusion was:

```text
PERPLEXITY_VERDICT=PROCEED_TO_MEASUREMENT_PILOT
DIRECT_CONFIRMATORY_COLLECTION_NOW=NO
MEASUREMENT_HARDENING_FIRST=YES
```

Durable externally supported points include:

- OANDA exposes pricing/candle data with bid/ask/mid components and candle-completion semantics;
- a pricing stream is not a complete historical tick tape;
- Telegram API success proves server/API acceptance, not that a human viewed the message;
- fixed 1-pip cost is not a universal execution model;
- same-bar TP/SL ordering cannot be recovered from OHLC alone;
- repeated interim statistical looks require a pre-specified sequential design;
- a measurement-only pilot may be separated from a later fresh confirmatory sample.

## What is now withdrawn as a fixed requirement

```text
FIXED_N_400=NO
FIXED_N_500=NO
FIXED_N_682=NO
FIXED_N_1446=NO
60_PERCENT_WIN_RATE_AS_PRIMARY_SCIENTIFIC_GATE=NO
```

The original 60% target may remain a future product/business aspiration. It is not the definition of statistical edge.

The eventual confirmatory sample size and stopping boundaries must be derived after the pilot establishes the empirical Net-R distribution, execution-cost distribution, ambiguity rate and dependence structure.

## Primary future scientific question

The intended confirmatory question is approximately:

> Does the frozen BotA baseline have positive Net R after realistic execution costs, under a pre-registered dependence-aware prospective design?

The exact hypothesis, analysis population, cost model and sequential boundaries are **not yet frozen**.

## Two required performance streams

The pilot should determine how to support two separate evidence streams:

```text
STRATEGY_THEORETICAL
- asks whether the frozen decision rule has edge under its own market-data model

SUBSCRIBER_EXECUTABLE
- asks whether a signal remains realistically actionable after measured publication latency and executable bid/ask pricing
```

These streams must never be collapsed into one undocumented success rate.

## Stage 0 — measurement pilot contract

### Strategy logic frozen

The pilot must not change:

- Policy-B qualifying logic;
- ADX/RSI/score thresholds;
- EURUSD/GBPUSD scope;
- M15 entry logic;
- H1/H4/D1 confirmation logic;
- TP/SL strategy rules;
- cooldown/dedup behavior unless a later change is explicitly classified as strategy-affecting and therefore kept outside the confirmatory baseline.

### Measurement changes authorized

The pilot may add or harden:

- run and signal identity;
- host/deployment/process identity;
- strategy/configuration fingerprinting;
- explicit UTC timestamp semantics;
- expected-scan/run completeness;
- provider identity and fail-closed provider behavior;
- decision-time bid/ask/spread capture where available;
- publication/API acknowledgement timing;
- explicit ambiguity states;
- lower-timeframe evidence for ambiguous outcome adjudication where technically justified;
- resolver versioning;
- immutable/append-only evidence and correction-safe lifecycle records;
- idempotency and crash reconciliation;
- automated weekly integrity reporting.

### Pilot completion is evidence-based, not N-based

The pilot ends only after it proves, under representative normal/restart/failure conditions:

```text
EXPECTED_SCANS_ACCOUNTED_FOR=YES
AUTHORITATIVE_ENGINE_SINGLETON_PROVEN=YES
RUN_IDENTITY_COMPLETE=YES
SIGNAL_IDENTITY_COMPLETE=YES
CONFIG_FINGERPRINT_STABLE=YES
CLOSED_BAR_DISCIPLINE_PROVEN=YES
PROVIDER_IDENTITY_PROVEN=YES
BID_ASK_OR_APPROVED_EXECUTION_PROXY_CAPTURE_PROVEN=YES
PUBLICATION_TIMESTAMPS_RECONCILED=YES
OUTCOME_RESOLVER_SINGLE_AND_VERSIONED=YES
SAME_BAR_AMBIGUITY_NOT_SILENTLY_TP_FIRST=YES
RESTARTS_DO_NOT_DUPLICATE_SIDE_EFFECTS=YES
MISSING_SCANS_DISTINGUISHED_FROM_NO_SIGNAL=YES
LIFECYCLE_RECONCILIATION_HAS_NO_UNEXPLAINED_GAPS=YES
```

Pilot observations are excluded from the later confirmatory sample.

## Weekly review contract

Weekly review is allowed for:

```text
OPERATIONS=YES
DATA_INTEGRITY=YES
DELIVERY_HEALTH=YES
DESCRIPTIVE_PERFORMANCE=YES
CANDIDATE_OBSERVATIONS=YES
BASELINE_STRATEGY_MUTATION=NO
```

AI reviewers may identify candidate hypotheses, but they must not adapt the confirmatory baseline. Any future candidate lane requires explicit separation and prospective identity.

## ProfitLab role

During research:

```text
PROFITLAB_PUBLIC_PRODUCT=NO
PROFITLAB_PRIVATE_ANALYTICS=YES
PROFITLAB_SOURCE_OF_TRUTH=NO
BOTA_EVIDENCE_IS_AUTHORITATIVE=YES
```

ProfitLab may consume BotA evidence and show operational/statistical summaries. It must not independently rewrite signal truth or outcomes.

## Hetzner evidence boundary

Historical repository evidence proves only:

```text
VPS_R5_HISTORICAL_STATE=NO_SIDE_EFFECT_SHADOW
VPS_PRODUCTION_CUTOVER_HISTORICALLY_COMPLETED=NO
```

It does **not** prove the current host state.

```text
CURRENT_HETZNER_RUNTIME_STATE=UNPROVEN
```

Before any restart or deployment, inspect the actual host read-only.

## Next real-world action

Exactly one next action is authorized:

**Perform a read-only forensic inspection of the current Hetzner host.**

Minimum evidence to collect:

1. host identity, UTC clock and time synchronization;
2. BotA directory, repository/worktree and exact commit;
3. all BotA processes and service-manager definitions;
4. cron/systemd/runit/manual execution paths that could create duplicate authority;
5. exact historical R5 entry point and current state;
6. configuration fingerprints without exposing secrets;
7. active market-data provider path;
8. Telegram, Supabase and ProfitLab wiring;
9. existing ledger/evidence files and last-run timestamps;
10. proof of whether anything BotA-related has run since it was left on Hetzner.

This inspection is read-only. No service start, stop, restart, deployment, checkout, config edit, database mutation, Telegram send or strategy change is authorized by this record.

## Final current state

```text
BOTA_EDGE_STATUS=UNVALIDATED
BOTA_SHADOW_RESEARCH=REOPENED_BY_OWNER
HISTORICAL_CORPUS_GATE_RESULT=PRESERVED
LIVE_TRADING=NO
COMMERCIAL_PROFITLAB=NO
PRIMARY_RUNTIME_TARGET=HETZNER
CURRENT_HETZNER_RUNTIME_STATE=UNPROVEN
ANDROID_ACTIVE_SCANNER=NO
NEXT_PHASE=STAGE_0_MEASUREMENT_PILOT
PILOT_NOT_STARTED=YES
NEXT_ACTION=READ_ONLY_HETZNER_FORENSIC_INSPECTION
FURTHER_BROAD_AI_REVIEW=STOP
```
