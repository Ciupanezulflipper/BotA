
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

