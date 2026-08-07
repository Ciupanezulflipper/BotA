# BotA Chat Handoff

Last updated: 2026-07-14

Read this first in any new AI chat before proposing BotA changes.

<!-- BOTA_SIGNAL_LIFECYCLE_V31_2026_07_14 -->

## Latest Status — 2026-07-14

**Signal lifecycle v3.1 is locally verified. It is NOT pushed and NOT in production.**

- Implementation commit: `be8c6ef` on branch `fix/signal-lifecycle-market-hours-20260713`
- Branch has NOT been pushed to origin.
- Production `main` branch and live BotA runtime are UNCHANGED.
- 119 tests pass, 0 failures, across PYTHONHASHSEED 0 / 1 / 17 / 99991.

**Canonical read order for every new AI session:**

1. `CHAT_HANDOFF_BOTA.md` — this file, latest status first
2. `DECISIONS.md` — locked engineering contracts
3. `RESOLVED.md` — closed engineering issues
4. `CONTINUITY.md` — full running session log
5. `state/STATE.json` — machine-readable current state
6. Relevant runtime logs in `/data/data/com.termux/files/home/BotA/logs/`

**Log discipline:**

- `logs/error.log` is a live runtime stream. It is NOT the permanent lessons ledger.
- Permanent lessons belong in `RESOLVED.md`, `DECISIONS.md`, `CONTINUITY.md`, and regression tests.
- Do not cite `logs/error.log` as proof of a resolved engineering decision.

**Next gate:**

1. Documentation review (current step)
2. Separate documentation commit
3. Push `fix/signal-lifecycle-market-hours-20260713` to origin as an isolated branch
4. Open a draft PR for review
5. CI and source review
6. Historical / read-only dry-run validation on the live BotA worktree
7. Separately approved production rollout
8. First real-signal proof

**Do NOT merge or deploy directly.** Every gate above must be completed and recorded before production deployment.

## Current situation

BotA had a signal drought / low accepted-signal throughput.

Main question:
Is BotA too quiet because the strategy is broken, or because filters are correctly blocking bad trades?

Current grounded answer:
BotA is quiet, but replay evidence shows the H1_trend_neutral gate protected BotA from losing trades in the current tested sample.

## Latest verified commits

1. bb01ff38d694482071e496922fd3b1d20a0a5644
Message: fix: map shadow tracker filter_str and log H1 outcome proof
Meaning: tools/rejected_shadow_tracker.py now recognizes filter_str from logs/alerts.csv.

2. ccf9f18c470e5b78ad8b08f84b00bba2ba999f19
Message: fix: shadow JSONL dedup + outcome proof — 7 SL_HIT 0 TP_HIT on rejected candidates
Meaning: duplicate shadow rows cleaned and current rejected-candidate outcome proof documented.

3. Current pending commit
Meaning: final May 13 pending rows resolved as SL_HIT and handoff was updated.

## Proven facts

Shadow tracker fix:
tools/rejected_shadow_tracker.py recognizes:
["filter_reason", "filter_reasons", "filters", "filter_str"]

Shadow JSONL was cleaned after final pending resolution.

Before cleanup: 13 rows
After cleanup: 10 rows
Removed: 3 duplicate rows

Final clean outcome state:
Total rows: 10
Resolved: 10
Pending: 0
TP_HIT: 0
SL_HIT: 10
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
2026-05-13 15:49 UTC GBPUSD BUY score=71.0 -> SL_HIT -19.9p
2026-05-13 16:00 UTC GBPUSD BUY score=68.0 -> SL_HIT -19.9p
2026-05-13 16:16 UTC GBPUSD BUY score=66.0 -> SL_HIT -19.6p

Current H1 sample:
H1 resolved: 8
TP_HIT: 0
SL_HIT: 8
WR: 0.0%

Score-gate resolved rows:
2026-05-07 14:15 UTC EURUSD BUY score=55.2 -> SL_HIT -11.7p
2026-05-07 14:30 UTC GBPUSD BUY score=56.2 -> SL_HIT -13.7p

Score-gate sample:
Resolved: 2
TP_HIT: 0
SL_HIT: 2
WR: 0.0%

## Current interpretation

H1_trend_neutral is the main throughput gate.

Current replay evidence says H1_trend_neutral is protective in this tested sample:
8 resolved H1-blocked candidates
8 SL_HIT
0 TP_HIT

Therefore:
Do NOT lower H1 override threshold yet.
Do NOT remove H1 veto yet.
Do NOT increase strategy aggressiveness based only on signal drought frustration.

## What is not proven yet

This is not final proof that H1 is always correct.

Limitations:
H1 resolved sample size is 8.
More samples are needed before long-term tuning.
The current evidence is strong enough to block reckless H1 changes, but not enough to finalize all future strategy decisions.

## No-change rules

Until more rejected-candidate samples are collected:

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

Keep collecting rejected shadow outcomes.

When enough new rejected rows exist, run:

cd /data/data/com.termux/files/home/BotA || { echo "FAIL"; exit 1; }

python3 tools/rejected_shadow_tracker.py --score-min 65 --lookback-hours 720 --outcome-hours 24

Then inspect logs/rejected_shadow_outcomes.jsonl and join back to logs/alerts.csv before drawing conclusions.

## Separate UX issue

Telegram API warning spam is a separate problem.

The strategy should not be changed because of warning frustration.
However, Telegram UX should eventually be improved so public/user channel receives useful status summaries instead of repeated API warning fear messages.

## Working discipline

1. Inspect before changing.
2. Full-file replacement only when approved.
3. No patches unless explicitly approved.
4. Always check logs/error.log before code changes.
5. Always include PASS/FAIL outcomes.
6. Always state whether production, strategy, Telegram, cron, or GitHub changed.
7. Never assume a bottleneck without log proof.
8. Never change thresholds based on frustration alone.
