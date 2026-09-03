# BotA Decisions Register

Last updated: **2026-09-03 UTC**

This file records active decisions. Older operational decisions remain in Git history and dated audits. Explicit supersession here controls current work.

## 2026-09-03 — BotA closes as an active trading-strategy project

- Status: **LOCKED / FINAL**
- Canonical evidence: `audits/FINAL_STRATEGY_CLOSURE_2026-09-03.md`.

Pre-registered corpus governance:

```text
POLICY_B_ACCEPTED < 400       -> KILL
400-599                       -> continue only if economics exceptional
600-799                       -> borderline
POLICY_B_ACCEPTED >= 800      -> PASS
```

Exact frozen replay result:

```text
POLICY_B_ACCEPTED=195
KILL_THRESHOLD=400
CORPUS_GATE=FAIL
FINAL_STRATEGY_VERDICT=CLOSE
```

Decision:

```text
ACTIVE_TRADING_STRATEGY_VALIDATION=STOP
STRATEGY_TUNING_AUTHORIZED=NO
ADDITIONAL_HISTORY_FOR_RESCUE=NO
HETZNER_PRODUCTION_CUTOVER=NO
MARKET_OPEN_ACCEPTANCE_GATE=SUPERSEDED
```

### Rationale

The kill rule was fixed before the exact full frozen Policy-B count was known. The deterministic read-only corpus run returned 195, materially below the 400 kill threshold. The rule exists specifically to prevent post-result parameter changes, data expansion, replay expansion, and indefinite continuation.

This decision does **not** claim that every BotA trade loses. It claims that the active project failed its own pre-committed evidence-sufficiency gate.

---

## 2026-09-03 — 500-bar warm-up remains procedural, not mathematical

- Status: **LOCKED CORRECTION**

The previous claim that 500 D1 bars are practically necessary because EMA/Wilder smoothing retains recursive dependence is withdrawn as materially overstated.

Decision:

```text
500_BAR_RULE=FROZEN_PROTOCOL_CHOICE
500_BAR_RULE=NOT_A_PHYSICS_REQUIREMENT
200_BAR_REPLAY=UNEXECUTED_SENSITIVITY
200_BAR_POLICY_B_COUNT=UNKNOWN
```

Changing warm-up after observing the 195 result would create a different experiment. It may be scientifically interesting as sensitivity analysis, but it is not the original frozen test and is not authorized as a rescue path.

Earlier estimates around 500-550 Policy-B accepts under a 200-bar convention are withdrawn as unobserved extrapolation.

---

## 2026-09-03 — Economic claims must remain hypothetical until outcomes are resolved

- Status: **LOCKED EVIDENCE BOUNDARY**

The full 195 Policy-B candidate outcomes have not been resolved in the final corpus run.

Therefore:

```text
OBSERVED_POLICY_B_WIN_RATE_FOR_195=UNKNOWN
40_PERCENT_WIN_RATE=ILLUSTRATIVE_ONLY
13_TRADES_PER_MONTH=ILLUSTRATIVE_ONLY
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
STRATEGY_EDGE_VALIDATED=NO
```

The prior illustrative model—+2R/-1R, 40% win rate, 16.56-pip risk, 1-pip baseline cost, ~+0.14R/trade and ~2.3-pip additional edge-erasure threshold—may be retained only as execution-fragility context.

---

## 2026-09-03 — Optional outcome resolution cannot reopen BotA

- Status: **LOCKED BEFORE ANY FUTURE OUTCOME RUN**

A one-time read-only resolution of the 195 frozen Policy-B candidates is allowed only as a historical closing record.

```text
OUTCOME_RESOLUTION_PURPOSE=DEATH_CERTIFICATE_ONLY
OUTCOME_RESULT_CAN_REOPEN_BOTA=NO
STRATEGY_CHANGE=NO
PROTOCOL_CHANGE=NO
PRODUCTION_DEPLOYMENT=NO
```

A strong result is historically informative but cannot retroactively erase the failed pre-registered corpus gate.

---

## 2026-09-03 — Hetzner/VPS migration authority revoked by strategy closure

- Status: **LOCKED**

Historical R5 VPS work remains valuable engineering evidence. It was a no-side-effect shadow, not Production cutover.

Decision:

```text
R5_ENGINEERING_ARTIFACT=PRESERVE
PR120_MERGE_AUTHORITY=REVOKED
VPS_PRODUCTION_CUTOVER=DO_NOT_PROCEED
OPEN_MARKET_R5_ACCEPTANCE=NO_LONGER_REQUIRED
```

Any shutdown/removal of an already-running shadow service is a separate host-cleanup operation and requires fresh host evidence. Documentation must not claim that cleanup happened unless verified.

---

## 2026-09-03 — ProfitLab is decoupled from BotA closure

- Status: **LOCKED**

```text
PROFITLAB_SHELL=PRESERVE_AS_INFRASTRUCTURE
PROFITLAB_BOTA_SIGNAL_DEPENDENCY=PARKED
PROFITLAB_VALIDATED_BUSINESS=NO
```

ProfitLab must not be described as a validated business waiting only for BotA signals, and it must not be used as a reason to reopen BotA.

---

## 2026-09-03 — AI consensus is not independent evidence when framing is shared

- Status: **LOCKED LESSON**

Kimi, Perplexity, Grok, DeepSeek and Gemini all returned CLOSE, but they reviewed the same supplied evidence/framing package.

Decision rule:

> Use model outputs for adversarial error discovery, not vote counting. Shared-prompt agreement is correlated evidence.

The substantive corrections surfaced by the audits are retained; the numerical consensus itself is not treated as proof.

---

## Historical operational decisions — status after closure

The following prior classes remain valid as engineering lessons for their historical generations but no longer create BotA release obligations:

- claim-specific evidence authority;
- repository state != deployed runtime state;
- one execution owner per responsibility;
- trusted server epoch for trading/session semantics;
- useful progress != process liveness;
- immutable generation-specific deployment;
- evaluation evidence != delivery evidence;
- generation barriers and terminal watcher evidence;
- no threshold lowering to manufacture activity.

Historical runtime/reliability work may be reused in future systems. It is not authorization to resume BotA strategy validation.

## Current repository workflow decision

Normal changes remain branch/PR based. This closure is documentation/governance work only; it does not authorize code, runtime, strategy, phone, Supabase, Telegram, or Hetzner Production mutation.

## Exactly one current decision

**Preserve the project and its engineering lessons. Do not continue BotA trading-strategy validation or Production deployment.**
