# BotA AI Start Here

Last updated: **2026-08-07 19:10 UTC**

Read this before proposing BotA commands, code, service, strategy, Telegram, provider, Supabase, replay, or deployment changes.

## Current authoritative truth

```text
RECORDED_DATE=2026-08-07
PHONE_BRANCH=deploy/repaired-core-20260802T215531Z
PHONE_HEAD=73b2306b5843f3396823ce815e96051abf78cf50
LIVE_WATCHER=RUNNING
LIVE_PAIRS=EURUSD_GBPUSD_ONLY
LIVE_TIMEFRAME=M15
FILTER_SCORE_MIN_ALL=65
H1_VETO_OVERRIDE_SCORE=75
TELEGRAM_MIN_SCORE=70
TELEGRAM_COOLDOWN_SECONDS=1800
DRY_RUN_MODE=0
TELEGRAM_ENABLED=1
BUY_SELL_VALID_ROWS=1427
BUY_SELL_ACCEPTED=110
BUY_SELL_REJECTED=1317
REJECTED_SCORE_GATE=903
REJECTED_H1_NEUTRAL=410
REJECTED_H4_D1_OPPOSE=4
TELEGRAM_SENT=61
TELEGRAM_COOLDOWN=38
TELEGRAM_SCORE_GATE=6
TELEGRAM_FAILED=1
RECENT_PUBLISHED_SIGNALS=13
RECENT_WINS=3
RECENT_LOSSES=9
RECENT_CANCELLED=1
RECENT_TOTAL_PIPS=-71.40
MARCH_LEDGER_ROWS=51
MARCH_ADX_LT30_PIPS=+98.0
TEMPORAL_PUBLISHED=13
TEMPORAL_MATCHED=9
TEMPORAL_MATCH_RATE=69.2_PERCENT
TEMPORAL_ADX_LT30_PIPS=+13.1
TEMPORAL_ADX_GTE30_WINS=0
TEMPORAL_ADX_GTE30_LOSSES=4
LOCAL_SIGNAL_RETENTION_GAP=CONFIRMED
LOCAL_M15_JUNE_JULY_COVERAGE=NO
LOCAL_H1_JUNE_JULY_COVERAGE=NO
LOCAL_H4_JUNE_JULY_COVERAGE=YES
LOCAL_D1_JUNE_JULY_COVERAGE=YES
TRUE_REPLAY_FROM_RETAINED_INPUTS=BLOCKED
STRATEGY_MUTATION_ALLOWED=NO_PENDING_TRUE_REPLAY
```

## Read first

1. `CONTINUITY_CURRENT.md` — current state and exactly one next objective.
2. `docs/FORENSIC_OPERATING_MODEL.md` — mandatory efficient investigation workflow.
3. `audits/RAW_CANDLE_REPLAY_GAP_2026-08-07.md` — current replay-data blocker.

Older dated audits remain evidence, but do not restart their closed investigative branches unless new contradictory evidence appears.

## Current diagnosis

BotA can produce BUY/SELL decisions and Telegram can send them. The current problem is signal quality/calibration, not basic transport.

ADX is the strongest replay candidate found so far:

```text
March baseline:          -264.1 pips
March ADX<30:             +98.0 pips
Later matched baseline:   -70.2 pips
Later matched ADX<30:     +13.1 pips
Later matched ADX>=30:     0W / 4L / -83.3 pips
```

This is not production approval. The later component sample is only 9/13 because local signal rows were not retained for four published outcomes.

## Raw-data blocker — verified 2026-08-07 19:10:26 UTC

Both pairs retain only:

```text
M15: 2026-07-31 -> 2026-08-07
H1 : 2026-07-10 -> 2026-08-07
H4 : 2026-04-14 -> 2026-08-07
D1 : 2024-09-02 -> 2026-08-05
```

Standalone historical M15 files end on 2026-03-06. They do not cover June–July.

A previous numeric-only CSV parser incorrectly reported the canonical CSVs as zero-row files. That result is superseded; they are valid ISO-timestamp CSVs.

## Mandatory source hierarchy

```text
GitHub connector  -> code, commits, PRs, docs, tests
Supabase connector -> published signal/outcome/database truth
Phone/Termux       -> runtime-only state, .env, local-only logs/caches
```

Do not ask the user to run a phone probe for information already obtainable through a connector.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, add a third pair, or modify ADX/RSI production logic yet.

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy semantics differ from the live watcher.

Do not use the live rolling candle fetcher to build replay history; it writes production cache paths and uses a short rolling window.

Never push directly to `main`. Use branch -> complete-file writes -> verified diff -> PR.

## Exactly one next engineering objective

Stop issuing ad-hoc forensic commands. Build reusable replay infrastructure:

```text
1. immutable historical-data collector + integrity manifest
2. deterministic replay harness for live production semantics
3. replay frozen A/B/C policies
4. only then consider production strategy changes
```

Frozen policies:

```text
A = current production baseline
B = score >=70 AND ADX <30
C = score >=70 AND ADX <30 AND no extreme RSI
```
