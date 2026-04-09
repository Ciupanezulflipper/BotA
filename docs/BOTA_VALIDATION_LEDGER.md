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
- `crond` was manually started and remained running
- `logs/cron.signals.log` updated at 2026-04-09 12:15
- `logs/cron.indicators.log` updated at 2026-04-09 12:14
- `logs/cron.shadow.log` exists and updated at 2026-04-09 12:15
- `logs/shadow_manager_heartbeat.txt` advanced to `2026-04-09T09:15:04... | OK | 0 active signals`

Conclusion:
- BotA cron runtime is alive and executing on schedule

Repeat this check again only if:
- cron logs stop advancing
- `pgrep -af crond` shows no process
- heartbeat goes stale again

---

## VALIDATION-002 — Boot persistence
Status: PROVEN

Evidence:
- Real device reboot performed
- After reboot:
  - `logs/cron.indicators.log` advanced
  - `logs/cron.signals.log` advanced
  - `logs/cron.shadow.log` appeared and advanced
  - `logs/shadow_manager_heartbeat.txt` advanced

Conclusion:
- Termux:Boot + `start-crond.sh` + cron persistence are working

Repeat this check again only if:
- reboot behavior changes
- boot scripts are edited
- Android battery/background settings are changed

---

## VALIDATION-003 — Shadow manager startup
Status: PROVEN

Evidence:
- `tools/run_shadow_manager.sh` created and used
- manual wrapper smoke test passed
- `logs/shadow_manager.log` shows:
  - `Schema compatibility: PASS`
  - `OANDA_MODE=PRACTICE`
  - normal completion
- `logs/cron.shadow.log` now updates on schedule

Conclusion:
- Shadow manager startup/bootstrap path is working

Repeat this check again only if:
- wrapper file changes
- env bootstrap changes
- shadow manager stops logging

---

## VALIDATION-004 — Unique-contract hardening
Status: INSTALLED_NOT_FULLY_EXERCISED

Evidence:
- `tools/be_shadow_manager.py` contains:
  - `UNIQ_CONFLICT_ERR`
  - `UNIQUE CONTRACT ERROR`
- file compiles successfully
- wrapper smoke test passed

Not yet proven:
- real live insert path hitting `ensure_shadow_row()` under active-signal conditions
- behavior when DB uniqueness contract is actually missing

Conclusion:
- protection is installed, but not fully exercised with live active signals

Next proof step:
- wait for active production signals
- inspect `ensure_shadow_row()` execution path in logs

---

## VALIDATION-005 — Runtime silence since Apr 6
Status: PARTIALLY_EXPLAINED

Evidence:
- cron had been down earlier at one checkpoint
- runtime is now restored
- scorer outputs for EURUSD/GBPUSD still return `HOLD` + `no_signal|phase=Open`

Conclusion:
- silence is not explained anymore by boot persistence or dead cron
- remaining cause is in decision data / signal logic

Repeat this check again only after:
- D1 cache refresh bug is addressed

---

## VALIDATION-006 — Direct scorer output for live watched pairs
Status: PROVEN

Evidence:
- `bash tools/scoring_engine.sh EURUSD M15` ->
  - `direction=HOLD`
  - `reasons=no_signal|phase=Open`
- `bash tools/scoring_engine.sh GBPUSD M15` ->
  - `direction=HOLD`
  - `reasons=no_signal|phase=Open`

Indicator snapshots at same time were valid:
- nonzero price
- nonzero ATR
- valid EMA/RSI/ADX
- `tf_ok=True`
- `error=` empty

Conclusion:
- watcher is not the owner of the failure
- scorer is intentionally returning HOLD on current live state

Repeat this check again only after:
- D1 cache refresh path is fixed
- or scorer logic is changed

---

## VALIDATION-007 — Pullback gate vs D1 veto
Status: PROVEN

Evidence:
- Manual condition check showed:
  - `pullback_buy=True` for EURUSD
  - `pullback_buy=True` for GBPUSD
- Scorer still returned `HOLD`
- D1 trend cache files contained:
  - `cache/d1_trend_EURUSD.json` -> `trend: SELL`
  - `cache/d1_trend_GBPUSD.json` -> `trend: SELL`
- Both files were stale from Apr 6

Conclusion:
- valid M15 bullish setups are being reset to HOLD by stale D1 trend veto data

Repeat this check again only after:
- D1 trend cache files are refreshed successfully

---

## VALIDATION-008 — D1 trend refresh path
Status: PROVEN_BROKEN_PATH_OWNER_IDENTIFIED

Owner file:
- `tools/indicators_updater.sh`

Evidence:
- `refresh_d1_trend_cache()` located in `tools/indicators_updater.sh`
- updater prints:
  - `D1 EUR_USD error: HTTP Error 400: Bad Request`
  - `D1 GBP_USD error: HTTP Error 400: Bad Request`
- after full updater run:
  - `cache/d1_trend_EURUSD.json` unchanged
  - `cache/d1_trend_GBPUSD.json` unchanged
  - both still stale from Apr 6

Conclusion:
- next technical fix target is `tools/indicators_updater.sh`
- specifically `refresh_d1_trend_cache()`

Next proof/fix step:
- compare behavior of `tools/refresh_d1_cache.sh`
- determine whether:
  - standalone D1 refresh works
  - or request/env/provider logic is wrong in both places

Do NOT repeat:
- cron runtime checks
- boot persistence checks
- generic watcher checks
unless D1 path is first ruled out

---

## VALIDATION-009 — Still unknown
Status: UNKNOWN

Unknowns:
- whether `tools/refresh_d1_cache.sh` succeeds or fails the same way
- whether the 400 comes from wrong instrument format, wrong URL, missing env, or provider behavior
- whether fixing D1 cache alone will restore actual tradeable outputs, or whether ADX < 20 becomes the next blocker

---

## RULES
1. Never mark PROVEN without command/log/file evidence.
2. Never collapse INSTALLED into PROVEN.
3. Every new check must answer:
   - what was tested
   - what was proven
   - what remains unknown
   - when this check should be repeated
4. If a check is already PROVEN and no relevant file changed, do not repeat it.
