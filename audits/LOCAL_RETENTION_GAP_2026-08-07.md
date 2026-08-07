# Local Retention Gap Audit — 2026-08-07

Recorded: 2026-08-07 18:58 UTC

## Purpose

Determine whether the four June 23-26 published BotA signals that failed the tight June-July component join can be recovered from the retained local `logs/alerts.csv` using a wider date/score/entry search.

## Source

Read-only Termux audit of `~/BotA/logs/alerts.csv`.

No production file, strategy setting, service, provider, Telegram, Supabase row, or runtime state was mutated.

## Targets

```text
2026-06-23 GBPUSD SELL score=79 entry=1.32179 WIN +33.1
2026-06-23 EURUSD SELL score=78 entry=1.13862 LOSS -13.3
2026-06-24 GBPUSD SELL score=77 entry=1.31448 LOSS -21.0
2026-06-26 EURUSD SELL score=75 entry=1.13892 CANCELLED 0.0
```

## Recovery result

```text
TARGETS_TOTAL=4
TARGETS_WITH_NEARBY_ROWS=1
TARGETS_WITH_RELAXED_MATCH=0
TARGETS_WITH_RELAXED_COMPONENT_MATCH=0
VERDICT=LOCAL_RETENTION_GAP_CONFIRMED
```

Three targets had no same-pair/same-direction M15 rows within +/-2 calendar days in the retained local alerts data. The June 23 EURUSD target had nine nearby rows, but none was within the relaxed identity tolerance of <=5 pips entry difference, <=3 score points, and <=1 day.

Closest June 23 EURUSD row:

```text
2026-06-22T17:00:39+0400
score=77.6
entry=1.14360
entry_delta=49.8p
score_delta=0.4
day_delta=1
rejected=false
ADX=26.2
RSI=37.9
H1=neutral_overridden
RELAXED=NO
```

This is not the published June 23 EURUSD signal at entry 1.13862.

## Consequence

The full 13-signal June-July component validation cannot be reconstructed from the currently retained `alerts.csv`. The existing 9/13 later-period join remains useful directional evidence but must not be promoted to complete out-of-sample proof.

The missing rows are now a confirmed retention/observability gap rather than a matching-tolerance problem.

## Strategy interpretation

Cross-period ADX evidence remains directionally consistent:

```text
March baseline: -264.1 pips
March ADX<30: +98.0 pips
June-July matched baseline: -70.2 pips
June-July matched ADX<30: +13.1 pips
June-July matched ADX>=30: 0W/4L, -83.3 pips
```

However, no production ADX or RSI mutation is approved because later-period component coverage is incomplete.

## Next action

Stop trying to reconstruct the four missing component rows from `alerts.csv`. Build or run a true historical replay from raw candles through the live scoring path, with candidate policies frozen before outcomes are examined:

```text
A: current production baseline
B: score >=70 AND ADX <30
C: score >=70 AND ADX <30 AND no extreme RSI
```

The replay must use the live production scoring/fusion semantics, not `tools/backtest_bota.py`, whose strategy implementation differs from the current watcher path.
