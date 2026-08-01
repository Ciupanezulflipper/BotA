# BotA Production Validation Failure — 2026-08-01

## Status

The one-week production validation did not pass.

BotA remained capable of fetching data, calculating decisions, and delivering at
least one eligible GBPUSD M15 signal. However, the runtime, recovery,
deployment, provider-budget, and notification layers were not reliable enough
to declare production validation complete.

## Verified runtime evidence

During the validation period:

- the control plane intermittently reached one `runsvdir` manager with all
  seven required `runsv` supervisors reparented to PID 1;
- the measured degraded state was `owned=0/7`, `running=7/7`, and
  `orphaned=7`;
- a later one-shot reconciliation restored one manager, seven owned services,
  seven running services, and zero orphans;
- service counts temporarily fell below seven during production operation;
- the phone checkout and GitHub `main` were not synchronized;
- the canonical crontab verification failed;
- runtime and GitHub documentation described a watchdog configuration that
  did not match the actual phone.

## Recovery incident

The existing native service-daemon watchdog startup path could not run because
the configured service-daemon executable was unavailable on the phone.

A continuous `runsvdir` guard was then started. Termux repeatedly restarted
while that continuous guard was active.

The continuous guard and watchdog were stopped. The production boot launcher
was replaced with a safe version that starts the standard Termux service tree
but intentionally does not start an automatic topology-recovery process.

At the final rollback verification:

```text
manager_count=1
owned=7/7
running=7/7
orphaned=0
control_plane_rc=0
automatic_recovery=disabled
cat >"$INCIDENT_FILE" <<'EOF'
