# BotA Decisions Register

Last updated: **2026-09-04 UTC**

This file records active decisions. Older operational decisions remain in Git history and dated audits. Explicit supersession here controls current work.

## 2026-09-04 — Reopen BotA only as shadow research / data collection

- Status: **LOCKED CURRENT DECISION**
- Canonical evidence: `audits/BOTA_SHADOW_REOPEN_MEASUREMENT_PILOT_2026-09-04.md`.

The owner explicitly clarified the intended objective: debug BotA until it runs reliably, collect prospective shadow signals, and evaluate edge from future evidence. The 2026-09-03 closure remains historical evidence but its blanket prohibition on future shadow collection is superseded.

Decision:

```text
BOTA_SHADOW_RESEARCH=REOPENED_BY_OWNER
HISTORICAL_RETROSPECTIVE_VALIDATION_PROJECT=CLOSED
BOTA_EDGE_STATUS=UNVALIDATED
LIVE_MONEY_TRADING=NO
COMMERCIAL_PROFITLAB=NO
PRIVATE_PROFITLAB_ANALYTICS=YES
PRIMARY_RUNTIME_TARGET=HETZNER
ANDROID_ACTIVE_SCANNER=NO
NEXT_PHASE=STAGE_0_MEASUREMENT_PILOT
STRATEGY_TUNING_DURING_PILOT=NO
MEASUREMENT_HARDENING_DURING_PILOT=YES
```

This human override does not retroactively change the 195 Policy-B corpus count or the historical `195 < 400` result.

---

## 2026-09-04 — Measurement pilot must precede confirmatory testing

- Status: **LOCKED**

The final Claude/Gemini/Grok/DeepSeek/Perplexity audit cycle established that final statistical power cannot be designed honestly until BotA's execution/evidence model is measured rather than assumed.

Decision:

```text
DIRECT_CONFIRMATORY_COLLECTION_NOW=NO
MEASUREMENT_PILOT_REQUIRED=YES
PILOT_COUNTS_TOWARD_CONFIRMATORY_SAMPLE=NO
PILOT_STRATEGY_CHANGES=NO
PILOT_MEASUREMENT_CHANGES=YES
```

The pilot must prove scan completeness, singleton execution, identity/versioning, closed-bar discipline, provider identity, execution-price evidence, publication timing, resolver integrity, same-bar ambiguity handling, restart/idempotency behavior and lifecycle reconciliation.

Pilot completion is evidence-based, not N-based.

---

## 2026-09-04 — No fixed confirmatory N or 60% scientific gate is authorized

- Status: **LOCKED CORRECTION**

The previous AI review loop surfaced a key statistical correction: a genuinely new single pre-registered prospective hypothesis does not automatically inherit the historical multiple-testing Bonferroni penalty. Claude explicitly withdrew the prior application that led to the ~1,446 observation requirement.

However, later ~682 and earlier 400/500 targets still rely on simplified assumptions and are not final requirements.

Decision:

```text
FIXED_N_400=NO
FIXED_N_500=NO
FIXED_N_682=NO
FIXED_N_1446=NO
PRIMARY_FUTURE_ENDPOINT=NET_R_AFTER_REALISTIC_EXECUTION_COSTS
SEQUENTIAL_EARLY_STOPPING=PREFERRED_IN_PRINCIPLE
SEQUENTIAL_BOUNDARIES=NOT_YET_DERIVED
60_PERCENT_WIN_RATE_AS_PRIMARY_SCIENTIFIC_GATE=NO
```

`60%` win rate may remain a future business/product aspiration. It is not the definition of edge.

---

## 2026-09-04 — Hetzner is the target authoritative runtime; current host state is unproven

- Status: **LOCKED**

Historical repository evidence shows R5 no-side-effect shadow engineering work, not Production cutover.

Decision:

```text
PRIMARY_RUNTIME_TARGET=HETZNER
ANDROID_ACTIVE_SCANNER=NO
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
CURRENT_HETZNER_RUNTIME_STATE=UNPROVEN
NEXT_ACTION=READ_ONLY_HETZNER_FORENSIC_INSPECTION
```

Do not restart, deploy, reconfigure or send test signals until the actual host is inspected and reconciled with repository evidence.

---

## 2026-09-04 — Preserve and extend existing measurement infrastructure; do not rewrite blindly

- Status: **LOCKED ENGINEERING BOUNDARY**

Repository cross-check proves existing relevant controls:

- bounded watcher-cycle reconciliation in `tools/watcher_cycle_ledger.py`;
- append-only event evidence, UUID event IDs, `flock`, UTC/monotonic timing and atomic state replacement in `tools/pipeline_ledger.py`;
- fail-closed stale-candle handling in current watcher logic.

Repository evidence also confirms same-candle TP-first behavior exists and is documented as potentially optimistic.

Decision:

