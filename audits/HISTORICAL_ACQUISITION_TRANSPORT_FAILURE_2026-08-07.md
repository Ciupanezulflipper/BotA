# Historical Acquisition Transport Failure — 2026-08-07

Recorded phone attempt: **2026-08-07 20:29:19 UTC**.

## Scope

Immutable replay dataset attempt:

```text
dataset-id=oanda-warmup-20240101-20260801-20260807-r2
raw_range=[2024-01-01T00:00:00Z, 2026-08-01T00:00:00Z)
replay_evaluation=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
pairs=EURUSD GBPUSD
timeframes=M15 H1 H4 D1
planned_requests=60
```

The preceding no-network preview passed with eight streams and 60 planned requests.

## Runtime evidence

A read-only live status check at **2026-08-07 20:31:12 UTC** showed active progress:

```text
DATASET_EXISTS=YES
RAW_RESPONSES=45
METADATA_FILES=45
COMPLETED_STREAM_CSVS=4
MANIFEST_EXISTS=NO
FAILED_EXISTS=NO
LATEST_ARTIFACT=metadata/GBPUSD/M15/chunk-0014-attempt-01.json
LATEST_ARTIFACT_AGE_SEC=1
MATCHING_PROCESS_COUNT=1
```

The collector subsequently failed with:

```text
COLLECTOR_EXECUTION=FAIL
FAILED_EVIDENCE_PRESERVED=YES
ERROR_TYPE=SSLEOFError
ERROR=[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1032)
PRODUCTION_CACHE_UNCHANGED=YES
ACQUISITION_STATUS=FAIL
```

## Classification

This is a **transient transport-resilience defect in the historical collector**, not evidence of:

- invalid OANDA credentials;
- an OANDA HTTP rejection;
- corrupted candle content;
- a strategy/scoring defect;
- a production candle-cache mutation.

Before this failure, `tools/fetch_historical_candles.py` retried HTTP `429` and `5xx` responses but allowed socket/TLS exceptions from the transport layer to escape immediately. The observed `ssl.SSLEOFError` therefore terminated the entire immutable dataset acquisition after substantial successful progress.

## Corrective contract

The collector must retry transient transport exceptions under the same existing bounded policy:

```text
MAX_HTTP_ATTEMPTS=3
RETRY_BACKOFF_SECONDS=0.5
backoff=0.5,1.0
```

For a transport exception:

- no fake raw response body is created;
- redacted immutable metadata records the attempt number, exception class, and bounded message;
- the request is retried only up to the existing maximum;
- after exhaustion, acquisition still fails closed and writes `FAILED.json`;
- HTTP retry behavior remains unchanged;
- provider responses and successful attempts remain immutable.

Regression coverage must reproduce `SSLEOFError -> SSLEOFError -> 200` and prove successful recovery plus preserved exception metadata.

## Dataset disposition

Both failed dataset roots are forensic evidence and must remain preserved:

```text
data/replay/oanda-20260601-20260801-20260807/
data/replay/oanda-warmup-20240101-20260801-20260807-r2/
```

Neither is eligible for replay because neither has a complete manifest.

The next acquisition must use a new immutable dataset ID after the transport-retry fix is merged and reviewed.

## Git worktree status nuance

The acquisition wrapper printed:

```text
GIT_WORKTREE_STATUS_UNCHANGED=NO
```

That check included untracked files. Replay datasets are local artifacts under `data/replay/`, and the phone is not necessarily checked out at the same `.gitignore` state as current GitHub `main`. Therefore this line alone is **not evidence of a tracked production-file mutation**. The stronger safety evidence from the same run is:

```text
PRODUCTION_CACHE_UNCHANGED=YES
STRATEGY_MUTATION=NO
THRESHOLD_MUTATION=NO
TELEGRAM_MUTATION=NO
SERVICE_CRON_MUTATION=NO
```

Future acquisition wrappers should distinguish tracked-file changes from ignored/untracked replay artifacts.

## Production decision

```text
STRATEGY_MUTATION_ALLOWED=NO
REPLAY_ALLOWED_FROM_FAILED_DATASET=NO
NEXT_ACTION=MERGE_TRANSPORT_RETRY_FIX_THEN_ACQUIRE_NEW_IMMUTABLE_DATASET
```
