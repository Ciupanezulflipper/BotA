# Q5 Production-Pipeline Boundary Audit

- [proven] This report uses only captured Termux evidence.
- [proven] Missing configuration and actual execution are treated separately.
- [proven] Restore window: `2026-07-08T11:41:32Z` to `2026-07-08T11:43:43Z`.

## Source boundaries

### watcher

- [proven] Path: `logs/cron.signals.log`
- [proven] File present: `True`
- [proven] Pre-restore evidence rows: `59`
- [proven] Post-restore evidence rows: `75`

- [proven] Final positive evidence before restore: `2026-06-22T17:16:01Z` line `24233` — `[DEDUP 2026-06-22T21:16:01+0400] GBPUSD M15 signal unchanged -> skip`
- [proven] First positive evidence after restore: `2026-07-08T11:45:07Z` line `24236` — `[WATCHER 2026-07-08T13:45:07+0200] SANITY: PAIRS="EURUSD GBPUSD" TIMEFRAMES="M15" ALERTS_CSV="/data/data/com.termux/files/home/BotA/logs/alerts.csv" DRY_RUN_MODE="0" TELEGRAM_ENABLED="1" TELEGRAM_MIN_SCORE="70" FILTER_SCORE_MIN="65" FILTER_SCORE_MIN_ALL="65" MAPPED_FILTER_SCORE_MIN_ALL="0" TELEGRAM_TIER_YELLOW_MIN="70" TELEGRAM_TIER_GREEN_MIN="75" TELEGRAM_TIER_YELLOW_MIN_INT="70" TELEGRAM_TIER_GREEN_MIN_INT="75" CANDLE_MAX_AGE_SECS="2700" INDICATOR_LAG_WARN_SECS="900"`

### alerts

- [proven] Path: `logs/alerts.csv`
- [proven] File present: `True`
- [proven] Pre-restore evidence rows: `16`
- [proven] Post-restore evidence rows: `13`

- [proven] Final positive evidence before restore: `2026-06-22T17:00:33Z` line `1561` — `2026-06-22T21:00:33+0400,EURUSD,M15,HOLD,0.00,40.00,0.00000,0.00000,0.00000,engine_A3,true,direction_not_tradeable | score<65 | entry_invalid_zero | rr<=0 | macro6=3,no_signal|phase=Open,,,,,,,,3,,LOW,NY_close,ranging`
- [proven] First positive evidence after restore: `2026-07-08T11:45:26Z` line `1562` — `2026-07-08T13:45:26+0200,EURUSD,M15,SELL,57.60,57.60,1.14033,1.14181,1.13737,engine_A3,true,score<65 | macro6=3,"ok|ema_bps=2.8|rsi=46.0|macd_hist=-0.000033|adx=33.4|ema_comp=2.8|rsi_comp=2.4|macd_comp=3.3|adx_comp=10.0|bb_comp=-3.0|bb=bb_squeeze|session_comp=2.0|session=session_london|vol_comp=0.0|vol=vol_normal|sr_comp=0.0|sr=sr_neutral|phase=Open|pullback_entry|d1_filter=SELL | sl_tp_rec=SL:1.14181,TP:1.13737,ATRx(2.0/4.0)",2.8,2.4,3.3,10.0,33.4,46.0,-0.000033,3,,LOW,London,trending`

### supervisor

- [proven] Path: `logs/cron.supervisor.log`
- [proven] File present: `True`
- [proven] Pre-restore evidence rows: `3092`
- [proven] Post-restore evidence rows: `511`

- [proven] Final positive evidence before restore: `2026-06-22T17:40:00Z` line `199830` — `[SUPERVISOR 2026-06-22T17:40:00Z] OK: no watcher.lock present`
- [proven] First positive evidence after restore: `2026-07-08T11:45:00Z` line `199840` — `[SUPERVISOR 2026-07-08T11:45:00Z] === SUPERVISOR START ===`

### updater

- [proven] Path: `logs/cron.indicators.log`
- [proven] File present: `True`
- [proven] Pre-restore evidence rows: `0`
- [proven] Post-restore evidence rows: `0`

- [not proven] No positive evidence before restore was located.
- [not proven] No positive evidence after restore was located.

### shadow

- [proven] Path: `logs/cron.shadow.log`
- [proven] File present: `True`
- [proven] Pre-restore evidence rows: `942`
- [proven] Post-restore evidence rows: `205`

- [proven] Final positive evidence before restore: `2026-06-22T21:30:06.874000Z` line `35102` — `2026-06-22 21:30:06,874 | INFO | Active production signals: 1`
- [proven] First positive evidence after restore: `2026-07-08T13:45:02.376000Z` line `35200` — `2026-07-08 13:45:02,376 | INFO | Schema compatibility: PASS (30 required columns verified)`

### heartbeat

- [proven] Path: `logs/cron.heartbeat.log`
- [proven] File present: `True`
- [proven] Pre-restore evidence rows: `66`
- [proven] Post-restore evidence rows: `12`

- [proven] Final positive evidence before restore: `2026-06-22T17:00:00Z` line `1764` — `[2026-06-22 17:00:00 UTC] ❌ tele.env missing`
- [proven] First positive evidence after restore: `2026-07-08T12:00:00Z` line `1765` — `[2026-07-08 12:00:00 UTC] ❌ tele.env missing`

## Configuration evidence

- [proven] Watcher, updater, shadow manager, and supervisor were absent from the preserved `11:37:37Z` and `11:41:32Z` crontab snapshots.
- [proven] Those jobs were present in the preserved `11:43:43Z` snapshot.

## Boundary interpretation

- [proven] Last located positive watcher evidence before recovery: `2026-06-22T17:16:01Z`.
- [proven] First located positive watcher evidence after recovery: `2026-07-08T11:45:07Z`.
- [proven] The interval between the final pre-gap watcher evidence and the first post-recovery watcher evidence is an operational uncertainty interval.
- [inferred] Within that uncertainty interval, the preserved July 8 snapshots prove that the signal-pipeline cron configuration was missing immediately before restoration.
- [not proven] The exact original deletion timestamp is not established solely by these snapshots.