```text
FULL_REWRITE_REQUIRED=NO_EVIDENCE
DEFAULT_IMPLEMENTATION_PATH=MINIMUM_INCREMENTAL_MEASUREMENT_HARDENING
SAME_CANDLE_TP_FIRST_ACCEPTABLE_FOR_FINAL_CONFIRMATION=NO
```

Any measurement change that alters which signals qualify must be explicitly classified as strategy-affecting and cannot silently enter the baseline.

---

## 2026-09-03 — BotA closes as an active retrospective trading-strategy validation project

- Status: **HISTORICAL / PRESERVED; CURRENT-ACTION PROHIBITION SUPERSEDED 2026-09-04**
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

Historical decision:

```text
ACTIVE_TRADING_STRATEGY_VALIDATION=STOP
STRATEGY_TUNING_AUTHORIZED=NO
ADDITIONAL_HISTORY_FOR_RESCUE=NO
HETZNER_PRODUCTION_CUTOVER=NO
MARKET_OPEN_ACCEPTANCE_GATE=SUPERSEDED
```

### Rationale

The kill rule was fixed before the exact full frozen Policy-B count was known. The deterministic read-only corpus run returned 195, materially below the 400 kill threshold. The rule prevented post-result parameter changes, data expansion, replay expansion and indefinite retrospective continuation.

This decision did **not** prove that every BotA trade loses. It established that the then-active historical validation project failed its own pre-committed evidence-sufficiency gate.

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

Changing warm-up after observing the 195 result would create a different experiment. Earlier estimates around 500-550 Policy-B accepts under a 200-bar convention are withdrawn as unobserved extrapolation.

---

## 2026-09-03 — Economic claims must remain hypothetical until outcomes are resolved

- Status: **LOCKED EVIDENCE BOUNDARY**

The full 195 Policy-B candidate outcomes were not resolved in the final corpus run.

Therefore:

```text
OBSERVED_POLICY_B_WIN_RATE_FOR_195=UNKNOWN
40_PERCENT_WIN_RATE=ILLUSTRATIVE_ONLY
13_TRADES_PER_MONTH=ILLUSTRATIVE_ONLY
STRATEGY_PROFITABILITY_PROVEN_NEGATIVE=NO
STRATEGY_EDGE_VALIDATED=NO
```

The prior illustrative model—+2R/-1R, 40% win rate, 16.56-pip risk, 1-pip baseline cost, ~+0.14R/trade and ~2.3-pip additional edge-erasure threshold—may be retained only as historical execution-fragility context.

---

## 2026-09-03 — Optional 195-outcome resolution cannot rewrite the historical gate

- Status: **LOCKED HISTORICAL BOUNDARY**

A one-time read-only resolution of the 195 frozen Policy-B candidates may be kept as a historical record, but cannot retroactively convert the original `195 < 400` corpus result into a pass.

---

## 2026-09-03 — Hetzner/VPS Production migration was not completed

- Status: **HISTORICAL / PRESERVED**

Historical R5 VPS work remains valuable engineering evidence. It was a no-side-effect shadow, not Production cutover.

```text
R5_ENGINEERING_ARTIFACT=PRESERVE
VPS_PRODUCTION_CUTOVER_HISTORICALLY_COMPLETED=NO
```

The 2026-09-04 owner decision authorizes future **shadow measurement work only**, not live-money Production cutover.

---

## 2026-09-03 — ProfitLab was decoupled from BotA closure

- Status: **SUPERSEDED IN PART 2026-09-04**

Historical decision parked BotA as a signal dependency. Current decision allows ProfitLab to operate privately as a measurement/analytics consumer only.

```text
PROFITLAB_PUBLIC_PRODUCT=NO
PROFITLAB_PRIVATE_ANALYTICS=YES
PROFITLAB_SOURCE_OF_TRUTH=NO
```

---

## 2026-09-03 — AI consensus is not independent evidence when framing is shared

- Status: **LOCKED LESSON**

Use model outputs for adversarial error discovery, not vote counting. Shared framing creates correlated evidence.

The final 2026-09-04 review cycle deliberately assigned Claude, Gemini, Grok, DeepSeek and Perplexity different roles; the final decision is based on concrete corrections and repository/external evidence, not majority vote.

## Historical operational decisions retained

The following remain active engineering principles:

- claim-specific evidence authority;
- repository state != deployed runtime state;
- one execution owner per responsibility;
- trusted server epoch / explicit UTC semantics for trading evidence;
- useful progress != process liveness;
- immutable generation-specific deployment evidence;
- evaluation evidence != delivery evidence;
- generation barriers and terminal watcher evidence;
- no threshold lowering to manufacture activity;
- no silent provider/config/resolver drift during a confirmatory experiment.

## Current repository workflow decision

Normal changes remain branch/PR based. Documentation/governance updates do not authorize runtime, strategy, Supabase, Telegram, Android or Hetzner mutation unless explicitly stated.

## Exactly one current decision

**Inspect Hetzner read-only, then build the minimum measurement-only Stage-0 delta required for a trustworthy shadow pilot. Do not start confirmatory collection or live trading yet.**
