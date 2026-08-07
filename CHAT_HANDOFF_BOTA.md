# BotA Chat Handoff

Last updated: 2026-08-07 17:01 UTC

Read this first in any new AI chat before proposing BotA changes.

## Current question

Why does BotA produce very few useful trade signals even though months of runtime,
service, heartbeat, Telegram, and deployment work have been completed?

The current answer is narrower than previous handoffs:

> The live direction engine does produce BUY and SELL decisions. The dominant
> current bottleneck is downstream rejection/eligibility. About 95.61% of the
> inspected decision corpus is rejected.

## Verified live watcher path — 2026-08-07

```text
runsv bota-watcher
  -> tools/run_signal_watcher_with_ledger.sh
  -> tools/signal_watcher_pro.sh --once
```

All seven required services were running during the latest observation.
Control-plane ownership was still degraded because `crond` remained a PID-1
orphan:

```text
manager_count=1
manager_pid=31140
owned=6/7
orphaned=1
running=7/7
duplicates=0
healthy=false
```

Do not confuse this ownership defect with proof that the watcher is not
functioning. The watcher was live and recording decisions.

## Signal funnel evidence — 2026-08-07

Source:

```text
logs/alerts.csv
```

Schema:

```text
timestamp,pair,tf,direction,score,confidence,entry,sl,tp,provider,rejected,filter_str,reasons
```

Corpus:

```text
TOTAL_DECISIONS=2507
HOLD=1082
SELL=959
BUY=466
ACCEPTED=110
REJECTED=2397
ACCEPTANCE_RATE≈4.39%
REJECTION_RATE≈95.61%
```

This is direct evidence that the direction generator is not dead. It creates
1425 BUY/SELL rows in the inspected corpus.

## Dominant rejection strings

Most common observed `filter_str` values include:

```text
794  direction_not_tradeable | score<65 | entry_invalid_zero | rr<=0 | macro6=3
537  score<65 | macro6=3
450  macro6=3 | H1_trend_neutral
294  score<70 | macro6=3
145  direction_not_tradeable | score<65 | entry_invalid_zero | rr<=0 | atr<=0 | macro6=3
50   score<62 | macro6=3
42   macro6=3 | H1_trend_neutral_overridden
16   macro6=3 | H1_trend_confirmed
4    macro6=3 | H4_D1_oppose
```

Interpretation rules:

- score thresholds are a major current suspect;
- `macro6=3` is common but has not yet been proven causal rather than
  informational;
- H1 remains relevant, but the whole-corpus evidence no longer supports the old
  statement that H1 neutral is necessarily the single dominant throughput gate;
- H4/D1 opposition is rare in this corpus.

## Zero entry finding — closed as root-cause hypothesis

A direct classification of all 2507 rows found:

```text
ALL_VALID_ENTRY_SL_TP=1493
ALL_ZERO_ENTRY_SL_TP=1014
MIXED=0
```

Every one of the 1014 zero-entry rows was:

```text
HOLD
score=0.00
M15
```

Pair distribution:

```text
GBPUSD=519
EURUSD=490
USDJPY=5
```

And:

```text
ZERO_ENTRY_BUY_SELL_ROWS=0
```

Therefore `entry=0`, `sl=0`, and `tp=0` are a HOLD symptom, not the current
root cause of lost BUY/SELL signals.

## Audit-script correction

One exploratory Python snippet used `filter_rejected` as a DictReader key. That
field does not exist in `logs/alerts.csv`; the correct key is `rejected`.
Therefore the snippet's printed empty filter-status section is invalid evidence.
The earlier acceptance/rejection counts based on column 11 remain valid.

## Historical H1 evidence — retain, but do not over-generalize

The May 2026 rejected-shadow sample remains real historical evidence: ten
resolved rejected candidates in that small sample all hit SL, including eight
H1-neutral rows. That evidence supports keeping H1 protections until better
counter-evidence exists.

However, it must not be used to claim that H1 neutral is the dominant current
whole-corpus bottleneck. The 2026-08-07 corpus is much larger and shows many
score-gate and direction/HOLD rejections.

## No-change rules until next proof

```text
PRODUCTION_STRATEGY_CHANGED=NO
FILTER_SCORE_CHANGED=NO
H1_THRESHOLD_CHANGED=NO
H4_D1_CHANGED=NO
MACRO_FILTER_CHANGED=NO
RR_POLICY_CHANGED=NO
TELEGRAM_ELIGIBILITY_CHANGED=NO
PROVIDER_CHANGED=NO
SUPABASE_CHANGED=NO
```

Do not lower thresholds merely to force signal volume. First quantify exactly
which valid BUY/SELL candidates are rejected by which gate and what happened to
the accepted 110 rows.

## Next exact proof step

Classify the 1493 rows with valid entry/SL/TP by:

```text
pair
direction
rejected=true/false
score bucket
exact filter_str
```

Then inspect the 110 accepted rows and determine whether they reached Telegram
eligibility, delivery dedup/cooldown, or actual send success.

That is the shortest evidence path to answering why valid-looking BUY/SELL
candidates are not becoming user-visible signals.

## Working discipline

1. Inspect before changing.
2. Use small, pager-proof evidence packages.
3. Do not repeat broad runtime archaeology unless it directly blocks the signal path.
4. Record every material finding with an explicit UTC date.
5. Use the real CSV schema before writing audit scripts.
6. Separate strategy rejection from Telegram delivery and from runtime health.
7. Full-file replacement only when a code mutation is approved.
8. Never change thresholds based only on signal drought frustration.
