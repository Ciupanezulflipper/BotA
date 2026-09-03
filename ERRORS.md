# BotA Errors and Silent-Failure Register

Last updated: **2026-09-03 UTC**

Purpose: preserve verified engineering and reasoning failure classes that future work must not repeat.

Current canonical sources:

- `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`
- `AI_START_HERE.md`
- `CONTINUITY_CURRENT.md`
- `DECISIONS.md`
- `state/STATE.json`

## Current verdict

```text
FINAL_STRATEGY_VERDICT=CLOSE
EXACT_POLICY_B_CORPUS=195
PRE_REGISTERED_KILL_THRESHOLD=400
CORPUS_GATE=FAIL
ACTIVE_TRADING_STRATEGY_VALIDATION=STOP
HETZNER_PRODUCTION_CUTOVER=NO
PROFITLAB_BOTA_DEPENDENCY=PARKED
```

The prior runtime/reliability error classes remain preserved in Git history and dated audits. This current register emphasizes the failure patterns that control all future BotA reasoning.

## E001 — Repository state mistaken for deployed/runtime state

**Status:** Durable prevention rule.

GitHub merge/HEAD does not prove what is running on Android or VPS. Runtime claims require fresh host evidence.

## E002 — Process liveness mistaken for useful progress

**Status:** Durable prevention rule.

A running service can be stalled, orphaned, duplicate-owned, or producing no authoritative decisions. Health requires useful progress and ownership evidence.

## E003 — Competing execution authorities

**Status:** Durable prevention rule.

Cron/runit/boot/watchdog/systemd ownership must not overlap for the same responsibility.

## E004 — Device wall clock used as trading truth

**Status:** Historically resolved; rule retained.

Trading/session semantics use trusted server time; monotonic time is for elapsed-duration health.

## E005 — Delivery evidence confused with decision evidence

**Status:** Durable prevention rule.

Telegram, ProfitLab/Supabase publication, decision persistence and lifecycle outcome are distinct evidence streams.

## E006 — Runtime failure used to erase strategy evidence

**Status:** Durable prevention rule.

Infrastructure instability can reduce evidence quality; it does not automatically invalidate negative outcomes or prove strategy edge.

## E007 — Strategy losses used to explain infrastructure failure

**Status:** Durable prevention rule.

Trading results and runtime reliability are separate claim domains.

## E008 — Small selected subsets promoted to validated edge

**Status:** Durable prevention rule.

Tiny in-sample or post-selected Policy/ADX/RSI subsets are hypotheses, not durable edge proof.

## E009 — Replay acceptance counts promoted to PnL evidence

**Status:** Durable prevention rule.

A deterministic replay count proves reconstructed candidate frequency under its contract. It does not by itself prove outcomes or profitability.

## E010 — Raw dataset range mistaken for valid evaluation range

**Status:** RESOLVED / CRITICAL ANALYTICAL CORRECTION.

The canonical dataset contains raw candles from 2024-01-01, but the frozen verifier requires 500 pre-evaluation candles for every stream including D1. Most early history was warm-up, not eligible evaluation history.

This mistake originally produced an invalid extrapolation of roughly 791 Policy-B candidates over the entire raw interval.

Correct rule:

> Raw acquisition coverage is not evaluation coverage. Derive the earliest verifier-valid evaluation instant from the strictest timeframe before estimating corpus size.

Exact corrected full frozen result:

```text
EVALUATION_START_UTC=2025-12-03T22:00:00Z
POLICY_B_ACCEPTED=195
```

## E011 — Technical truth used as practical justification without magnitude check

**Status:** RESOLVED / REASONING CORRECTION.

The statement "EMA/Wilder values depend recursively on all earlier supplied bars" is mathematically true but was used incorrectly to imply that all 500 D1 bars were practically necessary.

Old-state influence after long warm-up is numerically negligible for normal Forex decision precision.

Correct classification:

