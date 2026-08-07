# BotA AI Start Here

Last updated: **2026-08-07 20:20 UTC**

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
HISTORICAL_COLLECTOR=AVAILABLE_ON_THIS_REVISION
HISTORICAL_DATASET_ACQUIRED=NO
STRATEGY_MUTATION_ALLOWED=NO_PENDING_TRUE_REPLAY
```

## Read first

1. `CONTINUITY_CURRENT.md` — current state and exactly one next action.
2. `docs/FORENSIC_OPERATING_MODEL.md` — mandatory connector-first workflow.
3. `audits/HISTORICAL_CANDLE_ACQUISITION_2026-08-07.md` — collector safety/data contract.
4. `audits/RAW_CANDLE_REPLAY_GAP_2026-08-07.md` — why historical acquisition is required.

Older dated audits remain evidence. Do not restart closed investigative branches without new contradictory evidence.

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

## Historical data acquisition

Use only:

```text
tools/fetch_historical_candles.py
```

Contract:

```text
preview/no-network by default
--execute required for provider GETs
OANDA price=M
EURUSD GBPUSD
M15 H1 H4 D1
output=data/replay/<dataset-id>
existing dataset never overwritten
raw provider responses preserved
SHA-256 manifest emitted
production data/candles cache not touched
```

The required first dataset is:

```text
dataset-id=oanda-20260601-20260801-20260807
range=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
pairs=EURUSD GBPUSD
timeframes=M15 H1 H4 D1
```

Do not use `tools/data_fetch_candles.sh` for replay history; it is the rolling production fetcher and writes live cache paths.

## PR #6 warning

Draft PR #6 is historical design evidence only. It is currently non-mergeable and GitHub reports 129 changed files, including out-of-scope canonical/runtime paths. Do not merge or cherry-pick it wholesale. The current historical collector is the clean independently tested extraction.

## Mandatory source hierarchy

```text
GitHub connector   -> code, commits, PRs, docs, tests
Supabase connector -> published signal/outcome/database truth
Phone/Termux       -> runtime-only state, credentials, local-only logs/data
```

Do not ask the user to run a phone probe for information already obtainable through a connector.

## Scope lock

Do not lower score/H1/Telegram floors, remove cooldown, add a third pair, or modify ADX/RSI production logic yet.

Do not use `tools/backtest_bota.py` as production-rule validation because its strategy semantics differ from the live watcher.

Never push directly to `main`. Use branch -> complete-file writes -> verified diff -> PR.

## Exactly one next action after merge

Acquire the immutable June-July OANDA dataset on the phone and verify its manifest/checksums.

Only after acquisition passes, build/run a deterministic replay of the live production semantics for the frozen policies:

```text
A = current production baseline
B = score >=70 AND ADX <30
C = score >=70 AND ADX <30 AND no extreme RSI
```

No production strategy mutation before that replay.
