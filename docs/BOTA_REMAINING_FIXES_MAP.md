# BotA Remaining Fixes Map

Last updated: 2026-04-09

## 1) FIXED

### OPS-001 / OPS-002
Status: FIXED

Problem:
- Python files were being run as shell from cron paths

Proof:
- restore_cron.txt corrected to python3
- cron runtime now healthy
- no current evidence this remains the active issue

---

### OPS-003 / OPS-004
Status: FIXED

Problem:
- Shadow manager startup/config/scheduling path was broken or incomplete

Proof:
- tools/run_shadow_manager.sh created
- cron shadow entry active
- logs/cron.shadow.log advancing
- heartbeat advancing after reboot

---

### DATA-001 — Stale D1 cache refresh path
Status: FIXED

Problem:
- tools/indicators_updater.sh inline D1 refresh path failed
- EURUSD / GBPUSD D1 cache files became stale

Proof:
- old broken path emitted HTTP 400
- standalone refresh path worked
- updater file replaced with working D1 refresh logic
- D1 cache files now refresh correctly
- updated_at timestamps are current

Impact:
- stale D1 cache is no longer the cause of current no-signal behavior

---

## 2) INSTALLED / PARTIALLY PROVEN

### STRAT-002
Status: IN_PROGRESS

Problem:
- duplicate shadow rows / uniqueness contract concerns

Proven:
- hardening installed in tools/be_shadow_manager.py

Not yet proven:
- live insert-path behavior with real active signals
- duplicate prevention under actual live write conditions

Next proof:
- wait for active signals and inspect ensure_shadow_row() path

---

## 3) OPEN

### STRAT-003 — Current no-signal behavior in live scoring logic
Status: OPEN

Problem:
- After runtime recovery and D1 refresh fix, watched pairs still return HOLD / no_signal

Proven current snapshot:
- EURUSD:
  - bullish_trend=False
  - bearish_trend=False
  - pullback_buy=False
  - pullback_sell=False
  - direction_before_d1=HOLD
- GBPUSD:
  - bullish_trend=False
  - bearish_trend=False
  - pullback_buy=False
  - pullback_sell=False
  - direction_before_d1=HOLD

Conclusion:
- current active blocker is scoring entry logic
- not cron
- not boot persistence
- not stale D1 cache
- not D1 veto in the current snapshot
- not ADX gate in the current snapshot

Next target file:
- tools/scoring_engine.sh

Next audit scope only:
- bullish_trend
- bearish_trend
- pullback_buy
- pullback_sell

---

## 4) OPEN / UNKNOWN

### OPS-005
Status: OPEN

Problem:
- unclear whether closer/network issues affect downstream result tracking materially

Status:
- not current highest-priority blocker

---

## 5) Rules for Updating This File

1. Move items only with proof.
2. Never mark FIXED from reasoning alone.
3. Record:
   - exact file
   - exact proof source
   - what is no longer the blocker
4. If a new chat starts, use this file first before repeating validation work.

---

## 6) Change Log

### 2026-04-07
- Created canonical remaining-fixes map.
- Recorded TP/SL cap math as proven fixed.
- Recorded simulator and replay-rule fixes as proven fixed.
- Captured operational errors from logs.
- Captured current strategy validation blockers and unknowns.

### 2026-04-09
- Marked cron runtime healthy and boot persistence proven.
- Marked shadow scheduling/startup path fixed.
- Marked D1 stale-cache bug fixed in tools/indicators_updater.sh.
- Added current live no-signal root cause:
  scoring entry logic currently produces no valid trend/pullback setup.
