# BotA Continuity Log (Running)

## Latest Update — 2026-02-21 (T31S3, T32S1–T32S3)

### Fixed (confirmed)
- Added **OFFLINE replay mode**: `tools/replay_mode.sh`
  - Reads `cache/indicators_<PAIR>_<TF>.json`
  - Computes **direction + entry + SL/TP + RR + ATR**
  - **Never sends Telegram**
- Added **OFFLINE replay suite**: `tools/replay_suite.sh`
  - Runs replay across cached indicators files and prints evidence lines.
- Added **OFFLINE pipeline replay**: `tools/pipeline_replay.sh`
  - Generates replay JSON + produces the **Telegram-ready formatted card text** via `tools/format_card.py` (no send).

### Proven working (evidence from your paste)
- Indicators are sane for EURUSD M15:
  - `price=1.178550...`, `atr=0.0005748...`, `atr_pips=5.748...`, `tf_ok=true`, `weak=false`
- Replay suite smoke test:
  - `[SUITE_SUMMARY] runs=9 tradeable_not_rejected=6 rejected=3 one_tests_passed=9 one_tests_failed=0`
  - Example tradeable lines (not rejected):
    - `EURUSD M15 dir=BUY rejected=False rr=1.333... atr=0.0005748... entry=1.17855...`
    - `GBPUSD M15 dir=SELL rejected=False rr=1.333... atr=0.0007266... entry=1.34812...`
    - `USDJPY M15 dir=SELL rejected=False rr=1.333... atr=0.132129... entry=154.988...`

### Root-cause proof (why live fusion shows entry/atr/sl/tp = 0.0)
- `tools/scoring_engine.sh` is currently emitting a **fail-closed** payload with:
  - `provider="scoring_engine_market"`
  - `reasons="market phase Closed"`
  - `entry=0.0`, `atr=0.0`, `sl=0.0`, `tp=0.0`, `filter_rejected=true`
- `tools/m15_h1_fusion.sh` is inheriting that JSON (it does not recompute entry/atr/sl/tp).

### Blocking issues (still open)
- Live pipeline depends on:
  - market-status logic (weekend closed vs open)
  - gating thresholds (score/min score)
  - quality filter reasons derived from live JSON.
- We need the live engine to:
  - stay fail-closed on weekends
  - but be correct and non-degenerate during open sessions, and produce actionable fields when tradeable.

### Next proof step (do next)
- Run `tools/pipeline_replay.sh EURUSD M15` and paste:
  - `[PIPELINE] ...`
  - `[PIPELINE_RUNLINE] ...`
  - the full `[PIPELINE_CARD] begin ... end` block (if present)
- Then we do the live fix: adjust `tools/scoring_engine.sh` market-status branch so it doesn’t destroy computed fields (and confirm correct “open vs closed” detection during an actual open session).

## Latest Update — 2026-04-19

### Fixed (confirmed)
- none yet (inspection/proof only; no file replaced in this debugging branch)

### Proven working (evidence from your paste)
- OANDA auth endpoint test returned `HTTP 200` in about `1.51s`
- Yahoo chart endpoint test returned `HTTP 429` in about `0.70s`
- Current runtime state is correctly classified as `DEGRADED`, reason=`yahoo_rate_limited`
- Full current file `tools/data_fetch_candles.sh` was captured successfully (`225` lines)
- `tools/data_fetch_candles.sh` uses OANDA as primary and Yahoo as fallback
- OANDA Python fetch path already has `timeout=15` in `urllib.request.urlopen(...)`
- Yahoo `curl` fallback currently has no `--max-time`
- Yahoo `wget` fallback currently has no timeout option
- No proven `429`-specific handling exists in `tools/data_fetch_candles.sh`

### Blocking issues (still open)
- Yahoo fallback can hang too long on slow ship internet
- Yahoo fallback is not `429`-aware, so it can contribute to retry storms / degraded behavior
- There is still no explicit degraded/offline state file or recovery-notice flow

### Next proof step / next safe change
- Replace `tools/data_fetch_candles.sh` only
- Scope of change: add bounded Yahoo timeout handling and explicit `429`-aware fail-closed behavior
- Do not change scoring, watcher thresholds, or strategy logic in this step

## Recovery Update — 2026-04-19 (Updater path)

