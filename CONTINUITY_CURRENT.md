# BotA Current Continuity State

Last updated: **2026-09-04 UTC**

This is the current operational handoff. The 2026-09-03 final strategy closure remains preserved as historical evidence, but its current-action prohibition has been superseded by an explicit owner-authorized shadow-research reopening.

## Current authoritative status

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
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
NEXT_PHASE=STAGE_0_MEASUREMENT_PILOT
PILOT_STARTED=NO
STRATEGY_TUNING_DURING_PILOT=NO
MEASUREMENT_HARDENING_DURING_PILOT=YES
NEXT_ACTION=READ_ONLY_HETZNER_FORENSIC_INSPECTION
```

Canonical current record:

`audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`

Historical closure record:

`audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Historical corpus gate — unchanged

The pre-registered historical corpus thresholds were:

```text
<400    -> KILL
400-599 -> continue only if economics are exceptional
600-799 -> borderline
>=800   -> PASS
```

The deterministic frozen replay produced:

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
REPLAY_SOURCE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
EVALUATION_START_UTC=2025-12-03T22:00:00Z
EVALUATION_END_UTC_EXCLUSIVE=2026-08-01T00:00:00Z
DECISION_ROWS=32641
POLICY_A_ACCEPTED=478
POLICY_B_ACCEPTED=195
POLICY_C_ACCEPTED=164
REPOSITORY_STATE_UNCHANGED=YES
DATASET_MANIFEST_UNCHANGED=YES
PRODUCTION_CACHE_UNCHANGED=YES
```

Therefore the old retrospective validation project correctly closed under its own rule:

```text
195 < 400
HISTORICAL_CORPUS_GATE=FAIL
```

That result does not prove negative profitability and does not mathematically prohibit a new independent prospective experiment.

## Why the project is now reopened

The owner clarified that the intended project objective was always to debug BotA until it ran reliably and then keep collecting prospective signals long enough to evaluate the system. The 2026-09-03 closure moved beyond that intent by treating the failed historical corpus gate as a reason to stop all future collection.

The owner has now explicitly overridden that current-action decision while retaining the historical evidence.

```text
HUMAN_OVERRIDE=AUTHORIZED
REOPEN_SCOPE=SHADOW_DATA_COLLECTION_AND_MEASUREMENT_ONLY
STRATEGY_VALIDATION_CLAIM=NO
LIVE_TRADING=NO
```

## Final multi-AI audit synthesis

The final adversarial review cycle used Claude, Gemini, Grok, DeepSeek and Perplexity for distinct roles.

Durable conclusions:

1. **Prospective test validity:** a new frozen single-hypothesis prospective test is methodologically legitimate; the old historical Bonferroni penalty is not automatically carried forward.
2. **No magical N:** 400, 500, 682 and 1446 are not accepted as final BotA sample requirements.
3. **Economic endpoint:** Net R after realistic costs is preferred over raw win rate as the primary scientific endpoint.
4. **Execution realism:** model price, fixed 1-pip costs, binary +2R/-1R outcomes and M15 TP-first ties are too crude for final confirmation.
5. **Dependence:** EURUSD/GBPUSD and temporally overlapping trades may be correlated and require dependence-aware analysis.
6. **Sequential design:** early stopping is preferred in principle, but exact futility/success boundaries must be pre-specified and derived after empirical pilot data exists.
7. **Measurement pilot first:** do not begin confirmatory collection until fill/latency/resolver/completeness evidence is proven.
8. **No further broad AI review loop:** the external review stage is complete.

## Repository cross-check against audit claims

Several DeepSeek warnings were directionally useful but overstated because repository evidence already contains meaningful measurement controls.

Proven current repository infrastructure includes:

- `tools/watcher_cycle_ledger.py`: bounded watcher-cycle reconciliation, expected pair/timeframe decisions, structured Telegram/Supabase evidence and fail-closed unhealthy-cycle classification;
- `tools/pipeline_ledger.py`: append-only event ledger with UUID event IDs, process-shared `flock`, UTC display time, monotonic/boot-aware timing and atomic state replacement;
- watcher staleness logic based on candle timestamps with fail-closed skip behavior.

Therefore:

```text
REWRITE_REQUIRED=NO_EVIDENCE
MEASUREMENT_HARDENING_APPROACH=INCREMENTAL
```

Repository evidence also confirms that same-candle TP-first behavior exists and is documented as potentially optimistic when both TP and SL are touched in one M15 candle.

## Stage 0 — measurement pilot

The pilot is an instrumentation/measurement phase, not a strategy optimization phase.

### Allowed

- stronger run/signal identity;
- host/deployment/process identity;
- config/strategy fingerprints;
- explicit UTC event semantics;
- expected-scan accounting;
- provider identity and fail-closed provider handling;
- bid/ask/spread evidence where available;
- Telegram/API publication timestamps;
- explicit ambiguity states;
- lower-timeframe evidence where justified;
- resolver versioning;
- append-only/correction-safe lifecycle evidence;
- idempotency/crash reconciliation;
- automated weekly integrity reports.

### Not allowed

- Policy-B changes;
- ADX/RSI/score changes;
- pair/timeframe changes;
- H1/H4/D1 confirmation changes;
- TP/SL strategy changes;
- weekly baseline tuning.

Pilot observations do not count toward the confirmatory sample.

## Pilot completion gate

Pilot completion is based on evidence quality, not an arbitrary number of signals.

Required end state includes:

```text
EXPECTED_SCANS_ACCOUNTED_FOR=YES
AUTHORITATIVE_ENGINE_SINGLETON_PROVEN=YES
RUN_IDENTITY_COMPLETE=YES
SIGNAL_IDENTITY_COMPLETE=YES
CONFIG_FINGERPRINT_STABLE=YES
CLOSED_BAR_DISCIPLINE_PROVEN=YES
PROVIDER_IDENTITY_PROVEN=YES
EXECUTION_PRICE_EVIDENCE_PROVEN=YES
PUBLICATION_TIMESTAMPS_RECONCILED=YES
OUTCOME_RESOLVER_SINGLE_AND_VERSIONED=YES
SAME_BAR_AMBIGUITY_NOT_SILENTLY_TP_FIRST=YES
RESTART_DUPLICATION_TEST=PASS
MISSING_SCAN_VS_NO_SIGNAL_DISTINGUISHABLE=YES
LIFECYCLE_RECONCILIATION_NO_UNEXPLAINED_GAPS=YES
```

## Confirmatory test — not yet started

After Stage 0 passes:

1. freeze the measurement model;
2. define the confirmatory population;
3. pre-register one primary hypothesis based on Net R after realistic costs;
4. define dependence treatment;
5. derive valid sequential success/futility rules;
6. start a fresh sample from observation #1.

```text
FIXED_N_400=NO
FIXED_N_500=NO
FIXED_N_682=NO
FIXED_N_1446=NO
60_PERCENT_WR_AS_PRIMARY_EDGE_GATE=NO
```

## ProfitLab

ProfitLab remains private and subordinate to BotA evidence.

```text
PROFITLAB_PUBLIC_PRODUCT=NO
PROFITLAB_PRIVATE_ANALYTICS=YES
PROFITLAB_SOURCE_OF_TRUTH=NO
BOTA_EVIDENCE_SOURCE_OF_TRUTH=YES
```

## Android / Termux

The phone execution plane remains stopped. Android is not to be reactivated as a parallel scanner.

```text
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=MONITOR_CONTROL_ONLY
```

This avoids split-brain signal generation and reduces dependence on ship connectivity/Android background-process behavior.

## Hetzner / VPS

Historical evidence proves R5 no-side-effect shadow engineering work existed. It does not prove the current physical host state.

```text
VPS_R5_HISTORICAL_STATE=NO_SIDE_EFFECT_SHADOW
CURRENT_HETZNER_RUNTIME_STATE=UNPROVEN
```

## Exactly one next action

Perform a **read-only forensic inspection of Hetzner** before any restart or deployment.

Collect host identity/time sync, repository/commit, services/processes, all execution authorities, R5 state, configuration fingerprints without secrets, provider wiring, Telegram/Supabase/ProfitLab wiring, ledgers/logs and last-run evidence.

No runtime mutation is authorized until that evidence is reconciled against this repository.
