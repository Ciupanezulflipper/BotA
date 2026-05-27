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

## Session Update — 2026-04-26 (Gitleaks root-cause clarified)

### Proven working
- Custom OANDA gitleaks rule is NOT the source of the current failure:
  - it matches token-shaped values, not plain variable names
- OANDA matches in code were proven to be env-var reads/usages only:
  - `tools/data_fetch_candles.sh`
  - `tools/backtest_bota.py`
  - `tools/shadow_outcome_simulator.py`

### Root-cause clarification
- Historical secret-bearing files were committed in git history:
  - `.env` introduced in commit `a60e5d51b430c90555bcec0cc0cd2343f1261747`
  - `config/tele.env` introduced in commit `c0724ad36c4d68eafe2fa7bd78b1409173ebb108`
- Historical `.env` contained multiple real secret fields / API-key fields (redacted during audit)
- Historical `config/tele.env` contained Telegram credentials (redacted during audit)
- These paths are not globally allowlisted in `.gitleaks.toml`
- Therefore the current GitHub Actions Gitleaks failure is likely a valid historical-secrets finding, not a false positive from OANDA variable names

### Do not do yet
- Do NOT weaken `.gitleaks.toml`
- Do NOT allowlist `.env` or `config/tele.env`
- Do NOT classify the current Gitleaks failure as false positive

### Next proof / decision step
- Decide remediation path:
  - rotate any still-live exposed credentials
  - then decide whether to keep history as-is or do a history rewrite

## Session Update — 2026-04-26 (Secret rotation scope deferred)

### Decision
- Full credential rotation is intentionally deferred for now
- Immediate priority, if rotation starts later, is limited to high-blast-radius secrets only:
  - OANDA_API_TOKEN
  - SUPABASE_SERVICE_KEY
  - TELEGRAM_BOT_TOKEN

### Deferred
- Read-only / lower-priority provider keys are not being rotated in this session:
  - TWELVE_DATA_API_KEY
  - ALPHA_VANTAGE_API_KEY
  - FINNHUB_API_KEY
  - EODHD_API_KEY
  - FMP_API_KEY
  - POLYGON_API_KEY
  - NEWS_API_KEY
  - FRED_API_KEY
  - RAPIDAPI_CALENDAR_KEY

### Guardrail
- Do NOT weaken .gitleaks.toml yet
- Do NOT mark the historical exposure issue as resolved
- Gitleaks remediation remains open until either:
  - live critical secrets are rotated, and/or
  - a history-rewrite decision is made

## 2026-05-07T06:04:18Z — Ship clock/network/cache audit update

### Fixed / proven
- `tools/signal_watcher_pro.sh` server-clock patch is now present.
- Patch markers found: `v2.0.3 ship-mode server clock`, `compute_server_clock_epoch`, `BOTA_SERVER_EPOCH`.
- Watcher syntax check passed.
- Strategy thresholds were not changed.
- No scoring/Telegram/Supabase strategy changes were made.

### Proven current blockers
- Raw M15 cache is stale:
  - EURUSD/GBPUSD/USDJPY M15 last cache candle: `2026-05-05T18:30:00Z`.
- Current provider/cache audit showed server-clock source failure in that run:
  - Google/Cloudflare/OANDA/Yahoo Date headers missing in the audit script.
- However network audit clarified this is not a simple DNS failure:
  - Curl resolved provider hostnames.
  - TLS handshakes completed.
  - Python `socket_gethostbyname` resolved hosts.
  - Python urllib got `200` from Google with a valid Date header.
  - Cloudflare/OANDA returned HTTP 403 at root; Yahoo returned HTTP 429, meaning endpoints are reachable but may reject/limit root requests.
- `curl_exit_code=23` is likely an artifact from piping verbose curl output to `head`, not proof of provider failure.
- Most important runtime proof:
  - `NO_RELEVANT_PROCESSES_FOUND`
  - This means `crond` was not running at audit time, so scheduled cache refresh was not active.

### Interpretation
- The original local-phone clock freshness bug is fixed/patched in watcher.
- The active issue is now runtime/cache refresh:
  1. crond was not running;
  2. cache remained stale;
  3. watcher correctly refused to score stale candles.
- Secondary possible issue: server-clock helper should be hardened to read Date headers from HTTPError responses or use more reliable endpoints.

### Next proof step
1. Restart/verify `crond`.
2. Run manual `tools/indicators_updater.sh`.
3. Confirm M15 cache last candle advances.
4. Run dry watcher again and verify it reaches FILTER/scoring rather than STALE.
5. If server clock still fails while Python urllib can read Google Date, patch only the server-clock helper.

## 2026-05-07T06:24:52Z — Runtime validation after ship-clock fix

### Fixed / proven
- GitHub contains the watcher server-clock patch.
- Manual updater succeeded with `manual_updater_exit_code=0`.
- M15 raw cache refreshed successfully:
  - EURUSD/GBPUSD/USDJPY last M15 candle: `2026-05-07T03:45:00Z`
  - age vs server: `1481s`
  - `PASS_CACHE_FRESHNESS=pass`
- Watcher dry run reached scoring/filter:
  - `PASS_WATCHER_SERVER_CLOCK=pass`
  - `PASS_WATCHER_REACHED_SCORING=pass`
  - `WATCHER_STALE_PRESENT=no`

### Important correction
- Previous broad `pgrep -af crond` check was unreliable because it matched report/log text containing `crond`.
- Use `pgrep -x crond` only for exact crond validation.

### Remaining production proof
- Confirm exact crond daemon with `pgrep -x crond`.
- Confirm `tools/market_open.sh` allows watcher during valid market time.
- If market gate fails incorrectly, patch market gate separately.

## 2026-05-07T06:34:51Z — market_open.sh patched to server UTC

### Fixed / proven
- `tools/market_open.sh` replaced with server-clock based market gate.
- Reason: device UTC is wrong by ~7116 seconds during cruise ship time changes.
- Original session rules preserved: `07:00-20:00 UTC Mon-Fri`.
- Fail-closed behavior added if server UTC cannot be computed.
- Strategy thresholds/scoring unchanged.

### Expected behavior
- At real server UTC around `04:30`, market gate should correctly output `Closed`.
- It should not open early just because Android/device UTC is ahead.
- After real server UTC reaches `07:00`, gate should output `Open` if weekday and server clock is available.

## 2026-05-08T22:35:26Z — Sea-day health check passed

