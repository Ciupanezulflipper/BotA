# Replay Dataset Verifier — 2026-08-07

## Purpose

Replace disposable post-acquisition Termux verification blocks with one reusable offline verifier:

```text
tools/verify_replay_dataset.py
```

The verifier performs no network access and does not write to the replay dataset or production candle cache.

## Verification contract

Given one immutable replay dataset, expected raw range, evaluation start, pair/timeframe scope, and minimum warm-up bars, it checks:

- `manifest.json` exists and reports `status=COMPLETE`;
- `FAILED.json` does not exist;
- dataset id, provider `oanda`, midpoint price component `M`, pair scope and timeframe scope match expectations;
- manifest raw start/end exactly match the requested half-open range;
- `production_cache_touched` is explicitly false;
- every manifest artifact path stays inside the dataset root;
- every artifact exists and matches manifest byte count and SHA-256;
- the expected stream set is exact;
- every candle CSV has the canonical five-column header;
- timestamps parse, remain strictly increasing, and stay inside the raw range;
- OHLC values are finite, positive, and correctly ordered;
- CSV row count / first timestamp / last timestamp agree with stream metadata;
- every stream has at least the requested pre-evaluation warm-up count;
- every stream contains evaluation-period candles.

## Focused tests

`tests/test_verify_replay_dataset.py` covers:

1. valid dataset passes hash, CSV, scope, and warm-up checks;
2. post-manifest CSV tampering fails closed on checksum mismatch;
3. `FAILED.json` makes a dataset replay-ineligible;
4. insufficient warm-up bars fail closed.

The historical-acquisition CI workflow is extended to compile and run both acquisition and verification test suites.

## Operational effect

Future phone flow becomes:

```text
1. extract exact reviewed collector from one GitHub commit
2. acquire new immutable dataset
3. extract exact reviewed verifier from the same commit
4. verify dataset offline
5. only then build/run deterministic replay
```

This removes repeated large inline Python verification packages and makes the evidence contract versioned, reviewable, and reusable.

## Safety

```text
NETWORK_ACCESS=NO
PRODUCTION_CACHE_WRITE=NO
STRATEGY_MUTATION=NO
THRESHOLD_MUTATION=NO
TELEGRAM_MUTATION=NO
SUPABASE_MUTATION=NO
```
