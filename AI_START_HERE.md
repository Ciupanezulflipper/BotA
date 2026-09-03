# BotA AI Start Here

Last updated: **2026-09-04 UTC**

Read this before proposing any BotA strategy, deployment, Telegram, ProfitLab, Android/Termux, VPS/Hetzner, replay, historical-data, or runtime action.

## Current authoritative truth

```text
PROJECT=BotA
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
MEASUREMENT_HARDENING_DURING_PILOT=YES
NEXT_ACTION=READ_ONLY_HETZNER_FORENSIC_INSPECTION
FURTHER_BROAD_AI_REVIEW=STOP
```

Canonical current decision:

`audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`

Historical closure record remains valid historical evidence:

`audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Historical corpus result — preserve exactly

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

Interpretation:

```text
EXISTING_HISTORICAL_CORPUS_SUFFICIENT_FOR_PRIOR_GATE=NO
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
```

The 2026-09-03 closure stopped the then-active retrospective validation path. The owner has now explicitly authorized a **new prospective shadow-research path**. This does not erase or rewrite the old result.

## Statistical correction that must survive handoff

A genuinely new, frozen, single-hypothesis prospective test does **not** automatically inherit the historical multiple-testing Bonferroni penalty. Claude explicitly withdrew that prior application.

Do not treat any of these as the final required sample size:

```text
N=400
N=500
N=682
N=1446
```

The confirmatory sample size and sequential stopping boundaries must be derived after the measurement pilot establishes the empirical Net-R distribution, execution-cost distribution, ambiguity rate and dependence structure.

Primary future scientific endpoint is expected to be **Net R after realistic execution costs**, not raw win rate. Exact hypothesis is not frozen yet.

`60%` win rate is a future business/product aspiration only, not the primary scientific edge gate.

## Execution/evidence corrections

Do not assume:

- decision/model price equals subscriber-executable price;
- spread is always 1 pip;
- every win is exactly +2R and loss exactly -1R;
- EURUSD and GBPUSD signals are independent;
- M15 OHLC can order TP and SL when both touch in the same candle;
- Telegram API success proves a human saw the message.

Repository evidence confirms that same-candle TP-first logic exists and has been documented as potentially optimistic.

## Existing measurement infrastructure — do not rewrite blindly

The repository already contains substantial controls:

- `tools/watcher_cycle_ledger.py` — bounded current-cycle reconciliation and terminal decision evidence;
- `tools/pipeline_ledger.py` — append-only event ledger with UUID event IDs, process-shared `flock`, UTC display time, monotonic/boot-aware time and atomic compact state updates;
- watcher stale-candle handling that fails closed on missing/unparseable/stale candle evidence.

Therefore do not assume a rewrite is needed. Inspect actual Hetzner runtime first, then harden only the missing measurement controls.

## Stage 0 contract

The measurement pilot may improve observation only:

- run/signal/host identity;
- config fingerprinting;
- UTC timestamp semantics;
- expected-scan completeness;
- provider identity;
- bid/ask/spread evidence;
- publication timing;
- ambiguity handling;
- lower-timeframe resolver evidence where justified;
- idempotency/crash reconciliation;
- automated integrity reports.

It must not change:

- Policy B;
- ADX/RSI/score rules;
- pair/timeframe scope;
- higher-timeframe confirmation logic;
- TP/SL strategy logic;
- baseline trading rules.

Pilot observations **do not count** toward the later confirmatory sample.

## Hetzner / VPS boundary

Historical VPS work reached R5 **no-side-effect shadow**, not Production cutover.

```text
VPS_R5_ENGINEERING_ARTIFACT=PRESERVE
CURRENT_HETZNER_RUNTIME_STATE=UNPROVEN
HETZNER_LIVE_MONEY_CUTOVER=NO
```

Do not infer current host state from GitHub.

## ProfitLab

```text
PROFITLAB_PUBLIC_PRODUCT=NO
PROFITLAB_PRIVATE_ANALYTICS=YES
PROFITLAB_SOURCE_OF_TRUTH=NO
BOTA_EVIDENCE_SOURCE_OF_TRUTH=YES
```

## Exactly one current action

Perform a **read-only Hetzner forensic inspection** before any restart or deployment.

No service start/stop/restart, deploy, checkout, config edit, Supabase mutation, Telegram test send, strategy change or live-money action is authorized until that inspection is reconciled with repository evidence.