- Health check run during sea-day ship time changes before Sydney.
- Exact crond check passed.
- `market_open.sh` used server UTC and correctly returned Closed after 20:00 UTC.
- M15 cache was fresh.
- Watcher dry run reached scoring/filter.
- No stale skip appeared.
- Strategy changed: NO.
- No further code changes required at this stage.

---
## 2026-05-09 — Full Audit + Security Cleanup

### Infrastructure
- v2.0.3 clock fix active: signal_watcher_pro.sh + market_open.sh
- Crond: running | Cache: healthy when market open
- Watcher reaches scoring: confirmed

### Signal Drought (confirmed causes)
- Apr 16–May 6: clock drift → false STALE → 0 candidates generated → FIXED
- Apr 24: 3 candidates (score 68–76) blocked by H1_trend_neutral
  - H4 direction on Apr 24 = UNKNOWN (not provable from current files)
- May 8–9: weak setup — MACD=0, ADX<27, BB squeeze, genuine score 49–59
- Post-Apr-14 accepted score≥70 rows: 0
- macro6=3: confirmed informational only, not a hard rejection gate

### Supabase
- Stuck ACTIVE signal (Apr 10 EURUSD BUY) closed → CANCELLED
- shadow_log correct: CLOSED_TP +24 pips 2.017R

### Security
- Archive token files: removed from git tracking
- config.backup-* / _snapshots / archive paths: allowlisted in .gitleaks.toml
- GitHub Security Scan: PASS (commit fa6aeda)
- Old tokens in history: rotated during March 2026 Termux rebuild

### Next Engineering Step (not urgent)
- Build rejected-candidate shadow feeder for score≥55 H1-vetoed rows
- Uses existing: be_shadow_manager.py, shadow_log table, shadow_outcome_simulator.py
- Goal: prove whether H1 filter protects or over-filters
- Do on next port day with stable internet

---
## 2026-05-09 — Documentation Corrections (post-ChatGPT-5 repo verification)

### signal_closer.py local limitation
Manual local run requires service key sourcing before execution:
  set -a; source config/strategy.env; set +a
  python3 tools/signal_closer.py --live --confirm CLOSE_SIGNALS --max-batch 1
Plain shell environment without this source will fail with SUPABASE_SERVICE_KEY not set.
The Supabase closure itself succeeded — this is a local env sourcing note only.

### Twelve Data credit watch item
Twelve Data is used by emit_snapshot.py for H1/H4/D1 confluence vote context.
Credit exhaustion (seen at 600/800 in Telegram warnings Apr 26, May 4, May 6)
may degrade higher-timeframe vote quality but does not block signal generation.
Not a confirmed drought cause. Mark as data-quality risk to monitor.

### Security scan commit reference correction
Security checks PASS through latest session commit 41c7753
(not fa6aeda as previously noted — 41c7753 is the docs commit that also passes all checks).

---
## 2026-05-09 — Rejected Candidate Shadow Tracker v1.1

### Added
- New file: `tools/rejected_shadow_tracker.py`
- Output target: `logs/rejected_shadow_outcomes.jsonl`
- Purpose: replay rejected BUY/SELL candidates from `logs/alerts.csv` using OANDA M15 candles.
- Safety contract:
  - No Telegram sends.
  - No Supabase writes.
  - No live signal-table writes.
  - No scoring/strategy/threshold changes.
  - No cron installed yet.

### Important implementation details
- Uses trusted server UTC from HTTP Date headers to avoid Android/ship clock drift.
- Skips alert rows that are future-dated versus trusted server UTC.
- Uses `TP_FIRST_LIVE_MATCH` same-candle policy to match the proven BotA live closer behavior.
- Final dedup only applies to final outcomes: `TP_HIT`, `SL_HIT`, `EXPIRED_NO_HIT`.
- Retryable states such as fetch errors or pending rows are not treated as final.
- Candidate key includes pair, timeframe, direction, timestamp, entry, SL, and TP.
- Stores both `filter_reason` and `reasons` from `alerts.csv`.

### First test result
- Initial draft run failed with OANDA HTTP 400 because device/alert timestamps were ahead of OANDA server time.
- Invalid first output was archived as `logs/rejected_shadow_outcomes.jsonl.invalid_future_ts.*.bak`.
- After server-clock patch, live run succeeded:
  - rows: 2
  - fetch_errors: 0
  - EURUSD BUY score 55.2 -> `SL_HIT` -11.7 pips
  - GBPUSD BUY score 56.2 -> `SL_HIT` -13.7 pips
- Interpretation: these low-score rejected candidates would have lost, so this tiny sample supports the score filter. It does not yet prove whether H1 neutral/veto is over-filtering.

### Next
- Do not add cron yet.
- Wait for real non-future rejected candidates, especially score >=65 H1-neutral/H1-veto rows.
- After enough samples, analyze score-gated vs H1-blocked outcomes.

---
## 2026-05-09T04:06:44Z — Shadow Tracker Commit/Push Success

### Confirmed final state
- Rejected candidate shadow tracker is installed and pushed.
- Commit recorded: `71db50c`
- File added: `tools/rejected_shadow_tracker.py`
- Documentation updated: `CONTINUITY.md`, `BOOTLOG.md`
- First useful replay passed:
  - rows replayed: 2
  - fetch_errors: 0
  - outcomes: 2 x `SL_HIT`
  - EURUSD BUY score 55.2 -> -11.7 pips
  - GBPUSD BUY score 56.2 -> -13.7 pips

### Safety state
- Production changed: NO
- Strategy changed: NO
- Telegram changed: NO
- Cron added: NO
- Supabase writes: NO
- Signal table writes: NO

### Interpretation
- The first two low-score rejected candidates would have lost.
- This supports the current low-score filter on this tiny sample.
- It does not yet prove whether H1 neutral/veto is over-filtering.

### Next step
- Do not add cron yet.
- Wait for real non-future rejected candidates, especially score >=65 H1-neutral/H1-veto rows.
- Later analyze `logs/rejected_shadow_outcomes.jsonl` once enough samples exist.

---
## 2026-05-12 — First Signal After April 14 Drought

EURUSD M15 BUY fired at 01:02 local time.
Score: 75.70 | H1_trend_neutral_overridden | macro6=3
Entry: 1.17870 | SL: 1.17760 | TP: 1.18090

