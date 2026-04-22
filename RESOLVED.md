# BotA Resolved Issues

## 2026-04-21 / 2026-04-22

### Yahoo 429 retry storm
- Status: RESOLVED
- Root cause:
  - Yahoo fallback could return 429 and updater retried generic non-zero exits
- Fix:
  - `tools/data_fetch_candles.sh` exits with code `3` on Yahoo 429
  - `tools/indicators_updater.sh` stops retrying on rc=3
- Proof:
  - syntax checks passed
  - fetch/build flow recovered

### phase=Unknown contract mismatch
- Status: RESOLVED
- Root cause:
  - `tools/market_open.sh` emitted descriptive strings
  - `tools/scoring_engine.sh` accepted only exact `Open` or `Closed`
- Fix:
  - `tools/market_open.sh` now emits exact `Open` or `Closed`
- Proof:
  - scorer moved from `phase=Unknown` to `market phase Closed`

### stale watcher lock regression
- Status: RESOLVED
- Root cause:
  - stale watcher lock blocked live watcher execution
- Fix:
  - stale lock detection/removal proven in watcher output
- Proof:
  - watcher resumed and executed `--once` runs successfully
