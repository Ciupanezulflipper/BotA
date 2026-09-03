# BotA Current Continuity State

Last updated: **2026-09-03 UTC**

This is the current operational handoff. Older readiness, Android, VPS migration and market-open acceptance records remain historical evidence only.

## Current authoritative status

```text
GITHUB_MAIN_BEFORE_CLOSURE_DOCS=0212d9848ecb8e8b464da215c2ac115d62dae2f4
FINAL_STRATEGY_VERDICT=CLOSE
ACTIVE_TRADING_STRATEGY_VALIDATION=STOP
PRODUCTION_READY=NO
PRODUCTION_CUTOVER_AUTHORIZED=NO
HETZNER_PRODUCTION_CUTOVER=BLOCKED
MARKET_OPEN_ACCEPTANCE_REQUIRED=NO
STRATEGY_CHANGE_AUTHORIZED=NO
MORE_HISTORY_FOR_RESCUE_AUTHORIZED=NO
PROFITLAB_BOTA_DEPENDENCY=PARKED
```

Canonical closure evidence: `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`.

## Final corpus gate

The pre-registered Policy-B governance thresholds were fixed before the final count:

```text
<400    -> KILL
400-599 -> continue only if economics are exceptional
600-799 -> borderline
>=800   -> PASS
```

The exact read-only frozen replay result was:

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

Therefore:

```text
195 < 400
CORPUS_GATE=FAIL
BOTA_STRATEGY_PROJECT=CLOSED
```

## What is proven vs not proven

```text
EXACT_POLICY_B_CORPUS_UNDER_FROZEN_500_BAR_PROTOCOL=195
STRATEGY_EDGE_VALIDATED=NO
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
FULL_195_OUTCOMES_RESOLVED=NO
```

The closure is a governance/sample-sufficiency decision, not a claim that all 195 candidates lose money.

## Warm-up issue — final classification

The 500-bar D1 requirement is a frozen replay/verifier protocol choice. The prior argument that 500 bars are practically required by recursive EMA/Wilder memory is withdrawn as materially overstated.

A 200-bar replay would be a legitimate sensitivity experiment but has not been executed. Any prior estimate around 500-550 Policy-B accepts under a 200-bar convention is withdrawn as speculation.

```text
500_BAR_PROTOCOL_INVALIDATES_195=NO
200_BAR_CORPUS_COUNT=UNKNOWN
200_BAR_REPLAY_AUTHORIZED_AS_RESCUE=NO
```

## Economic evidence — bounded statement only

Previous economics used an illustrative 40% true win rate, +2R/-1R payoff, 16.56-pip risk and 1-pip baseline cost, producing an illustrative ~+0.14R/trade and ~2.3-pip additional edge-erasure threshold.

Important corrections:

- 40% is not the observed win rate of the 195 candidates;
- 13 trades/month was an illustrative scenario, not the observed corpus frequency;
- complete outcomes for the 195 frozen candidates remain unresolved;
- the economic case must therefore not be presented as measured BotA performance.

The economics are useful only as execution-fragility context. They are not the primary closure proof.

## External adversarial audit

Kimi, Perplexity, Grok, DeepSeek and Gemini all returned `CLOSE`. Claude's final executive review also supported closure.

Do not treat this as six independent votes. The five external models saw the same framing package. Durable value comes from the criticisms they surfaced: hypothetical economics, unresolved outcomes, non-independence/clustering risk, warm-up protocol distinction, and invalidity of the unexecuted 200-bar count extrapolation.

## Android / Termux historical state

The previous phone/runtime reliability work remains historically valid for the generations and timestamps it proved. It no longer creates a release obligation.

No new natural market-open phone proof is required for project closure.

## Hetzner / VPS disposition

Issue #9 records that the exact VPS release reached R5 no-side-effect shadow operation, with the phone still Production and Production side effects suppressed. The project closed before VPS Production cutover.

```text
R5_ENGINEERING_WORK=PRESERVE
R5_PRODUCTION_CUTOVER=STOP
PR120_MERGE=DO_NOT_PROCEED
MARKET_OPEN_R5_ACCEPTANCE=NO_LONGER_REQUIRED
```

This repository record does not claim the existing shadow service has been stopped on the host. Any service shutdown/removal is separate operational cleanup requiring fresh Hetzner evidence.

## ProfitLab disposition

ProfitLab's application/auth/subscription infrastructure may be retained, but BotA is no longer an authorized signal source or reason to continue strategy work.

```text
PROFITLAB_SHELL=PRESERVE
PROFITLAB_BOTA_PIPELINE=PARK
PROFITLAB_VALIDATED_BUSINESS=NO
```

## Optional final historical result

The existing frozen decision rows may later be resolved to outcomes once as a read-only closing record only. Before any such run, the following stays locked:

```text
OUTCOME_RESULT_CAN_REOPEN_BOTA=NO
STRATEGY_CHANGE=NO
PROTOCOL_CHANGE=NO
PRODUCTION_DEPLOYMENT=NO
```

## Current blockers

There are no remaining blockers to BotA strategy closure.

The former blockers—live-market three-pair acceptance, R5 observation acceptance, VPS cutover and ProfitLab live-signal continuation—are **superseded by project closure**.

## Exactly one next action

**Archive/preserve the engineering and research evidence. Do not deploy BotA to Hetzner Production and do not resume strategy validation.**
