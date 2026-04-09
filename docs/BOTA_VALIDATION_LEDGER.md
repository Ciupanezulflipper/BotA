# BotA Validation Ledger

Last updated: 2026-04-09

Purpose:
- Prevent repeated validation work
- Preserve grounded proof across chats / AIs
- Separate PROVEN vs INFERRED vs UNKNOWN

---

## VALIDATION-001 — Cron runtime alive
Status: PROVEN

Evidence:
- crond running
- logs/cron.signals.log advancing
- logs/cron.indicators.log advancing
- logs/cron.shadow.log advancing
- shadow_manager heartbeat advancing

Conclusion:
- BotA cron runtime is alive and executing on schedule

Repeat this check again only if:
- cron logs stop advancing
- pgrep shows no crond
- heartbeat goes stale again

---

## VALIDATION-002 — Boot persistence
Status: PROVEN

Evidence:
- real device reboot performed
- after reboot:
  - cron.indicators.log advanced
  - cron.signals.log advanced
  - cron.shadow.log advanced
  - shadow_manager_heartbeat advanced

Conclusion:
- boot persistence is working for crond / cron-driven BotA tasks

Repeat this check again only if:
- reboot behavior changes
- boot scripts are edited
- Android background/boot settings are changed

---

## VALIDATION-003 — Shadow manager startup
Status: PROVEN

Evidence:
- tools/run_shadow_manager.sh created and used
- manual wrapper smoke test passed
- logs/shadow_manager.log shows normal startup and completion
- logs/cron.shadow.log now updates on schedule

Conclusion:
- Shadow manager startup/bootstrap path is working

---

## VALIDATION-004 — Unique-contract hardening
Status: INSTALLED_NOT_FULLY_EXERCISED

Evidence:
- tools/be_shadow_manager.py contains UNIQ_CONFLICT_ERR / UNIQUE CONTRACT ERROR markers
- file compiles successfully
- wrapper smoke test passed

Not yet proven:
- real ensure_shadow_row() failure path under active-signal conditions
- missing DB uniqueness contract behavior in live insert path

Conclusion:
- protection is installed, but not yet fully exercised with live active signals

---

## VALIDATION-005 — Stale D1 cache bug
Status: PROVEN_FIXED

Evidence:
- stale D1 cache files existed for EURUSD / GBPUSD
- broken owner path identified:
  - tools/indicators_updater.sh
  - refresh_d1_trend_cache()
- broken inline path emitted HTTP 400 errors
- standalone refresh_d1_cache.sh worked
- updater file was replaced with working D1 refresh logic
- post-fix proof:
  - bash -n tools/indicators_updater.sh => PASS
  - D1 refresh output printed for EURUSD and GBPUSD
  - cache/d1_trend_EURUSD.json refreshed
  - cache/d1_trend_GBPUSD.json refreshed
  - updated_at values advanced

Conclusion:
- D1 cache refresh corruption is fixed

Do not repeat:
- stale-cache root cause investigation
unless this updater file changes again or D1 cache stops updating

---

## VALIDATION-006 — Current live no-signal reason
Status: PROVEN

Evidence:
- scorer after D1 fix still returns:
  - EURUSD HOLD no_signal|phase=Open
  - GBPUSD HOLD no_signal|phase=Open
- live M15 proof shows:
  - bullish_trend=False
  - bearish_trend=False
  - pullback_buy=False
  - pullback_sell=False
  - direction_before_d1=HOLD
- D1 trend is SELL for both, but direction is already HOLD before D1 filter

Conclusion:
- current live no-signal state is caused by entry logic not producing a tradeable trend/pullback setup
- D1 veto is not the active blocker in the current snapshot
- ADX gate is not the active blocker in the current snapshot

Do not repeat:
- boot/cron/D1-staleness checks before first re-checking current scoring conditions

---

## VALIDATION-007 — Still unknown
Status: UNKNOWN

Unknowns:
- whether current pullback/trend rules are intentionally strict or over-restrictive
- whether future live snapshots will fail mainly on:
  - no trend/pullback
  - D1 veto
  - ADX gate
- whether strategy calibration should be changed after audit

Next target:
- audit tools/scoring_engine.sh entry logic only
