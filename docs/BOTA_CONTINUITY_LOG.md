# BotA Historical Continuity Log

> Historical record only. This file preserves April 2026 continuity evidence and does **not** define current production state. For current truth use `AI_START_HERE.md`, `CONTINUITY_CURRENT.md`, `CHAT_HANDOFF_BOTA.md`, and `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`.

## [2026-04-08] Shadow Manager + Cron Fixes (PROVEN PARTIAL)

### Fixed
- Cron Python execution corrected (python3 used instead of shell)
- restore_cron.txt cleaned and applied
- tools/run_shadow_manager.sh created and working
- Shadow manager cron entry added and executed

### Recovery
- tools/be_shadow_manager.py was lost during overwrite
- Successfully restored from latest backup
- File integrity verified (1134+ lines, py_compile PASS)

### Upgrade
- Added uniqueness contract protection in ensure_shadow_row()
- Detects missing ON CONFLICT constraint
- Logs: "UNIQUE CONTRACT ERROR"
- Prevents silent duplicate insert failures

### Proven
- py_compile PASS
- Wrapper manual execution PASS
- Shadow manager runs without runtime errors
- Schema compatibility PASS

### NOT YET PROVEN
- Uniqueness guard execution during real insert
- Duplicate shadow prevention under live signals
- Impact on signal generation

### Next Proof Step
- Wait for cron cycle with active signals
- Validate:
  - logs/cron.shadow.log
  - shadow_manager.log
  - heartbeat updates
  - ensure_shadow_row() execution path

## [2026-04-09] Runtime / Boot / D1 Refresh / Live No-Signal Root Cause

### Proven
- Cron runtime is healthy again:
  - crond running
  - logs/cron.signals.log updating
  - logs/cron.indicators.log updating
  - logs/cron.shadow.log updating
  - shadow_manager heartbeat advancing
- Boot persistence is proven:
  - after real reboot, cron logs advanced automatically
  - Termux boot path successfully restarted crond
- Shadow manager startup path is working:
  - tools/run_shadow_manager.sh works
  - logs/cron.shadow.log now updates on schedule

### D1 Cache Investigation
- Original stale-cache issue was real:
  - cache/d1_trend_EURUSD.json
  - cache/d1_trend_GBPUSD.json
  had remained stale from Apr 6
- Broken owner path identified:
  - tools/indicators_updater.sh
  - function: refresh_d1_trend_cache()
- Broken inline path produced:
  - D1 EUR_USD error: HTTP Error 400: Bad Request
  - D1 GBP_USD error: HTTP Error 400: Bad Request
- Standalone path worked:
  - bash tools/refresh_d1_cache.sh
  - refreshed both EURUSD and GBPUSD D1 cache files successfully
- indicators_updater.sh was then fixed so its internal D1 refresh now works too
- Post-fix proof:
  - bash syntax PASS
  - D1 cache timestamps refreshed
  - D1 cache contents now refresh correctly from inside tools/indicators_updater.sh

### Current Live Strategy State (historical 2026-04-09 snapshot)
- After D1 refresh fix, scorer still returned:
  - EURUSD -> HOLD / no_signal|phase=Open
  - GBPUSD -> HOLD / no_signal|phase=Open
- That historical snapshot showed this was NOT caused by D1 veto and NOT caused by ADX gate.
- Historical live M15 gate result:
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

### Historical conclusion
- At that April snapshot, silence was no longer explained by dead cron, boot failure, or stale D1 cache corruption.
- The no-signal state at that time was grounded in the then-current scoring rules and market snapshot.
- These statements must not be treated as the current August 2026 root cause or readiness gate.

### Historical next proof step
- Audit tools/scoring_engine.sh entry logic only:
  - bullish_trend
  - bearish_trend
  - pullback_buy
  - pullback_sell
- Determine whether that April no-signal behavior was intended strict regime behavior or over-restrictive calibration.

---

## [2026-08-09] Current-status pointer

Current production has moved from cron-owned core jobs to a runit-owned seven-service control plane and from two-pair historical snapshots to `EURUSD GBPUSD USDJPY` M15 production scope.

Current Package #1/#2 status is intentionally **not duplicated in full here**. Use:

- `AI_START_HERE.md`
- `CONTINUITY_CURRENT.md`
- `CHAT_HANDOFF_BOTA.md`
- `state/STATE.json`
- `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`

Current classification:

```text
PACKAGE_1_CLOCK_SESSION=PASS
LIVE_CONTROL_PLANE_REPAIR=PASS
PACKAGE_2_PERSISTENT_HARDENING=PENDING
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
MONDAY_READY=NO
```
