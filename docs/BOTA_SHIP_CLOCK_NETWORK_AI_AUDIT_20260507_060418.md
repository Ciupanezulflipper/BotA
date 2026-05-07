# BotA Ship-Mode Clock / Network / Cache Audit Handoff

## Project
- Path: `/data/data/com.termux/files/home/BotA`
- Environment: Termux on Android, cruise ship network, manually shifted device time.
- Trading bot: BotA, Forex, M15 focus for EURUSD/GBPUSD, with USDJPY also used in cache/updater.

## User workflow rules
- No partial code patches.
- No inline edits.
- Full-file replacement only when code replacement is required.
- For Termux commands: show `FILES_REPLACED=YES/NO`, `PRODUCTION_CHANGED=YES/NO`, `STRATEGY_CHANGED=NO`.
- Step-by-step with verification after each step.

## Grounded facts already proven
1. Original blocker was local phone clock drift.
   - Local Android UTC was around +7117 seconds ahead of trusted server UTC.
   - `signal_watcher_pro.sh` previously used `datetime.now(timezone.utc)` inside `candle_age_info()`.
   - That falsely classified fresh M15 candles as stale.

2. Watcher server-clock patch is now present.
   - Markers found:
     - `v2.0.3 ship-mode server clock`
     - `compute_server_clock_epoch`
     - `BOTA_SERVER_EPOCH`
   - `bash -n tools/signal_watcher_pro.sh` passes.
   - Strategy thresholds were not changed.

3. Current watcher behavior after patch:
   - It can log `CLOCK server_clock_ok BOTA_SERVER_EPOCH=...`.
   - But it still skips if raw cache is genuinely stale.
   - Example stale cache:
     - `last_cache_candle_utc=2026-05-05T18:30:00Z`
     - stale far beyond `CANDLE_MAX_AGE_SECS=2700`.

4. Network audit nuance:
   - DNS is not simply dead.
   - Curl resolved:
     - `www.google.com`
     - `www.cloudflare.com`
     - `api-fxpractice.oanda.com`
     - `query1.finance.yahoo.com`
   - TLS handshakes completed.
   - Python socket DNS resolved hosts.
   - Python urllib got HTTP 200 and Date from Google.
   - Cloudflare and OANDA root endpoints returned HTTP 403.
   - Yahoo returned HTTP 429.
   - `curl_exit_code=23` is likely caused by piping verbose curl output into `head`, not by network failure.

5. Runtime issue:
   - Audit printed `NO_RELEVANT_PROCESSES_FOUND`.
   - This means `crond` was not running.
   - Therefore cron-based indicators updater was not actively refreshing cache.

## Most likely current root cause
The current blocker is not scoring. It is not the original phone-clock bug. It is runtime/cache refresh:

1. `crond` not running.
2. Scheduled updater not active.
3. Raw M15 cache stuck at old timestamp.
4. Watcher correctly refuses to score stale data.

## Questions for another AI
Please audit and answer:

1. Is the next safest step to restart `crond`, run `tools/indicators_updater.sh` manually, then verify M15 cache freshness?
2. Should `tools/market_open.sh` also be patched to use server UTC instead of Android local time, given ship time shifts?
3. Should `compute_server_clock_epoch()` in `signal_watcher_pro.sh` be hardened to:
   - use Python urllib instead of curl;
   - extract Date headers even from HTTPError 403/429;
   - use endpoints more likely to return Date reliably?
4. Are there any code paths still using local time for blocking trading decisions?
5. Confirm that no scoring/strategy changes are needed until cache freshness and runtime are stable.

## Acceptance criteria for next technical step
- `pgrep -af crond` shows one crond process.
- Manual updater exits 0.
- M15 cache last candle advances from `2026-05-05T18:30:00Z`.
- Watcher dry run reaches `FILTER` or downstream scoring lines instead of `STALE`.
- If server clock fails but Python can read Google Date, patch only the server-clock helper.