Confirmed working:
- v2.0.3 server clock fix
- market_open.sh server clock fix
- Watcher reaching scoring and Telegram delivery
- H1 neutral override at score >= 75 (H1_VETO_OVERRIDE_SCORE=75 in .env.runtime)

Drought confirmed resolved. 28-day gap explained by clock drift + weak market setup.
Twelve Data 600/800 warning at 08:28 — monitor but not urgent.

---
## 2026-05-12T01:04:58Z — First Accepted Signal After April Drought

### Signal observed
- Pair/timeframe: EURUSD M15
- Direction: BUY
- Score: 75.70
- Filter state: `macro6=3 | H1_trend_neutral_overridden`
- Entry: 1.17870
- SL: 1.17760
- TP: 1.18090
- Telegram delivery: CONFIRMED by received Telegram alert and chart image.
- Displayed Telegram time: 01:02 on May 12.
- Note: displayed Telegram time is not recorded here as UTC unless confirmed directly from logs.

### What this proves
- BotA can send accepted Telegram trade alerts again.
- Chart image delivery works.
- H1 neutral override path is active when score reaches the override threshold.
- The long signal drought is no longer an active total-send failure.

### What remains to monitor
- Twelve Data warning observed: 600/800 credits used. Monitor, but no immediate strategy/code change made.
- Later manual check showed `server_clock_unavailable`, so server-clock source availability still needs monitoring under ship internet conditions.
- Rejected shadow tracker should continue being used manually before adding cron.

### Safety state
- Production changed: NO
- Strategy changed: NO
- Telegram changed: NO
- Cron changed: NO

---
## 2026-05-12 — Telegram Branding Updated

Toma Signal AI / BotA logo accepted and uploaded to Telegram.

Confirmed:
- Telegram visual branding updated.
- Bot identity is now clearer for users/subscribers.
- No production code changed.
- No trading strategy changed.
- No cron changed.

---
## 2026-05-14 — Shadow Tracker Fix + First H1 Outcome Proof

### Bug Fixed
`tools/rejected_shadow_tracker.py` was not recognizing the current `alerts.csv` filter column name: `filter_str`.

Previous lookup:
`["filter_reason", "filter_reasons", "filters"]`

Fixed lookup:
`["filter_reason", "filter_reasons", "filters", "filter_str"]`

Patch applied at line 369. Syntax check passed.

### Grounded Outcome Inspection
`logs/rejected_shadow_outcomes.jsonl` was joined back to `logs/alerts.csv` using timestamp, pair, timeframe, direction, entry, SL, and TP.

Join result:
- Shadow rows inspected: 10
- Matched back to alerts.csv: 10
- Unmatched: 0
- Outcome counts: 7 SL_HIT, 3 OPEN_PENDING
- Matched H1_trend_neutral rows: 8
- Matched score-gate rows: 2

### H1_trend_neutral Resolved Outcomes
Resolved H1_trend_neutral rows so far:

- 2026-04-23 14:47 UTC — EURUSD BUY score=76.1 -> SL_HIT -16.1p
- 2026-04-23 15:46 UTC — EURUSD BUY score=71.7 -> SL_HIT -16.0p
- 2026-04-23 16:00 UTC — EURUSD BUY score=68.7 -> SL_HIT -16.0p
- 2026-05-11 14:30 UTC — EURUSD BUY score=68.5 -> SL_HIT -11.2p
- 2026-05-11 16:51 UTC — GBPUSD BUY score=71.0 -> SL_HIT -17.9p

Resolved H1 sample:
- TP_HIT: 0
- SL_HIT: 5
- WR: 0%
- Sample size: 5 resolved H1 rows

### H1_trend_neutral OPEN_PENDING
Still unresolved:

- 2026-05-13 15:49 UTC — GBPUSD BUY score=71.0
- 2026-05-13 16:00 UTC — GBPUSD BUY score=68.0
- 2026-05-13 16:16 UTC — GBPUSD BUY score=66.0

### Current Conclusion
Current evidence says the H1_trend_neutral gate is protective, not merely strangling throughput.

Do not lower the H1 override threshold yet.
Do not remove the H1 veto yet.
Do not increase alert aggressiveness based only on signal drought frustration.

### Limitations
- Resolved H1 sample size is still small: 5.
- 3 H1 rows remain OPEN_PENDING.
- This is evidence, not final proof.
- The 2 score<65 rows are a separate category and should not be mixed into H1-veto conclusions.

### Next Step
After the 3 OPEN_PENDING rows have had enough time to resolve, rerun:

`python3 tools/rejected_shadow_tracker.py --score-min 65 --lookback-hours 720 --outcome-hours 24`

Then re-inspect `logs/rejected_shadow_outcomes.jsonl` and join back to `alerts.csv` again.

---
## 2026-05-14 — Shadow Tracker Dedup Fix + Final Outcome State

### Dedup fix applied to logs/rejected_shadow_outcomes.jsonl
Before=13 after=10 removed=3 duplicate OPEN_PENDING rows.
Cause: tracker wrote May 13 rows twice (before and after filter_str fix).
Fix: keep-last dedup by (ts[:16], pair, direction, entry).

### Current JSONL state (10 rows, clean)
Resolved (7): all SL_HIT, WR=0.0%
  2026-04-23 14:47 EURUSD score=76.1 -> SL_HIT -16.1p  [H1_trend_neutral - join confirmed]
  2026-04-23 15:46 EURUSD score=71.7 -> SL_HIT -16.0p  [H1_trend_neutral - join confirmed]
  2026-04-23 16:00 EURUSD score=68.7 -> SL_HIT -16.0p  [H1_trend_neutral - join confirmed]
  2026-05-07 14:15 EURUSD score=55.2 -> SL_HIT -11.7p  [score_gate, written by --score-min 55 run]
  2026-05-07 14:30 GBPUSD score=56.2 -> SL_HIT -13.7p  [score_gate, written by --score-min 55 run]
  2026-05-11 14:30 EURUSD score=68.5 -> SL_HIT -11.2p  [H1_trend_neutral - join confirmed]
  2026-05-11 16:51 GBPUSD score=71.0 -> SL_HIT -17.9p  [H1_trend_neutral - join confirmed]

Pending (3): OPEN_PENDING, resolve after 2026-05-14T15:49Z
  2026-05-13 15:49 GBPUSD score=71.0  h1=True
  2026-05-13 16:00 GBPUSD score=68.0  h1=True
  2026-05-13 16:16 GBPUSD score=66.0  h1=True

