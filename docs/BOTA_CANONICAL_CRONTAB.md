# BotA Canonical Crontab

Last updated: **2026-08-09 UTC**

Purpose: preserve the canonical cron block without reintroducing duplicate ownership after core BotA services migrated to runit.

## Source of truth

- Canonical BotA cron block: `ops/bota_crontab.canonical`
- Verifier: `tools/verify_canonical_crontab.sh`
- Installer: `tools/install_canonical_crontab.sh`
- Current production/control-plane truth: `CONTINUITY_CURRENT.md`
- Package #1/#2 control-plane audit: `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md`

## Ownership model

The canonical file is now a **hybrid runit + cron record**.

Entries beginning with `#MIGRATED_TO_RUNIT` are intentionally disabled historical/canonical references. They must **not** be uncommented by an installer, verifier, repair script, or operator unless a separately reviewed ownership migration explicitly reverses the runit architecture.

Core services owned by runit:

```text
bota-updater
bota-watcher
bota-closer
bota-shadow
bota-heartbeat
bota-supervisor
crond
```

The direct cron entries for watcher, updater, closer, shadow, heartbeat, and supervisor are therefore marked `#MIGRATED_TO_RUNIT` in `ops/bota_crontab.canonical`.

Current watcher invariant:

```text
ACTIVE_DIRECT_WATCHER_CRON=0
WATCHER_OWNER=runit
```

`crond` itself is also supervised by runit. Package #2 proved that `crond` being alive is not enough: the live daemon must belong to the current manager-owned `runsv crond`, with no stale singleton process holding `crond.pid`.

## Active canonical cron jobs

The active, non-commented BotA entries currently include the independent/scheduled jobs retained in `ops/bota_crontab.canonical`, including:

- `alerts_to_trades.py`
- `pause_guard.py`
- `autostatus.sh`
- `profitlab_delivery.py` once per minute
- `signal_accuracy.py`
- `clock_drift_check.sh`
- `daily_summary_server_gate.sh`
- `run_runtime_health_push.sh`

The canonical file itself is authoritative for exact commands and cadence. Do not duplicate them manually from this prose summary.

## Rules

- Preserve unrelated project cron blocks when installing BotA canonical entries.
- Preserve BotA `CRON_TZ=UTC` semantics where the canonical block requires them.
- Do not reactivate `#MIGRATED_TO_RUNIT` lines.
- Do not create a second watcher/updater/shadow/closer/supervisor/heartbeat owner.
- Keep exactly one active ProfitLab delivery cron entry.
- Do not run `profitlab_delivery.py --bootstrap` on the current production state.
- Verify the live service tree through `$PREFIX/var/service`; do not infer service ownership from cron text alone.
- Treat service liveness and correct manager ownership as separate health dimensions.
- Do not change strategy, thresholds, pair selection, Telegram eligibility, or Supabase signal semantics through cron repair.

## Current Package #2 control-plane lesson

A production incident on 2026-08-09 showed:

```text
old live crond PID 4107 (PPID 1) still held crond.pid
current manager-owned runsv crond PID 24583 retried replacements
cron jobs still executed from the stale daemon
runit service appeared down
```

After identity-checked repair, the current runsv started one stable replacement, and the final topology was:

```text
manager_count=1
owned_services=7/7
running_services=7/7
orphaned_runsv=0
duplicate_service_rows=0
live_crond_count=1
```

Package #2 still needs reviewed persistent-watchdog and stale-live-singleton recovery hardening. Do not encode ad-hoc process killing in the canonical cron installer.

## Acceptance

A canonical-cron verification is healthy only when all applicable conditions pass:

```text
canonical active cron entries have expected counts
MIGRATED_TO_RUNIT entries remain commented
active direct watcher cron count = 0
active ProfitLab cron count = 1
one native runsvdir manager
all seven required runsv supervisors owned by that manager
all seven required services running
zero orphaned supervisors
zero duplicate service rows
exactly one correctly owned live crond child
```

Cron hash/count checks alone are not sufficient production-readiness proof.