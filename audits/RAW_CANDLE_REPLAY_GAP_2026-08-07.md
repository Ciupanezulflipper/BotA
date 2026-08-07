# Raw Candle Replay Gap — 2026-08-07

Recorded from production phone evidence: **2026-08-07 19:10:26 UTC**

## Purpose

Determine whether the retained local candle inputs are sufficient for a deterministic June–July 2026 replay of the live BotA M15 strategy without making provider calls or mutating production.

## Corrected file-format finding

The canonical files under `data/candles/` are valid CSV files with ISO-like UTC timestamps (`YYYY-MM-DD HH:MM:SS`) in column 1. A prior inventory incorrectly reported zero rows because that one-off parser accepted numeric epoch timestamps only. This audit supersedes that parser result.

The prior standalone-file check also printed `COVERS_2026_06_01=YES` when a file merely *started before* June 1. That label was logically incomplete: the standalone M15 files end in March and do **not** cover the June–July replay interval.

## Verified retained coverage

| Pair | TF | Rows | First UTC | Last UTC | June–July replay coverage |
|---|---:|---:|---|---|---|
| EURUSD | M15 | 499 | 2026-07-31 15:00 | 2026-08-07 19:30 | INSUFFICIENT |
| EURUSD | H1 | 499 | 2026-07-10 00:00 | 2026-08-07 18:00 | INSUFFICIENT |
| EURUSD | H4 | 499 | 2026-04-14 13:00 | 2026-08-07 13:00 | SUFFICIENT for June–July interval |
| EURUSD | D1 | 499 | 2024-09-02 21:00 | 2026-08-05 21:00 | SUFFICIENT for June–July interval |
| GBPUSD | M15 | 499 | 2026-07-31 15:00 | 2026-08-07 19:30 | INSUFFICIENT |
| GBPUSD | H1 | 499 | 2026-07-10 00:00 | 2026-08-07 18:00 | INSUFFICIENT |
| GBPUSD | H4 | 499 | 2026-04-14 13:00 | 2026-08-07 13:00 | SUFFICIENT for June–July interval |
| GBPUSD | D1 | 499 | 2024-09-02 21:00 | 2026-08-05 21:00 | SUFFICIENT for June–July interval |

Standalone historical M15 files:

```text
data/EURUSD_M15.csv: 500 rows, 2026-02-27 17:00 UTC -> 2026-03-06 21:45 UTC
data/GBPUSD_M15.csv: 500 rows, 2026-02-27 17:00 UTC -> 2026-03-06 21:45 UTC
```

These files are useful only for the older March period and do not bridge the June–July gap.

No identical SHA-256 file groups were found among the ten inspected files.

## Production fetcher limitation

Current `tools/data_fetch_candles.sh` requests a rolling OANDA window with `count=500`. Its Yahoo fallback also requests short rolling ranges. It is appropriate for live context but is not a historical replay data collector and must not be used to overwrite live caches while building a research dataset.

## Conclusion

```text
LOCAL_M15_JUNE_JULY_COVERAGE=NO
LOCAL_H1_JUNE_JULY_COVERAGE=NO
LOCAL_H4_JUNE_JULY_COVERAGE=YES
LOCAL_D1_JUNE_JULY_COVERAGE=YES
STANDALONE_M15_JUNE_JULY_COVERAGE=NO
TRUE_REPLAY_FROM_RETAINED_INPUTS=BLOCKED
REQUIRED_NEXT_CAPABILITY=IMMUTABLE_HISTORICAL_DATASET_ACQUISITION
```

The investigation should stop trying to reconstruct missing historical inputs from rolling production caches. Acquire the missing historical data once into an immutable replay namespace with explicit coverage, checksums, provider metadata, and no live-cache mutation.

## Safety

```text
MUTATION_PERFORMED=NO
PRODUCTION_FILES_CHANGED=NO
PROVIDER_CALL_PERFORMED=NO
TELEGRAM_CALL_PERFORMED=NO
```
