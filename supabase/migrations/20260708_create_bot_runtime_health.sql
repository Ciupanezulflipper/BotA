-- Phase 5: BotA current runtime health
-- Purpose:
--   Expose current BotA liveness to Supabase/ProfitLab without touching trading logic.
--
-- Security model:
--   - No Supabase service_role key on Termux.
--   - Termux should later push through a limited Edge Function/webhook.
--   - RLS enabled.
--   - No anon/authenticated direct access.
--   - service_role access only for server-side writers/readers.
--
-- Not included in v1:
--   - append-only history table
--   - crond_pid
--   - full raw runtime_health.json dump

create table if not exists public.bot_runtime_health (
  bot_id text primary key,

  source text not null default 'termux',
  observed_at_utc timestamptz not null,

  bot_mode text not null check (bot_mode in ('HEALTHY', 'DEGRADED', 'UNKNOWN')),
  last_supervisor_run_utc timestamptz,

  watcher_log_age_min integer check (watcher_log_age_min is null or watcher_log_age_min >= 0),
  updater_log_age_min integer check (updater_log_age_min is null or updater_log_age_min >= 0),
  closer_log_age_min integer check (closer_log_age_min is null or closer_log_age_min >= 0),
  shadow_log_age_min integer check (shadow_log_age_min is null or shadow_log_age_min >= 0),

  eurusd_m15_cache_age_min integer check (eurusd_m15_cache_age_min is null or eurusd_m15_cache_age_min >= 0),
  gbpusd_m15_cache_age_min integer check (gbpusd_m15_cache_age_min is null or gbpusd_m15_cache_age_min >= 0),
  eurusd_h1_cache_age_min integer check (eurusd_h1_cache_age_min is null or eurusd_h1_cache_age_min >= 0),
  gbpusd_h1_cache_age_min integer check (gbpusd_h1_cache_age_min is null or gbpusd_h1_cache_age_min >= 0),

  failure_reasons text,
  last_degraded_utc timestamptz,
  last_degraded_reason text,
  last_healthy_utc timestamptz,

  -- Sanitized/allowlisted debug details only. Do not store env, secrets, tokens,
  -- raw shell output, stack traces, or full runtime_health.json here.
  details jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.bot_runtime_health is
  'Current BotA runtime health row. Single-row upsert by bot_id. No trading logic or signals data.';

comment on column public.bot_runtime_health.details is
  'Sanitized allowlisted debug details only. Never store secrets, tokens, env, raw shell output, or full runtime JSON.';

create or replace function public.set_bot_runtime_health_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_bot_runtime_health_updated_at on public.bot_runtime_health;

create trigger trg_bot_runtime_health_updated_at
before update on public.bot_runtime_health
for each row
execute function public.set_bot_runtime_health_updated_at();

alter table public.bot_runtime_health enable row level security;

revoke all on public.bot_runtime_health from anon;
revoke all on public.bot_runtime_health from authenticated;

grant select, insert, update, delete on public.bot_runtime_health to service_role;

drop policy if exists "Service role full access" on public.bot_runtime_health;

create policy "Service role full access"
on public.bot_runtime_health
for all
to service_role
using (true)
with check (true);
