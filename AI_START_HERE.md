# BotA AI Start Here

Last updated: **2026-09-03 UTC**

Read this before proposing any BotA strategy, deployment, Telegram, ProfitLab, Android/Termux, VPS/Hetzner, replay, historical-data, or runtime action.

## Current authoritative truth

```text
PROJECT=BotA
FINAL_STRATEGY_VERDICT=CLOSE
ACTIVE_TRADING_STRATEGY_VALIDATION=STOP
PRODUCTION_READY=NO
PRODUCTION_CUTOVER_AUTHORIZED=NO
HETZNER_PRODUCTION_CUTOVER=BLOCKED
STRATEGY_TUNING_AUTHORIZED=NO
ADDITIONAL_HISTORY_ACQUISITION_AUTHORIZED=NO
PROFITLAB_BOTA_DEPENDENCY=PARKED
```

Canonical closure record:

`audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Why BotA is closed

A corpus governance rule was fixed before the final frozen Policy-B count was known:

```text
POLICY_B_ACCEPTED < 400 -> KILL
400-599                -> continue only if economics are exceptional
600-799                -> borderline
>=800                  -> corpus gate PASS
```

The exact deterministic full frozen replay produced:

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
REPLAY_SOURCE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
EVALUATION_START_UTC=2025-12-03T22:00:00Z
EVALUATION_END_UTC_EXCLUSIVE=2026-08-01T00:00:00Z
DECISION_ROWS=32641
POLICY_A_ACCEPTED=478
POLICY_B_ACCEPTED=195
POLICY_C_ACCEPTED=164
CORPUS_GATE=FAIL
```

Read-only proof from the count run:

```text
REPOSITORY_STATE_UNCHANGED=YES
DATASET_MANIFEST_UNCHANGED=YES
PRODUCTION_CACHE_UNCHANGED=YES
PRODUCTION_STRATEGY_MUTATED=NO
```

The pre-registered rule is therefore honored:

```text
195 < 400 -> CLOSE
```

## Important corrections

Do not repeat these superseded claims:

1. **Do not claim 500 D1 bars are practically necessary because EMA/Wilder memory is recursive.** Old-state influence is numerically negligible after sufficiently long warm-up. The 500-bar rule is retained because it defines the frozen replay protocol, not because 500 is a mathematical law.
2. **Do not claim a 200-bar replay would produce ~500-550 Policy-B candidates.** That replay has not been executed; the count is unknown.
3. **Do not present 40% as the observed win rate of the 195 candidates.** Complete outcomes for the 195 frozen candidates are unresolved.
4. **Do not present 13 trades/month as the observed corpus rate.** It was an illustrative economics scenario.
5. **Do not treat multi-model agreement as independent proof.** Kimi, Perplexity, Grok, DeepSeek and Gemini reviewed the same framing package; their useful contribution is the specific adversarial criticism, not vote counting.

## What closure does and does not mean

```text
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
CORPUS_SUFFICIENCY_GATE_FAILED=YES
```

BotA is being closed because the active validation project failed its pre-registered corpus gate and the remaining path would reopen the same data/replay/tuning cycle the gate was created to stop.

## Hetzner / VPS status

Historical VPS work reached an R5 **no-side-effect shadow**, not Production cutover. Market opening is no longer a release gate.

```text
VPS_R5_ENGINEERING_ARTIFACT=PRESERVE
VPS_PRODUCTION_CUTOVER=DO_NOT_PROCEED
PR120_MERGE_AUTHORITY=REVOKED_BY_CLOSURE
OPEN_MARKET_LIVE_ACCEPTANCE=NO_LONGER_REQUIRED
```

Do not infer from this file that any running Hetzner service has been stopped. Host cleanup requires separate fresh host evidence.

## ProfitLab status

```text
PROFITLAB_SHELL=PRESERVE_AS_INFRASTRUCTURE
PROFITLAB_BOTA_SIGNAL_DEPENDENCY=PARKED
PROFITLAB_VALIDATED_BUSINESS=NO
```

ProfitLab must not be used as justification to restart BotA.

## Optional final outcome record

A one-time read-only resolution of the 195 frozen Policy-B candidates may be performed only as a historical closing record, with this constraint fixed before execution:

```text
OUTCOME_RESULT_CAN_REOPEN_BOTA=NO
STRATEGY_CHANGE=NO
PROTOCOL_CHANGE=NO
PRODUCTION_DEPLOYMENT=NO
```

## Prohibited next actions

Do not:

- tune Policy B;
- lower thresholds;
- add GEMs, filters, indicators, pairs, or strategy rules;
- change the warm-up and call the result the original frozen experiment;
- acquire more historical data to rescue validation;
- build another open-ended PnL/replay project;
- pursue natural market-open proof as a readiness gate;
- merge or deploy the VPS migration as Production;
- use ProfitLab as a reason to resume signal development.

## Read first

1. `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`
2. `CONTINUITY_CURRENT.md`
3. `DECISIONS.md`
4. `state/STATE.json`
5. historical audit/runtime files only when their dated evidence is needed

## Exactly one current project action

**Preserve and archive the engineering evidence. Do not continue BotA strategy validation or Production cutover.**
