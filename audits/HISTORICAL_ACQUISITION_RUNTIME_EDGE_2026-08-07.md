# Historical Acquisition Runtime Edge — 2026-08-07

Recorded phone evidence: **2026-08-07 20:10:49 UTC**

## Attempt

The first credential-gated immutable OANDA acquisition was launched for:

```text
dataset-id=oanda-20260601-20260801-20260807
range=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
pairs=EURUSD GBPUSD
timeframes=M15 H1 H4 D1
planned_requests=10
```

Preview had already passed with `NETWORK_PERMITTED=False`, eight streams, and zero production mutation.

## Verified runtime failure

The real read-only provider GET sequence failed closed on EURUSD H4:

```text
ERROR_TYPE=ValueError
ERROR=OANDA returned candle outside requested chunk for EURUSD H4: 2026-05-31T21:00:00Z
COLLECTOR_EXECUTION=FAIL
FAILED_EVIDENCE_PRESERVED=YES
```

The live production candle-cache SHA before the attempt was:

```text
8d407d175e23929dd3ff2c898ee994670ca1057a2dfdfd0c3c61acc91fbb0847
```

No strategy, threshold, Telegram, service, cron, or order mutation occurred.

## Root cause classification

This is an acquisition-validator edge, not a trading-strategy defect and not an OANDA authentication/network failure.

OANDA returned one provider-aligned H4 candle beginning at `2026-05-31T21:00:00Z` for a request whose `from` was `2026-06-01T00:00:00Z`. The returned candle begins before `from` but overlaps it in H4 time. The original collector rejected every candle start earlier than the literal request timestamp.

The corrected contract is fail-closed but alignment-aware:

- allow at most one leading candle whose interval overlaps the requested `from`;
- reject more than one leading candle;
- reject a leading candle whose interval ends at or before `from`;
- continue rejecting any candle starting after the explicit request `to`;
- keep the raw provider response immutable;
- final dataset output remains filtered to the requested half-open range;
- record the count of accepted provider-alignment overlaps in each stream manifest.

Regression coverage reproduces the observed H4 start exactly: `2026-05-31T21:00:00Z` against `from=2026-06-01T00:00:00Z`.

## Second issue caught before rerun: indicator warm-up

The initial raw-data range beginning exactly on 2026-06-01 is insufficient for a production-semantics replay at the start of June.

`tools/build_indicators.py` currently uses:

```text
SAFE_WINDOW=500
min_bars=60
validate_tf window=200
EMA9 / EMA21
RSI14
MACD 12/26/9
ADX14
ATR14
BB20
```

For deterministic replay, the dataset must contain enough pre-June candles for the rolling production indicator state. A raw acquisition start of **2024-01-01T00:00:00Z** is selected as a simple uniform pre-roll across M15/H1/H4/D1; the replay evaluation window remains 2026-06-01 through 2026-08-01.

This intentionally favors a slightly larger immutable dataset over fragile per-timeframe warm-up arithmetic.

## Immutable failure evidence

Do not delete or reuse:

```text
data/replay/oanda-20260601-20260801-20260807/
```

It is a failed immutable attempt and contains provider evidence plus `FAILED.json`.

The next successful attempt must use a new dataset ID after the alignment fix is merged and previewed.

Proposed next dataset:

```text
dataset-id=oanda-warmup-20240101-20260801-20260807-r2
raw-range=[2024-01-01T00:00:00Z, 2026-08-01T00:00:00Z)
replay-evaluation=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
pairs=EURUSD GBPUSD
timeframes=M15 H1 H4 D1
```

## Production mutation status

```text
STRATEGY_CHANGED=NO
THRESHOLDS_CHANGED=NO
PAIR_UNIVERSE_CHANGED=NO
TELEGRAM_CHANGED=NO
SERVICE_OR_CRON_CHANGED=NO
PRODUCTION_CANDLE_CACHE_CHANGED_BY_COLLECTOR=NO
FAILED_DATASET_PRESERVED=YES
```
