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

### Current Live Strategy State (most important)
- After D1 refresh fix, scorer still returns:
  - EURUSD -> HOLD / no_signal|phase=Open
  - GBPUSD -> HOLD / no_signal|phase=Open
- Live proof shows this is NOT caused by D1 veto and NOT caused by ADX gate
- Current live M15 gate result:
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

### Conclusion
- BotA silence is no longer explained by dead cron, boot failure, or stale D1 cache corruption
- Current no-signal state is now grounded in live scoring rules:
  - there is no valid M15 trend/pullback setup under current entry logic
- D1 trend remains SELL for both:
  - EURUSD
  - GBPUSD
- But D1 is not the active blocker in the current snapshot because direction is already HOLD before D1 filter is applied

### Next Proof Step
- Audit tools/scoring_engine.sh entry logic only:
  - bullish_trend
  - bearish_trend
  - pullback_buy
  - pullback_sell
- Determine whether current no-signal behavior is:
  - intended strict regime behavior
  - or over-restrictive calibration