### h1=False on resolved rows — known artifact
Resolved rows were written before filter_str fix. h1 labels unreliable for those rows.
Attribution confirmed separately via ChatGPT-5 CSV join: matched_H1_trend_neutral=8.
5 of 7 resolved = H1_trend_neutral vetoed. 2 of 7 = score_gate (score 55-56).

### Evidence summary
H1-vetoed resolved: 5 — all SL_HIT
Score-gate resolved: 2 — all SL_HIT
H1-vetoed pending:  3 — resolve ~2026-05-14T16:00Z

### Verdict (current evidence)
H1_trend_neutral veto is protective on available sample.
Do NOT lower H1 override threshold.
Do NOT remove H1 veto.
Next: rerun tracker after May 14 16:00 UTC to resolve 3 pending rows.
Command: python3 tools/rejected_shadow_tracker.py --score-min 65 --lookback-hours 720 --outcome-hours 24

---
## 2026-05-15 — Final H1 Pending Resolution: 8/8 H1 SL_HIT

Final pending H1 rows resolved.

Command run:
python3 tools/rejected_shadow_tracker.py --score-min 65 --lookback-hours 720 --outcome-hours 24

Tracker output:
- 2026-05-13 15:49 UTC GBPUSD BUY score=71.0 -> SL_HIT -19.9p
- 2026-05-13 16:00 UTC GBPUSD BUY score=68.0 -> SL_HIT -19.9p
- 2026-05-13 16:16 UTC GBPUSD BUY score=66.0 -> SL_HIT -19.6p

After cleanup:
- JSONL before: 13 rows
- JSONL after: 10 rows
- Removed: 3 duplicate rows
- Final clean outcomes: 10 SL_HIT, 0 TP_HIT, 0 pending

Joined result:
- H1_trend_neutral: 8 resolved, 8 SL_HIT, 0 TP_HIT, WR=0.0%
- score_gate: 2 resolved, 2 SL_HIT, 0 TP_HIT, WR=0.0%

Conclusion:
Current tested sample strongly supports H1_trend_neutral as protective.
Do NOT lower H1 override threshold.
Do NOT remove H1 veto.
Do NOT increase strategy aggressiveness based only on signal drought frustration.

Important distinction:
This does not prove H1 is always correct forever. It proves that, in the current replay sample, H1 prevented losing trades.

---
## 2026-05-19 — PR #4 Merged: Clock Drift Observability

Files added: tools/clock_drift_check.py, tools/clock_drift_check.sh, docs/CLOCK_DRIFT_OBSERVABILITY.md
Reports: local_utc, server_utc, drift_seconds, local_clock_unsafe, status (OK/DRIFT_WARN/SERVER_CLOCK_UNAVAILABLE)
Cron: hourly at :55 → logs/cron.clock_drift.log
market_open.sh logic: UNCHANGED (server clock already active from v2.0.3)
Strategy: UNCHANGED

Known gap closed: operator now sees clock drift explicitly instead of inferring from negative cache ages.
Remaining gap: market_open.sh does not write clock_drift_status.json automatically (blocked by PR safety layer).
Next: Telegram proof-of-work daily summary at 20:00 UTC.

---
## 2026-05-19 — Correction: PR #4 Actual Local Deployment

Previous commit 2c9d8f3 described PR #4 as deployed before the files and cron were actually present on Termux.

Actual status now:
- PR branch merged locally into main: YES
- Files present on Termux: tools/clock_drift_check.py, tools/clock_drift_check.sh, docs/CLOCK_DRIFT_OBSERVABILITY.md
- Syntax checks: PASS
- Live run: PASS
- Live status: DRIFT_WARN
- Confirmed drift: approximately -7568s, phone UTC behind server UTC
- Server clock status: OK
- Cron: hourly :55 clock drift observability added
- Trading strategy: UNCHANGED
- H1 logic: UNCHANGED
- Score thresholds: UNCHANGED
- Telegram alert logic: UNCHANGED
- Production observability: CHANGED
- Production trading behavior: UNCHANGED

Important correction:
PR #4 was not actually deployed when 2c9d8f3 was written. This entry corrects that record.

---
## 2026-05-19 — Telegram Daily Proof-of-Work Summary

Implemented and live-tested `tools/daily_summary.sh` replacement.

Proof:
- Syntax test: PASS
- Dry run with DAILY_SUMMARY_SEND=0: PASS
- Real Telegram send with DAILY_SUMMARY_SEND=1: PASS
- Telegram response: TELEGRAM_SEND=PASS http=200
- Message delivered to TomaiSignalAI

Current summary reports:
- Cron status
- Market gate status and reason
- Scans logged
- Candidates found
- Accepted signals
- Rejected candidates
- Reject mix: H1 / score gate / macro6 / no-trade
- Best candidate and rejection reason
- Latest row
- API usage
- Clock drift status
- Strategy/H1/threshold safety line

Observed proof on 2026-05-19:
- Best candidate: EURUSD SELL score=70.70
- Rejection: macro6=3 / H1_trend_neutral
- API usage: 280/800
- Clock drift: DRIFT_WARN, approx -7566s
- Accepted signals: 0
- Strategy: UNCHANGED
- H1 logic: UNCHANGED
- Thresholds: UNCHANGED
- Production trading behavior: UNCHANGED

Known cosmetic issue:
- `market_skip_tail` is rough tail evidence, not a clean daily count. Acceptable for this version; refine later.

---
## 2026-05-19 — Server-UTC Daily Summary Gate Added

Reason:
Ship/local phone time is unsafe. Current confirmed clock drift is around -7566s/-7567s, and tonight the ship time moves 1 hour back again. Therefore a normal cron line such as `0 20 * * *` would mean device-local time, not guaranteed real UTC.

Change:
Added `tools/daily_summary_server_gate.sh`.

Behavior:
- Runs from cron hourly.
- Calls `tools/clock_drift_check.py --json --write-state`.
- Uses server UTC, not phone/local UTC.
- Sends `tools/daily_summary.sh` only when server UTC hour equals target hour.
- Default target: 20 UTC.
- Sends once per server date using `state/daily_summary_sent_YYYY-MM-DD.ok`.
- Logs to `logs/daily_summary_gate.log` and `logs/cron.daily.log`.