### Fixed (confirmed)
- `tools/data_fetch_candles.sh` updated so Yahoo fallback is bounded and 429-aware
- `tools/indicators_updater.sh` updated so exit code `3` (Yahoo rate limit) skips retry storm behavior
- `bash -n tools/data_fetch_candles.sh` passed
- `bash -n tools/indicators_updater.sh` passed

### Proven working (evidence from live run)
- `tools/data_fetch_candles.sh` contains Yahoo 429 exit path:
  - curl branch exits `3`
  - wget branch exits `3`
- `tools/indicators_updater.sh` catches `rc=3` and skips retries
- Manual updater run completed with:
  - `fetch_fail_count=0`
  - `build_fail_count=0`
- Fresh caches and indicators were rebuilt successfully across the pasted pairs/timeframes
- D1 refresh ran and printed:
  - `EURUSD: BUY`
  - `GBPUSD: BUY`

### Not yet fully proven
- Next real watcher/cron cycle has not yet been evidenced in this log entry
- Telegram/send path for the recovery cycle is not yet evidenced here

### Blocking issues (remaining)
- Need one watcher-cycle proof after recovery:
  - watcher reads fresh indicators
  - watcher evaluates normally
  - no stale-lock regression
- Explicit degraded/offline mode is still not implemented
- Recovery/back-online Telegram state notice is still not implemented

### Next proof step
- After the next `:00/:15/:30/:45` cycle, capture watcher evidence from logs
- Goal: prove end-to-end pipeline health beyond the updater path

## Recovery Update — 2026-04-21 (ADX gate proof)

### Fixed (confirmed)
- none in this step (inspection/proof only)

### Proven working
- `tools/scoring_engine.sh` hard ADX regime gate is the live source of zeroed HOLD payloads:
  - lines `468-476` emit `entry=0.0`, `sl=0.0`, `tp=0.0`, `price=0.0`, `atr=0.0` when `adx < 20.0`
- EURUSD M15 live indicators are healthy before the gate:
  - `price=1.17905`
  - `atr=0.0003672800343187802`
  - `adx=18.6`
  - `tf_ok=True`
  - `weak=False`
- Shadow pre-gate proof exists for EURUSD M15:
  - `direction_pre_gate='BUY'`
  - `score_partial_pre_gate=51.6`
  - `confidence_partial_pre_gate=51.6`
  - `entry=1.17905`
  - `sl=1.17832`
  - `tp=1.18052`
  - `volatility='low'`
  - `gate_status_current='blocked_lt20'`
  - `d1_trend='BUY'`

### Root-cause clarification
- The zeroed contract is real, but it is NOT the only alert blocker
- EURUSD pre-gate score (`51.6`) is still below live watcher thresholds:
  - `FILTER_SCORE_MIN=65`
  - `TELEGRAM_MIN_SCORE=70`
- Therefore, preserving context for `15 <= adx < 20` would improve observability, but would NOT restore Telegram alerts by itself
- GBPUSD remains much weaker (`adx=9.6`) and should remain blocked

### Blocking issues (current)
- No alert-grade setup currently passes live thresholds
- ADX gate zeroing still degrades payload quality / diagnostics
- If desired later, safest scorer change is:
  - preserve context fields for `15 <= adx < 20`
  - keep `direction=HOLD` and `filter_rejected=true`
  - do NOT relax the gate for `adx < 15`

### Next proof step
- Prove whether any current pair/timeframe can exceed `FILTER_SCORE_MIN=65` under live conditions
- Do not patch the scorer before deciding whether the goal is observability cleanup or actual signal frequency change

## Recovery Update — 2026-04-21 (Live score survey)

### Fixed (confirmed)
- none in this step (inspection/proof only)

### Proven working
- Watcher is alive and consuming fresh M15 caches after immediate refresh
- Active watcher scope from SANITY output is:
  - `PAIRS="EURUSD GBPUSD"`
  - `TIMEFRAMES="M15"`
- Live score survey proves the scorer is not globally broken:
  - `GBPUSD D1` scored `70.1`
  - `EURJPY D1` scored `85.5`
  - `EURJPY M15` scored `53.1`

### Root-cause clarification
- Current alert silence is expected under the active watched scope
- In the watched live universe (`EURUSD/GBPUSD`, `M15`), no setup currently clears the live gates:
  - `EURUSD M15` blocked by `adx_regime_block` with `adx=18.6`
  - `GBPUSD M15` blocked by `adx_regime_block` with `adx=9.6`
