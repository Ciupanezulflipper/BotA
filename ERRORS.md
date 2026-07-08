# BotA Errors and Silent-Failure Register

Last updated: 2026-07-08

Purpose: record runtime failures that must not be rediscovered from scratch in new chats.

## Error class E-001: Closer lifecycle freeze

Status: fixed structurally, still needs ongoing runtime monitoring.

Verified history:

- Stale ACTIVE Supabase signals blocked new per-pair signals through dedup.
- `tools/run_signal_closer_live.sh` was added.
- `tools/signal_closer.py` was updated to use trusted server clock and OANDA-backed cache.

Required future detection:

- `logs/cron.closer.log` age.
- ACTIVE signal count.
- Oldest ACTIVE signal age.
- Signal transition proof: ACTIVE -> CLOSED/CANCELLED.

Alert rule:

- DEGRADED if closer log stale during market hours.
- DEGRADED if any ACTIVE signal exceeds the approved lifecycle threshold.

## Error class E-002: Runtime crontab wipe

Status: immediate crontab restored by C1C; hardening not complete.

Verified on 2026-07-08:

- Live crontab lost BotA runtime lines.
- Only dividend scanner and BotA Daily Proof remained.
- Watcher, updater, closer, shadow, supervisor, and clock-drift lines were missing.
- `cron.signals.log`, `cron.indicators.log`, `cron.closer.log`, and `api_credits.json` were frozen around 2026-06-22.
- Daily Proof gave false comfort because it reported `Cron: running`, meaning only that `crond` existed.

Required future detection:

- Required cron line count.
- Canonical crontab hash.
- Crontab drift detection.
- Freshness of watcher/updater/closer/supervisor logs.

Required recovery:

- Restore from committed canonical crontab template, not from ad-hoc backups.
- Verify line counts after restore.
- Run C2 liveness proof.

Alert rule:

- RED/DEGRADED if required cron lines are missing or crontab hash changed.

## Error class E-003: Daily Proof incomplete truth

Status: open.

Verified issue:

- Daily Proof currently proves `crond` is running.
- It does not fully prove watcher freshness, updater freshness, closer freshness, supervisor freshness, crontab integrity, or runtime health.

Required fix:

Daily Proof must report:

- crond status
- required cron lines OK/FAIL
- crontab hash OK/CHANGED
- watcher log age
- updater log age
- closer log age
- shadow log age
- supervisor log age
- cache ages
- runtime mode
- last signal created time
- active signal count
- oldest active signal age
- API credit status
- clock status

## Error class E-004: Termux/Android runtime fragility

Status: open / external to trading code.

Risk:

- Android may kill background processes.
- Phone reboot may stop crond.
- Battery optimization may suspend Termux.
- Ship/mobile network may block or intercept HTTPS.
- Lack of phone internet stops Termux-hosted BotA.

Required fix:

- Verify Termux:Boot installed.
- Verify `~/.termux/boot/` script starts `termux-wake-lock` and `crond`.
- Verify boot script restores canonical crontab if missing.
- Verify battery optimization disabled for Termux and Termux:Boot.

## Error class E-005: Network / TLS / Telegram failure

Status: observed and recovered manually.

Verified issue:

- Telegram send failed with TLS hostname mismatch to `api.telegram.org` during ship/cabin network condition.
- Later `curl -I https://api.telegram.org` returned HTTP 302 and Telegram send passed.

Interpretation:

- This was network/certificate interception or captive network behavior, not BotA code failure.

Required detection:

- Telegram connectivity check.
- Supabase connectivity check.
- Provider connectivity check.
- Alert if network is down after recovery, but avoid spam during transient failures.

## Error class E-006: API/data-provider degradation

Status: partially mitigated historically; still monitor.

Known risks:

- Twelve Data credit exhaustion.
- Yahoo 429/rate-limit behavior.
- OANDA/cache gaps.
- Server clock source unavailable.

Required detection:

- `logs/api_credits.json` movement and usage percent.
- provider error counts.
- cache freshness.
- server clock status.

Required reporting:

- Daily Proof must distinguish quiet market from provider/data failure.

## Error class E-007: ProfitLab observability gap

Status: open.

Verified issue:

- ProfitLab displays signals from Supabase.
- It does not know whether BotA is alive.
- No Supabase runtime-health bridge is verified yet.

Required fix:

- Add BotA runtime-health push to Supabase.
- Add ProfitLab Admin Health Panel.
- Show BotA OFFLINE/DEGRADED if heartbeat is stale.

## Do not misdiagnose again

If signals stop, do not first blame:

- H1 veto
- thresholds
- ADX
- strategy weakness
- pair list

First verify runtime:

1. crontab line counts
2. crond process
3. watcher log mtime
4. updater log mtime
5. closer log mtime
6. supervisor log mtime
7. cache freshness
8. Supabase ACTIVE count
9. Telegram/Supabase connectivity