Proof:
- Bash syntax: PASS.
- Dry-run gate: PASS.
- Current dry-run result: OUTSIDE_WINDOW.
- Observed server UTC: 2026-05-19T11:58:44Z.
- Observed server hour: 11.
- Target hour: 20.
- Telegram send during dry run: NO.
- Cron changed from direct daily summary to hourly server-UTC gate:
  `10 * * * * bash /data/data/com.termux/files/home/BotA/tools/daily_summary_server_gate.sh >> /data/data/com.termux/files/home/BotA/logs/cron.daily.log 2>&1`

Safety:
- Strategy: UNCHANGED.
- H1 logic: UNCHANGED.
- Score thresholds: UNCHANGED.
- Production trading behavior: UNCHANGED.
- Telegram alert logic: UNCHANGED, except daily proof-of-work summary scheduling path.
- Cron: CHANGED for daily summary only.

---
## 2026-05-19 — Full Session Handoff

### What was built today
1. PR #4 clock drift observability (0b1b211)
   - tools/clock_drift_check.py + tools/clock_drift_check.sh
   - Cron: hourly :55 → logs/cron.clock_drift.log
   - Live result: DRIFT_WARN drift=-7568s server_clock_ok=YES

2. Telegram Daily Proof-of-Work Summary (397dbfb)
   - tools/daily_summary.sh
   - Replaces panic API warnings with structured daily report
   - Test send: PASS http=200

3. Server-UTC Daily Gate (8f75d9c)
   - tools/daily_summary_server_gate.sh
   - Fires hourly at :10, sends only when server_hour==20
   - Reason: ship clock drift (-7568s) + tonight 1hr clock rollback
   - Dry-run: PASS OUTSIDE_WINDOW
   - First real fire expected ~20:16 UTC tonight

### Bot trading state at session close
- Infrastructure: RUNNING
- Last candidate: EURUSD SELL score=66.60 May 18 16:45 UTC → H1-vetoed (correct)
- Best candidate today: EURUSD SELL score=70.70 → H1_trend_neutral + macro6=3
- Accepted signals: 0 (H1 protective per shadow replay evidence)
- Clock drift: -7568s (v2.0.3 handles candle/gate via server clock)
- API credits: 280/800 on session check
- Strategy/H1/thresholds: UNCHANGED throughout

