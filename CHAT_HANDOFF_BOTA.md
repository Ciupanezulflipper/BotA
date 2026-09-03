# BotA Chat Handoff

Last updated: **2026-09-03 UTC**

Read this first in any new AI session before proposing BotA work.

## Current grounded answer

```text
FINAL_STRATEGY_VERDICT=CLOSE
BOTA_ACTIVE_TRADING_STRATEGY_PROJECT=NO
PRODUCTION_READY=NO
HETZNER_PRODUCTION_CUTOVER=NO
MARKET_OPEN_ACCEPTANCE_NEXT_STEP=NO
STRATEGY_TUNING=NO
ADDITIONAL_HISTORY_TO_RESCUE=NO
PROFITLAB_BOTA_DEPENDENCY=PARKED
```

Canonical final record:

`audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`

## Decisive evidence

A corpus governance rule was fixed before seeing the final frozen Policy-B count:

```text
<400 -> KILL
400-599 -> only if economics exceptional
600-799 -> borderline
>=800 -> PASS
```

Exact read-only replay result:

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

Read-only proof passed: repository state, dataset manifest and production cache were unchanged.

## Required interpretation

BotA closes because **195 failed the pre-registered <400 kill gate**.

Do not claim this proves the 195 candidates are unprofitable. Their complete outcomes have not been resolved in this final corpus run.

## Corrections that must survive handoff

- 500 D1 bars are part of the frozen replay protocol; they are not practically required by long-tail EMA/Wilder memory.
- A 200-bar replay has not been run. Its Policy-B count is unknown. Prior ~500-550 projections are withdrawn.
- 40% win rate is an illustrative economic assumption, not the observed Policy-B win rate.
- 13 trades/month was an illustrative scenario, not the observed corpus rate.
- Five external AI CLOSE verdicts are not independent evidence because they reviewed the same framing package.

## VPS / Hetzner

The exact release reached R5 no-side-effect shadow operation; Production side effects remained suppressed and the phone remained Production in the last recorded readiness state.

Project closure supersedes the migration acceptance path:

```text
PR120_MERGE_AUTHORITY=REVOKED_BY_CLOSURE
R5_PRODUCTION_CUTOVER=STOP
OPEN_MARKET_R5_OBSERVATION=NOT_REQUIRED
```

Do not infer that the running R5 shadow service has been stopped. Host cleanup is a separate operational action requiring fresh host evidence.

## ProfitLab

```text
SHELL_AND_INFRASTRUCTURE=MAY_BE_PRESERVED
BOTA_AS_SIGNAL_SOURCE=PARKED
VALIDATED_BUSINESS=NO
```

Do not describe ProfitLab as a business waiting only for BotA signals.

## Optional outcome resolution

One read-only frozen outcome resolution may be run later for historical completeness only if this condition remains pre-committed:

```text
OUTCOME_RESULT_CAN_REOPEN_BOTA=NO
```

It is a death-certificate record, not an appeal.

## Prohibited continuation paths

Do not:

- lower thresholds or change Policy B;
- add GEMs, indicators or filters;
- change warm-up and use the result to evade the original gate;
- acquire older history to restart validation;
- pursue market-open proof;
- promote Hetzner to Production;
- use ProfitLab as justification to resume BotA.

## Exactly one next action

**Preserve/archive the project evidence. BotA strategy validation and Production cutover are closed.**
