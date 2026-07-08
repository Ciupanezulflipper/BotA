# BotA -> ProfitLab Reliability Handoff

Last updated: 2026-07-08

## Executive summary

BotA's confirmed weakness is silent runtime failure, not trading strategy.

A crontab wipe removed BotA runtime jobs while Daily Proof continued to report that cron was running. ProfitLab showed no active signals but could not distinguish quiet market conditions from a dead signal factory.

The required fix is an observability bridge:

```text
BotA supervisor -> runtime_health -> Supabase -> ProfitLab Admin Health Panel
```

## Verified findings

- BotA powers ProfitLab through Supabase `public.signals`.
- ProfitLab can display signals, but currently has no verified BotA runtime-health source.
- BotA local supervisor exists and is intended to check runtime health.
- BotA runtime cron was restored and C2 liveness proof passed.
- Daily Proof truth fields are now upgraded by commit `5744802`.

## Remaining risks

- Termux:Boot not yet verified.
- Wake lock not yet verified.
- Canonical crontab is committed as source of truth and verified.
- Runtime health not yet pushed to Supabase.
- ProfitLab does not yet display HEALTHY/DEGRADED/OFFLINE.
- Phone/mobile internet loss can still stop Termux-hosted BotA.

## Decisions taken

- No trading strategy changes.
- No threshold changes.
- No H1 logic changes.
- No pair-list changes.
- Reliability work takes priority over signal-frequency work.

## Required ProfitLab changes

Minimum Admin Health Panel:

- BotA status: HEALTHY / DEGRADED / OFFLINE
- Last heartbeat age
- Watcher age
- Updater age
- Closer age
- Supervisor age
- API credits
- Clock status
- Active signal count
- Last signal timestamp
- Failure reasons

Reporting correction:

- If dashboard P&L is all-time, label it All-Time P&L.
- If win rate is all-time, label it All-Time Win Rate.
- Only use Today/30-Day labels if the query actually filters by those windows.

## Runtime health fields ProfitLab should display

```yaml
bot_id: bota_termux_primary
last_heartbeat_utc:
bot_mode: HEALTHY | DEGRADED | OFFLINE
crond_running:
required_cron_lines_ok:
crontab_hash:
watcher_log_age_min:
updater_log_age_min:
closer_log_age_min:
shadow_log_age_min:
supervisor_log_age_min:
api_credits_used:
api_credits_limit:
api_warned:
server_clock_ok:
clock_drift_seconds:
market_gate_status:
last_signal_created_at:
active_signal_count:
oldest_active_age_min:
cache_age_summary:
network_telegram_ok:
network_supabase_ok:
failure_reasons:
last_degraded_utc:
last_recovery_utc:
```

## Required BotA-side changes before ProfitLab health panel

1. Prove C2 liveness after restored cron.
2. Commit canonical crontab template and verification script.
3. Verify Termux:Boot and wake lock.
4. Upgrade Daily Proof truth fields. CLOSED by commit `5744802`.
5. Push `runtime_health` to Supabase.
6. Only then wire ProfitLab health panel.

## Production readiness score

Current: 58/100.

Target after minimal reliability roadmap: 85/100.

Reason for current score:

- Runtime cron has been restored.
- Supervisor exists.
- Daily Proof and Telegram can send.
- But silent failure can still occur from ProfitLab's perspective until runtime health is pushed and displayed.

## Phase 4C handoff update

Timestamp: 2026-07-08 15:44:34 UTC

Daily Proof truth upgrade is complete.

Commit:
- `5744802` — `tools: strengthen BotA daily proof runtime reporting`

Impact for ProfitLab:
- ProfitLab still cannot see runtime health directly.
- BotA now produces a stronger local Daily Proof message that distinguishes quiet markets from stale runtime evidence.
- Next product/backend requirement remains: push `runtime_health` to Supabase, then expose it in a ProfitLab Admin Health Panel.

Still not done:
- Supabase runtime health table/row.
- ProfitLab Admin Health Panel.
- Real reboot recovery proof.