- Therefore:
  - BotA pipeline is operational
  - scorer can reach threshold on other pair/timeframe combinations
  - but no alert-grade setup currently exists inside the active watcher universe

### Blocking issues (current)
- No current watched M15 setup passes:
  - `FILTER_SCORE_MIN=65`
  - `TELEGRAM_MIN_SCORE=70`
- ADX zeroing still reduces payload observability, but is not the only alert blocker
- High-scoring setups currently exist outside the watched universe, not inside it

### Next decision point
- Keep current strict scope (`EURUSD GBPUSD`, `M15`) and accept no alerts until market regime improves
- OR later evaluate strategy/config scope changes if more signal frequency is desired

## Recovery Update — 2026-04-20 (DeepSource shell compatibility fix)

### Fixed (confirmed)
- DeepSource Shell issue `SH-3014` in `tools/data_fetch_candles.sh` was corrected
- Changed Yahoo HTTP comparisons from `==` to `=` for shell portability
- `bash -n tools/data_fetch_candles.sh` passed after the change

### Proven working
- Current `YAHOO_HTTP` checks now use:
  - `if [[ "${YAHOO_HTTP}" = "429" ]]; then`
  - `[[ "${YAHOO_HTTP}" = "200" && -s "${TMP_JSON}" ]] || die ...`
- This preserves Bash behavior while removing the POSIX-compatibility warning flagged by DeepSource/ShellCheck

### Not yet fully proven
- Watcher log evidence for consuming the fresh 2026-04-20 16:27 M15 indicators is still pending

### Next proof step
- Force one watcher run now and inspect the newest watcher log lines

## Architecture Lock — 2026-04-24 (Boot ownership model)

### Frozen decisions
- bota_supervisor.sh: FROZEN. Works correctly when run manually. No changes until reboot proof exists.
- Boot script owns daemon resurrection. Cron owns recurring jobs. Supervisor owns detection and state logging once cron is alive.
- ~/.termux/boot/start_bota.sh is the single point of autonomous crond recovery.

### Android platform risk (production contract)
- Termux battery optimization MUST be set to Unrestricted (not Optimized).
- Termux:Boot battery optimization MUST be set to Unrestricted.
- Termux:Boot app must be opened once after every fresh install or Android update.
- Android 13+: BOOT_COMPLETED may be delayed until Termux is manually opened once after reboot.
- Background restrictions in battery saver profiles can silently kill crond.
- These are platform risks, not BotA code risks. Verify after every Android OS update.

### Remaining proof required
- One real phone reboot must produce:
  - logs/boot.log entry: BOOT_OK crond_pid=XXXXX
  - crond visible in ps -ef within 30s of boot
  - logs/cron.supervisor.log advancing at next */5 tick without manual intervention
- Until that proof exists, autonomous recovery is NOT fully proven.

## Session Update — 2026-04-26 (BotA git auth migrated from HTTPS+PAT to SSH)

### Fixed (confirmed)
- BotA git auth path migrated from HTTPS + PAT to SSH
- Existing local key `~/.ssh/id_ed25519` was reused; no new key was generated
- GitHub SSH auth test passed:
  - `Hi Ciupanezulflipper! You've successfully authenticated, but GitHub does not provide shell access.`
- BotA remote changed to:
  - `git@github.com:Ciupanezulflipper/BotA_Prod_2025_11.git`

### Proven working
- `git fetch origin` over SSH passed
- `git push origin main` over SSH passed
- latest proven push:
  - `83dcbc9..5b781dc  main -> main`
- `git remote -v` now shows SSH for fetch and push
- `git config --get remote.origin.url` now returns SSH URL

### Root-cause clarification
- Previous Git path depended on HTTPS remote + stored credentials/PAT
- BotA no longer depends on PAT for normal `git pull` / `git push`
- Global `credential.helper=store` may still exist, but it is no longer the active auth path for BotA because BotA remote is now SSH

### Current status
- Git auth for BotA: CLOSED
- Infra auth path for repo operations: SSH
- PAT is no longer the primary git path for BotA

### Next proof step
- None required for BotA git auth migration
- Optional future hygiene step: assess whether old stored HTTPS GitHub credentials should be removed from the global credential store