### Known issues carried forward
- Untracked files (leave alone): audits/, state/*.json, state/*.txt
- Premature docs commit 2c9d8f3 corrected in a06a53c
- Future PR merges: use --squash not --no-ff (avoid merge commit warning)
- market_open.sh does not auto-write clock_drift_status.json (blocked in PR safety layer)

### Next session items
1. Verify daily summary fired tonight at ~20:16 UTC (check logs/daily_summary_gate.log)
2. Review daily_summary.sh content after first real run
3. API warning cleanup — reduce/remove daily 600/800 panic messages from Telegram
4. Continue accumulating shadow tracker data (H1 veto outcome proof)

---
## 2026-05-20 — Daily Summary First Unattended Fire: PASS

First real unattended server-UTC gate fire confirmed.

Proof:
  GATE_SEND_START server_date=2026-05-19 server_utc=2026-05-19T20:16:09Z drift=-7568
  [daily] TELEGRAM_SEND=PASS http=200
  GATE_SEND_DONE status=PASS server_date=2026-05-19
  state/daily_summary_sent_2026-05-19.ok EXISTS

Daily summary content (2026-05-19):
  Scans: 28 | Candidates: 23 | HOLD/no-trade: 5
  Accepted signals: 1 | Rejected: 22
  Best candidate: EURUSD SELL score=70.70 → H1_trend_neutral + macro6=3
  API usage: 526/800 warned=false
  Clock drift: DRIFT_WARN drift=-7568s
  Strategy/H1/thresholds: UNCHANGED

Known issue:
  Later dry run returned SERVER_CLOCK_UNAVAILABLE — ship internet intermittent.
  Did NOT block the 20:16 UTC send. Fail-closed behavior correct.
  If SERVER_CLOCK_UNAVAILABLE hits during the 20 UTC window repeatedly,
  consider cached-offset fallback (separate branch, not urgent).

Phase status: COMPLETE. No further code changes needed.

---
## 2026-05-20 — Daily Summary Accepted Count Verified

Investigation of "Accepted signals: 1" in May 19 summary.

Finding: CORRECT. Not a bug.
Row: line=1178, 2026-05-19T21:30:28+1000 = 11:30:28 UTC
  EURUSD M15 SELL score=67.1 filter_rejected=false filters=macro6=3 | H1_trend_confirmed

Explanation:
  H1 was confirmed SELL direction (not neutral). Signal passed the production filter.
  Score 67.1 is above FILTER_SCORE_MIN=65 but below TELEGRAM_MIN_SCORE=70.
  Correctly logged to alerts.csv as accepted, correctly NOT sent to Telegram.
  Daily summary counts filter-accepted rows, not Telegram-sent rows.

Known cosmetic gap (low priority):
  Summary does not distinguish "accepted + Telegram sent" vs "accepted + below Telegram threshold".
  Not a bug. Acceptable for current version. Refine in a future PR if needed.

No code changes made.

---
## 2026-05-20 — Daily Summary Wording Clarified

Change:
- Reworded daily proof-of-work summary so CSV `rejected=false` rows are shown as filter-accepted candidates, not final accepted signals.
- Added Telegram-threshold eligible count using TELEGRAM_MIN_SCORE.
- Renamed accepted_lines log evidence to watcher_accepted_log_lines.

Reason:
The May 19 summary showed `Accepted signals: 1`, but audit proved the row was filter-accepted with score=67.10 while TELEGRAM_MIN_SCORE=70. Therefore it was not Telegram-send eligible.

Safety:
- Strategy: UNCHANGED.
- H1 logic: UNCHANGED.
- Threshold values: UNCHANGED.
- Production trading behavior: UNCHANGED.
- Cron: UNCHANGED.
- Telegram sending logic: UNCHANGED.

---
## 2026-05-20 — Daily Summary Wording Clarified

Change:
- Reworded daily proof-of-work summary so CSV `rejected=false` rows are shown as filter-accepted candidates, not final accepted signals.
- Added Telegram-threshold eligible count using TELEGRAM_MIN_SCORE.
- Renamed accepted_lines log evidence to watcher_accepted_log_lines.

Reason:
The May 19 summary showed `Accepted signals: 1`, but audit proved the row was filter-accepted with score=67.10 while TELEGRAM_MIN_SCORE=70. Therefore it was not Telegram-send eligible.

Safety:
- Strategy: UNCHANGED.
- H1 logic: UNCHANGED.
- Threshold values: UNCHANGED.
- Production trading behavior: UNCHANGED.
- Cron: UNCHANGED.
- Telegram sending logic: UNCHANGED.

---
## 2026-05-21 — May 20 Daily Summary Missed: CLOCK_FAIL During 20 UTC Window

May 19 summary: PASS (sent at 20:16 UTC)
May 20 summary: MISSED — server clock unavailable from ~17:15 UTC through end of day
May 21 summary: pending (~17:10 AEST / 20:10 server UTC tonight)

Root cause: ship internet blocked all server clock endpoints during the entire
20 UTC window on May 20. Fail-closed behavior is correct for trading gate,
but causes daily summary to miss when clock fails at exactly the send hour.

Pattern: now missed twice during 20 UTC window due to CLOCK_FAIL.
Threshold reached for building cached-offset fallback (daily summary only).

Proposed fix (next branch — do not build on ship):
  daily_summary_server_gate.sh: if server clock fails, use last-known-good
  offset from clock_drift_status.json (if written within last 4 hours) to
  estimate server UTC. Trading market_open.sh remains fail-closed unchanged.

Tonight: if May 21 summary fires → CLOCK_FAIL was temporary.
          if May 21 also misses → cached-offset fallback is urgent.

---
## 2026-05-21 — May 20 Daily Summary Missed: CLOCK_FAIL During 20 UTC Window

Status:
- May 19 daily summary: PASS, sent at server UTC 20:16.
- May 20 daily summary: MISSED.
- May 21 daily summary: pending.

Proof:
- No state/daily_summary_sent_2026-05-20.ok file exists.
- Gate log shows repeated CLOCK_FAIL / SERVER_CLOCK_UNAVAILABLE during the May 20 target window.
- This prevented the server-UTC gate from confirming server_hour=20, so the gate correctly failed closed.

Root cause:
Ship internet/server-clock endpoints were unavailable during the May 20 daily-summary send window.

Safety:
- Trading strategy: UNCHANGED.
- H1 logic: UNCHANGED.
- Thresholds: UNCHANGED.
- Cron: UNCHANGED.
- Telegram sending logic: UNCHANGED.
- Production trading behavior: UNCHANGED.

Next observation:
Check the May 21 daily summary after the next server UTC 20 window. Based on current drift, expected local-device check time is around 03:10 AEST on May 22, but ship/device time may move again.

Decision rule:
- If May 21 sends successfully, no urgent fix.
- If May 21 also misses due to CLOCK_FAIL, build a daily-summary-only cached server-offset fallback.
- Do not apply cached offset fallback to trading/market gates; those remain fail-closed.

---
## 2026-05-22 — Clock Drift Last-Good State Added

Change:
- Updated tools/clock_drift_check.py to write logs/clock_drift_last_good.json only when server_clock_ok=true.
- Failed clock checks continue writing logs/clock_drift_status.json, but they do not overwrite the last-good server clock file.
- This prepares for a future daily-summary-only cached-offset fallback.

Proof:
- python3 -m py_compile tools/clock_drift_check.py passed.
- Live check wrote logs/clock_drift_last_good.json.
- Last-good payload included server_utc, drift_seconds, generated_utc, local_utc, and server source metadata.

Safety:
- Trading strategy: UNCHANGED.
- H1 logic: UNCHANGED.
- Thresholds: UNCHANGED.
- Cron: UNCHANGED.
- Telegram sending logic: UNCHANGED.
- Daily summary gate behavior: UNCHANGED.
- Production trading behavior: UNCHANGED.

Next:
- Update tools/daily_summary_server_gate.sh so only the daily proof-of-work summary can use last-good server offset when live server clock is unavailable.
- Do not apply this fallback to trading or market gates.

---
## 2026-05-22 — H1 Veto Final Proof: SELL Direction Confirmed Protective

Shadow replay expanded to include SELL-direction H1-vetoed candidates.

SELL results: resolved=7, TP=0, SL=7, WR=0.0%
  May 18 EURUSD SELL 66.6 → SL_HIT -12.1p
  May 19 GBPUSD SELL 68.4 → SL_HIT -15.3p
  May 19 EURUSD SELL 70.7 → SL_HIT -11.8p  (would have been Telegram signal)
  May 21 EURUSD SELL 72.4 → SL_HIT -15.7p  (would have been Telegram signal)
  May 21 EURUSD SELL 72.5 → SL_HIT -16.2p  (would have been Telegram signal)
  May 21 EURUSD SELL 73.2 → SL_HIT -16.4p  (would have been Telegram signal)
  May 22 GBPUSD SELL 68.7 → SL_HIT -11.5p

Combined ALL directions: 20 resolved, 20 SL_HIT, 0 TP_HIT, WR=0.0%
BUY results: resolved=13, all SL_HIT (prior sessions)

CONCLUSION:
  H1 neutral veto is protective in BOTH BUY and SELL directions.
  Directional bias concern eliminated.
  Do NOT lower H1_VETO_OVERRIDE_SCORE.
  Do NOT remove or weaken H1 veto.
  Silence is correct behavior in ranging H1 market conditions.

ROOT CAUSE OF SIGNAL SCARCITY:
  Strategy requires trending H1 conditions to produce clean signals.
  EUR/USD and GBP/USD H1 has been ranging since mid-May.
  When H1 trends, the strategy fires (May 12 BUY 75.70 worked).
  The fix is not threshold changes — it is market exposure.

NEXT QUESTION:
  Should USDJPY or additional pairs be added to increase probability
  of at least one pair being in H1 trend at any given time?
  This requires a separate analysis — not a threshold change.

---

## Pre-Commercial Checkpoint — 2026-05-22

Read-only audit. No production files modified.
Full report: `audits/bota_pre_commercial_checkpoint_2026-05-22.md`

### State

- Signal pipeline: ACTIVE.
- Active signal scan: EURUSD + GBPUSD on M15.
- USDJPY: indicators fetched/cached by indicators_updater.sh, but not confirmed in active signal scan cron.
- Thresholds unchanged:
  - FILTER_SCORE_MIN=65
  - TELEGRAM_MIN_SCORE / YELLOW tier=70
  - TELEGRAM_TIER_GREEN_MIN=75
  - H1_VETO_OVERRIDE_SCORE=75
  - TELEGRAM_COOLDOWN_SECONDS=1800
  - SCALP_SL_ATR_MULT=2.0
  - SCALP_TP_ATR_MULT=4.0
  - FILTER_RR_MIN=1.4
- H1 veto: hard in tools/m15_h1_fusion.sh; proven protective by shadow replay (20/20 SL_HIT, 0 TP_HIT both BUY and SELL directions, commit 20e23a5).
- Telegram: ACTIVE. YELLOW watchlist tier >=70, GREEN full-alert tier >=75.
- Supabase/ProfitLab: code path wired through tools/supabase_publish.py and signal_watcher_pro.sh; local key presence observed; production insert success not confirmed in this audit window.
- Daily summary: May 19 PASS; May 20 and May 21 missed due to CLOCK_FAIL during target window; May 22 pending at audit time (target: 20 UTC).
- Last-good server clock fallback: deployed and operational (commit 26e333d); affects daily summary only, not trading gates.
- Clock drift observability active; device clock ~4.1h ahead but server clock currently recoverable (DRIFT_WARN, server_clock_ok=true).

### Risks Logged

- Supabase production insert success remains unproven in current logs.
- state/bota_shipmode_crontab.txt is stale; live crontab (crontab -l) is the authoritative source.
- Daily summary can still miss if server clock unavailable for more than 8 hours through the target window.
- H1_VETO_OVERRIDE_SCORE duplicate line in strategy.env (lines 25-26); both values are 75, no functional impact.
- No product/commercial message layer exists yet.

### Next Planned Branch

  feat/signal-product-message-v1

Do not start that branch until this checkpoint commit is reviewed.

---

## 2026-05-23 — Product Message Layer V1: Shadow Market Pulse Formatter Added

Branch: `feat/signal-product-message-v1`  
Commit: `c9bcee4` — `feat: add product message v1 shadow market pulse formatter`

### What Changed

Added new file:

- `tools/product_message_v1.py`

Purpose:

- Generate a shadow-only BotA Market Pulse message.
- Read existing cache files only.
- Write preview output to stdout.
- Write shadow audit record to `logs/product_messages_v1.jsonl`.

### Confirmed Safety Contract

- Telegram send: NO.
- Supabase publish: NO.
- Cron change: NO.
- Trading thresholds changed: NO.
- H1 veto changed: NO.
- Signal generation logic changed: NO.
- Active scan scope remains: EURUSD + GBPUSD only.
- USDJPY remains fetched/cached only, not part of active signal scan.
- Market Pulse output does not include executable trade instructions.

### Data Sources Used

The formatter reads:

- `cache/indicators_EURUSD_M15.json`
- `cache/indicators_EURUSD_H1.json`
- `cache/indicators_EURUSD_H4.json`
- `cache/d1_trend_EURUSD.json`
- `cache/indicators_GBPUSD_M15.json`
- `cache/indicators_GBPUSD_H1.json`
- `cache/indicators_GBPUSD_H4.json`
- `cache/d1_trend_GBPUSD.json`

The formatter intentionally ignores broken D1 indicator files:

- `cache/indicators_EURUSD_D1.json`
- `cache/indicators_GBPUSD_D1.json`

Reason: both showed `tf_ok=false`, `weak=true`, and `error=tf_mismatch`.

### Validation Results

Commands run:

- `python3 -m py_compile tools/product_message_v1.py`
- `python3 tools/product_message_v1.py --type market_pulse --shadow`
- `git status --short`

Results:

- Syntax check: PASS.
- Shadow output generated successfully.
- `telegram_sent=false`.
- `supabase_published=false`.
- Shadow JSONL log created and confirmed non-empty.
- `logs/product_messages_v1.jsonl` is ignored by Git through `.gitignore`.
- No tracked production files modified after commit.

### Runtime Observation

During the first shadow run:

- Market phase was closed.
- M15/H1/H4 cache ages were stale, expected for Saturday market closure.
- EURUSD H4 rendered as unavailable because cache had:
  - `tf_ok=true`
  - `weak=true`
  - `error=insufficient_data`

This is not a formatter bug. The formatter handled weak cache data safely.

### Next Required Step

Before any public Watchlist message is enabled:

- Fix the YELLOW/Supabase product-contract issue.
- YELLOW watchlist-style Telegram messages must not be inserted into ProfitLab as ACTIVE executable signals.
- Public Telegram / Supabase / cron activation remains blocked until that contract is fixed and verified.

---

## 2026-05-23 — Step 3.5: YELLOW/Supabase Contract Fix

Branch: `feat/signal-product-message-v1`

Code commit:
- `df53cbf` — `fix: prevent YELLOW watchlist tier from publishing active Supabase signals`

### Problem Fixed

YELLOW Telegram alerts were watchlist-style messages, but the successful Telegram path still called `tools/supabase_publish.py`.

That allowed a YELLOW/watchlist message to be inserted into Supabase `public.signals` as:

- `status='ACTIVE'`
- executable `entry_price`
- executable `stop_loss`
- executable `take_profit`

This was a product-contract bug because ProfitLab treats `public.signals.status='ACTIVE'` as an executable signal.

### Files Changed

Modified only:

- `tools/signal_watcher_pro.sh`
- `tools/supabase_publish.py`

No changes made to:

- `tools/m15_h1_fusion.sh`
- `tools/scoring_engine.sh`
- `tools/product_message_v1.py`
- `config/strategy.env`
- cron
- thresholds
- H1 veto logic
- Supabase schema
- ProfitLab frontend

### Fix Implemented

`tools/signal_watcher_pro.sh`:

- GREEN tier continues to publish to Supabase after successful Telegram send.
- YELLOW tier still sends Telegram.
- YELLOW tier now skips Supabase publishing.
- Added clear Supabase skip log for non-GREEN tiers.

`tools/supabase_publish.py`:

- Added defensive tier guard at the top of `publish()`.
- Non-GREEN tiers return success with a skip message.
- Non-GREEN tiers no longer require `SUPABASE_SERVICE_KEY`.
- Only GREEN can proceed toward ACTIVE Supabase insertion.
- `min_tier` is now constant `pro` for published ACTIVE signals.

### Validation Results

Passed:

- `git diff --check`
- `python3 -m py_compile tools/supabase_publish.py`
- `bash -n tools/signal_watcher_pro.sh`

Defensive behavior confirmed:

- `YELLOW_EXIT:0`
  - Printed skip message.
  - Did not require Supabase key.
  - Did not attempt ACTIVE publish.

- `GREEN_NO_KEY_EXIT:1`
  - Still failed when `SUPABASE_SERVICE_KEY` was missing.
  - Preserved existing GREEN publish safety behavior.

### Final Contract After Step 3.5

GREEN:

- Telegram: sends.
- Chart: GREEN-only behavior preserved.
- Supabase: publishes ACTIVE executable signal.

YELLOW:

- Telegram: sends.
- Supabase: skipped.
- ProfitLab ACTIVE signal: not created.

### Remaining Gate

Public Watchlist activation remains blocked until a separate product decision is made about whether watchlist items need:

- their own Supabase table,
- a schema migration adding `WATCHLIST`,
- or Telegram-only behavior.

---

## 2026-05-27 — Step 5: Private Telegram Market Pulse Send Confirmed

Branch: `main`
Commit: `274b0d3`
Tag: `step-5-private-send-confirmed-2026-05-27`
Commit message: `feat: Step 5 — add --send mode with explicit --chat-id gate, fix macro6=3 neutral blocker`

### What Changed

`tools/product_message_v1.py` updated:

- Added `--send` mode as a mutually exclusive alternative to `--shadow`. One of the two is required.
- `--send` requires `--chat-id` to be passed explicitly on the command line. Fails loudly if missing.
- Token read from `TELEGRAM_BOT_TOKEN` only. Fails loudly if missing.
- Telegram send uses `urllib` stdlib only. No new dependencies.
- Success requires HTTP 200 and `ok=true` from Telegram JSON response.
- Shadow log records `mode=shadow|send`, `telegram_sent=true` only after confirmed send, `supabase_published=false` always.
- Fixed macro6=3 neutral/default bug: when `macro6=3`, no "macro filter active" blocker is displayed. Only actual non-neutral opposing macro conditions trigger macro blocker language.

### Fixed

- `macro6=3` is the neutral/default value and must not display as "macro filter active". Fixed.
- `--shadow` and `--send` are now mutually exclusive. Both modes explicit, no silent defaults.
- `TELEGRAM_CHAT_ID` env var is never used automatically for Step 5. Chat ID must always be passed via `--chat-id`.

### Proven Working

- Shadow mode: `telegram_sent=False`, `supabase_published=False`. Unchanged.
- Send mode manual test:
  - `[send] telegram_sent      : True`
  - `[send] supabase_published : False`
- Telegram message delivered to private test chat.
- Market Pulse contains no entry, SL, or TP.
- Market Pulse disclaimer present: "not a trade alert".

### Safety State

- Production trading behavior changed: NO.
- Strategy changed: NO.
- H1 logic changed: NO.
- Thresholds changed: NO.
- Cron changed: NO.
- Supabase publish changed for Market Pulse: NO — remains false.
- ProfitLab executable signal publish behavior: UNCHANGED.

### Blocking Issues / Open Decisions

- Step 6 scheduled daily pulse: NEXT but NOT approved yet.
- Step 6 target chat decision still open: private test chat for one week vs main BotA channel.
- Main BotA channel rollout requires separate explicit approval.
- Cron scheduling requires separate explicit approval.

### Next Step

- Decide Step 6 target chat (private test vs main channel).
- Get explicit approval before adding cron or widening send scope.

---

## 2026-05-27 — Step 6: Daily Pulse Wrapper + First Private Live Send + Layout Cleanup

### Step 6 Implementation

Branch: `main`
Commit: `6aa985e`
Tag: `step-6-wrapper-gates-2026-05-27`

Added `tools/run_daily_pulse.sh`:

- Reads `config/pulse.env` for `PULSE_TEST_CHAT_ID`.
- Dedup gate: writes `state/daily_pulse_sent_YYYY-MM-DD.ok` on first send; skips if file already exists.
- `--dry-run` flag supported: prints gate decision, no Telegram send.
- Sources `TELEGRAM_BOT_TOKEN` from `.env`.
- Calls `product_message_v1.py --type market_pulse --send --chat-id`.
- Cron: NOT active. Manual execution only at this stage.
- `config/pulse.env` is local-only and not committed.

### Step 6A: First Private Live Send Passed

- `LIVE_SEND_EXIT_CODE=0`
- `telegram_sent=True`
- `supabase_published=False`
- Private test chat received the Market Pulse message.
- Dedup file created correctly: `state/daily_pulse_sent_2026-05-27.ok`

### Step 6A: Layout Cleanup

Commit: `65d1137`
Commit message: `style: simplify Market Pulse mobile layout`

Changed only `tools/product_message_v1.py` — `format_market_pulse`:

- Heavy `━━━` separator bars removed.
- New mobile-friendly layout per pair:
  ```
  EUR/USD · 1.16384 · 📉 Bearish
  🟡 Watching — bearish bias present
  ```
- Footer simplified to two lines:
  ```
  Pulse only · No trade levels
  🔴 Trade Alerts are sent separately
  ```
- `py_compile`: PASS. `bash -n run_daily_pulse.sh`: PASS.
- `--dry-run` skipped correctly (dedup file present).

### Proven Working

- Wrapper send: `LIVE_SEND_EXIT_CODE=0`, `telegram_sent=True`, `supabase_published=False`.
- Dedup prevents duplicate sends within same UTC day.
- `--dry-run` mode works: prints gate result, no send.
- Market Pulse contains no entry, SL, or TP.
- Disclaimer present: "Pulse only · No trade levels" + "🔴 Trade Alerts are sent separately".
- Layout confirmed readable on Telegram mobile.

### Safety State

- Production trading behavior changed: NO.
- Strategy changed: NO.
- H1 logic changed: NO.
- Thresholds changed: NO.
- Cron changed: NO — cron NOT active.
- Supabase publish: NO — remains false for all Market Pulse sends.
- ProfitLab executable signal behavior: UNCHANGED.
- Main BotA channel: NOT approved.

### Remaining Gates Before Wider Rollout

- 3 successful private scheduled/manual daily sends required before cron or main channel approval.
- Main BotA channel rollout requires separate explicit approval.
- Cron scheduling requires separate explicit approval after private proof.

### Next Step

- Run `bash tools/run_daily_pulse.sh` manually each day (or wait for cron approval).
- After 3 confirmed private sends, bring proof and request cron/main channel decision.
