# P8 Documentation Workflow Exception — 2026-08-03

At 2026-08-03 01:14 UTC, the documentation-only file
`audits/P8_HEARTBEAT_PHONE_DEPLOYMENT_2026-08-03.md` was mistakenly created
directly on `main` as commit `db911fce58fe40bb24cf7859b10d0e24a2ca6229`.

This violated the standing no-direct-push-to-main workflow rule. It did not
change runtime code, services, crontab, strategy, providers, Telegram delivery,
or Supabase. The audit content accurately records the observed P8 deployment.

Corrective rule: all subsequent documentation and code changes must use a
branch, pull request, review gates, and merge. Do not repeat this exception.
