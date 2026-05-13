# BotA Chat Handoff

Last updated: 2026-05-14

Read this first in any new AI chat before proposing BotA changes.

## Current situation

BotA had a signal drought / low accepted-signal throughput.

Main question:
Is BotA too quiet because the strategy is broken, or because filters are correctly blocking bad trades?

Current grounded answer:
BotA is quiet, but first replay evidence shows the H1_trend_neutral gate is protective so far, not proven harmful.

## Latest verified commits

1. bb01ff38d694482071e496922fd3b1d20a0a5644
Message: fix: map shadow tracker filter_str and log H1 outcome proof
Meaning: tools/rejected_shadow_tracker.py now recognizes filter_str from logs/alerts.csv.

2. ccf9f18c470e5b78ad8b08f84b00bba2ba999f19
Message: fix: shadow JSONL dedup + outcome proof — 7 SL_HIT 0 TP_HIT on rejected candidates
Meaning: duplicate shadow rows cleaned and current rejected-candidate outcome proof documented.

## Proven facts

Shadow tracker fix:
tools/rejected_shadow_tracker.py now recognizes:
["filter_reason", "filter_reasons", "filters", "filter_str"]

Shadow JSONL state:
logs/rejected_shadow_outcomes.jsonl was deduplicated.

Before: 13 rows
After: 10 rows
Removed: 3 duplicate OPEN_PENDING rows

Current clean state:
Total rows: 10
Resolved: 7
Pending: 3
TP_HIT: 0
SL_HIT: 7
WR: 0.0%

## H1 evidence

Shadow rows were joined back to logs/alerts.csv.

Join result:
Matched: 10
Unmatched: 0
Matched H1_trend_neutral: 8
Matched score_gate: 2

Resolved H1_trend_neutral rows:
2026-04-23 14:47 UTC EURUSD BUY score=76.1 -> SL_HIT -16.1p
2026-04-23 15:46 UTC EURUSD BUY score=71.7 -> SL_HIT -16.0p
2026-04-23 16:00 UTC EURUSD BUY score=68.7 -> SL_HIT -16.0p
2026-05-11 14:30 UTC EURUSD BUY score=68.5 -> SL_HIT -11.2p
2026-05-11 16:51 UTC GBPUSD BUY score=71.0 -> SL_HIT -17.9p

Current H1 resolved sample:
H1 resolved: 5
TP_HIT: 0
SL_HIT: 5
WR: 0.0%

Score-gate resolved rows:
2026-05-07 14:15 UTC EURUSD BUY score=55.2 -> SL_HIT -11.7p
2026-05-07 14:30 UTC GBPUSD BUY score=56.2 -> SL_HIT -13.7p

Pending H1 rows:
2026-05-13 15:49 UTC GBPUSD BUY score=71.0 OPEN_PENDING
2026-05-13 16:00 UTC GBPUSD BUY score=68.0 OPEN_PENDING
2026-05-13 16:16 UTC GBPUSD BUY score=66.0 OPEN_PENDING

## Current interpretation

H1_trend_neutral is the main throughput gate.

However, first replay evidence says H1_trend_neutral is protective so far:
5 resolved H1-blocked candidates
5 SL_HIT
0 TP_HIT

Do NOT lower H1 override threshold yet.
Do NOT remove H1 veto yet.
Do NOT increase strategy aggressiveness based only on signal drought frustration.

## What is not proven yet

This is not final proof that H1 is always correct.

Limitations:
H1 resolved sample size is only 5.
3 H1 rows remain OPEN_PENDING.
More samples are needed.

Current evidence is strong enough to block reckless strategy changes, but not enough to finalize long-term tuning.

## No-change rules

Until the 3 pending rows resolve:

PRODUCTION_CHANGED=NO
STRATEGY_CHANGED=NO
TELEGRAM_CHANGED=NO
CRON_CHANGED=NO
H1_THRESHOLD_CHANGED=NO
FILTER_SCORE_CHANGED=NO

Do not change:
H1 veto
H1 override threshold
FILTER_SCORE_MIN
TELEGRAM_MIN_SCORE
Cron schedule
Telegram alert routing
Production signal pipeline

## Next exact proof step

After 2026-05-14 16:00 UTC, run:

cd /data/data/com.termux/files/home/BotA || { echo "FAIL"; exit 1; }

python3 tools/rejected_shadow_tracker.py --score-min 65 --lookback-hours 720 --outcome-hours 24

Then inspect logs/rejected_shadow_outcomes.jsonl.

If the 3 pending rows become SL_HIT, the H1 protective case strengthens.
If any becomes TP_HIT, that is counter-evidence and must be analyzed before any threshold change.

## Working discipline

1. Inspect before changing.
2. Full-file replacement only when approved.
3. No patches unless explicitly approved.
4. Always check logs/error.log before code changes.
5. Always include PASS/FAIL outcomes.
6. Always state whether production, strategy, Telegram, cron, or GitHub changed.
7. Never assume a bottleneck without log proof.
8. Never change thresholds based on frustration alone.