```text
500_BAR_REQUIREMENT=FROZEN_PROTOCOL_CHOICE
NOT=PRACTICAL_500_BAR_INDICATOR_NECESSITY
```

Rule:

> When invoking a mathematically nonzero effect, quantify its magnitude before calling it decision-relevant.

## E012 — Unexecuted sensitivity estimate stated too strongly

**Status:** RESOLVED / WITHDRAWN.

Earlier discussion suggested a 200-bar warm-up might yield roughly 500-550 Policy-B candidates. No such replay was executed.

Correct state:

```text
200_BAR_REPLAY=NOT_RUN
200_BAR_POLICY_B_COUNT=UNKNOWN
```

Rule:

> Never let linear/regime extrapolation become an observed result. Label it explicitly as an estimate or do not use it for governance.

## E013 — Illustrative economics presented too close to observed economics

**Status:** RESOLVED / EVIDENCE BOUNDARY LOCKED.

The following are illustrative assumptions, not measured outcomes of the exact 195 Policy-B corpus:

```text
WIN_RATE=40%
PAYOFF=+2R/-1R
AVERAGE_RISK=16.56 pips
BASELINE_COST=1 pip
NET_EXPECTANCY≈+0.14R/trade
ADDITIONAL_EDGE_ERASURE≈2.3 pips
```

The full 195 outcomes are unresolved. Therefore no final BotA win rate or realized expectancy can be inferred from these assumptions.

## E014 — Illustrative 13 trades/month treated as observed frequency

**Status:** RESOLVED / CORRECTION.

The 13/month figure was an economics scenario, not the observed corpus rate. The exact corpus contains 195 Policy-B accepts over roughly eight evaluation months, implying a simple average around 24/month before accounting for regime clustering or operational/live differences.

Rule:

> Keep scenario inputs and measured sample properties explicitly separated.

## E015 — Shared-prompt AI agreement treated as independent convergence

**Status:** RESOLVED / GOVERNANCE RULE.

Kimi, Perplexity, Grok, DeepSeek and Gemini all reviewed the same framing package and all returned CLOSE. Their agreement is correlated because the evidence and framing were shared.

Rule:

> Use multiple models to surface distinct attacks, calculations and contradictions. Do not count identical-prompt votes as independent evidence.

## E016 — Post-result escape hatch threatens pre-registered governance

**Status:** CLOSED BY FINAL DECISION.

The exact frozen Policy-B count is 195 against a pre-registered `<400 -> KILL` rule.

Changing warm-up, obtaining older data, tuning Policy B, adding GEMs, or building another replay/PnL layer as a rescue would reopen researcher discretion after the gate result.

Final prevention rule:

```text
195 < 400 -> CLOSE
REOPEN_WITH_TUNING=NO
REOPEN_WITH_MORE_HISTORY=NO
REOPEN_WITH_200_BAR_SENSITIVITY=NO
```

## E017 — Market-open urgency can override evidence discipline

**Status:** PREVENTION RULE.

A market opening soon is not a reason to deploy a strategy that has failed its validation governance.

Current consequence:

```text
OPEN_MARKET_PROOF=NO_LONGER_REQUIRED
HETZNER_PRODUCTION_CUTOVER=BLOCKED
```

## E018 — Working product infrastructure mistaken for validated business

**Status:** PREVENTION RULE.

ProfitLab may have functioning application/auth/subscription infrastructure, but that is not evidence of customer demand or a validated signal business.

```text
PROFITLAB_SHELL=PRESERVE
PROFITLAB_VALIDATED_BUSINESS=NO
BOTA_SIGNAL_DEPENDENCY=PARKED
```

## Current open risks

No remaining risk blocks the BotA **strategy closure**.

Operational cleanup may remain for any running phone/VPS shadow services, but cleanup is not a strategy-validation gate and must not be used to restart the project.

## Exactly one next action

**Preserve/archive evidence. Do not resume BotA strategy validation or Hetzner Production deployment.**
