# BotA reporting-truth rebase — 2026-08-08

Base: `7fc51dd2f9209b2efeace62e6c1de9f65e62e32c`

Purpose: preserve the current three-pair / Policy-B production scope while carrying forward the reporting-truth corrections from PR #45.

Scope:
- `tools/daily_summary.sh`
- `tools/verify_canonical_crontab.sh`
- `ops/bota_crontab.canonical`
- `tests/test_reporting_truth_policy.py`

Safety:
- no strategy thresholds changed;
- no pair/timeframe content removed;
- current EURUSD/GBPUSD/USDJPY and Policy-B command text preserved;
- six runit-owned jobs are represented as `#MIGRATED_TO_RUNIT` in the canonical cron block;
- no live crontab, service, Telegram, provider, or Supabase mutation performed by this branch.
