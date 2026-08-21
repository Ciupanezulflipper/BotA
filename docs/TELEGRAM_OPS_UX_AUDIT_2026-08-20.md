# Telegram operational UX audit — 2026-08-20

Observed production Telegram output mixed user-facing Market Pulse messages with raw engineering alerts such as `control_plane:zombie_runsv_count:2`, generic recovery strings, and DEADMAN lines carrying full internal timestamps.

Two separate defects are confirmed from current source:

1. `tools/bota_supervisor.sh` forwards the raw joined `FAILURE_STR` directly to Telegram. Zombie-only rows are already classified in the readiness tracker as unattributed monitoring noise, so those transitions should remain recorded locally but should not create subscriber-facing DEGRADED/RECOVERY churn.
2. `tools/heartbeat_runtime.py` evaluates DEADMAN unconditionally after obtaining trusted UTC. The production market gate is 07:00–20:00 UTC Monday–Friday, so a new stale-progress DEADMAN must not be emitted outside that active session. A recovery for a previously alerted in-session incident may still be delivered if fresh progress resumes.

Presentation target:

- no raw pipe-separated failure codes in Telegram;
- no zombie-only Telegram transition spam;
- no new DEADMAN alert outside 07:00–20:00 UTC Monday–Friday;
- concise `SCAN DELAYED`, `SCAN RESTORED`, `SYSTEM ISSUE`, and `SYSTEM RESTORED` wording;
- preserve local logs, runtime-health evidence, failure classification, trading safeguards, strategy thresholds, pair scope, and delivery semantics.

This audit does not authorize a strategy/risk/threshold change and does not declare production readiness.
