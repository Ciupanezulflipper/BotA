# Production Timeframe Contract Mapping — 2026-07-11

## Status

- [proven] This document maps the isolated historical-replay sidecar to production BotA at base commit `fa289ad3f7b6ff430f13609950e5af341aee2e9d`.
- [proven] This is a static, read-only mapping. No production module was imported or executed.
- [proven] The mapping covers `tools/data_fetch_candles.sh`, `tools/indicators_updater.sh`, `tools/m15_h1_fusion.sh`, and `tools/signal_watcher_pro.sh`.
- [not proven] Full production parity is not established.

## Production source identities

- [proven] `tools/data_fetch_candles.sh` blob SHA: `64dbcd13f3269883771b42bc5255211c9d4b7a7f`.
- [proven] `tools/indicators_updater.sh` blob SHA: `01fe34887afbb388fa7ee3e422bcdb7d65e9a9da`.
- [proven] `tools/m15_h1_fusion.sh` blob SHA: `c1de0312ed928f870b9a45df109b730d30888ee7`.
- [proven] `tools/signal_watcher_pro.sh` blob SHA: `f065476ec70627e63218796cc4621debd2d631e7`.

## Provider and candle contract

- [proven] Production OANDA requests use midpoint candles with `price=M`.
- [proven] Production maps `M15`, `H1`, `H4`, and `D1` to OANDA granularities `M15`, `H1`, `H4`, and `D` respectively.
- [proven] Production `data_fetch_candles.sh` requests `count=500` and does not use explicit `from`/`to` bounds.
- [proven] Production filters out candles whose OANDA `complete` field is false.
- [proven] Production converts provider timestamps to UTC epoch seconds and writes a Yahoo-compatible chart payload into `cache/<PAIR>_<TF>.json`.
- [proven] Production writes CSV rows using the provider candle start timestamp.
- [proven] Production validates cadence by median timestamp spacing against the requested timeframe.
- [proven] Production does not explicitly set OANDA `dailyAlignment`, `alignmentTimezone`, `weeklyAlignment`, `smooth`, or `includeFirst`; provider defaults therefore control those semantics.

## D1 contract

- [proven] The main production fetch path requests D1 as OANDA granularity `D`, `count=500`, `price=M`.
- [proven] `indicators_updater.sh` also contains a separate D1 trend refresh path using granularity `D`, `count=50`, `price=M` for EURUSD and GBPUSD.
- [proven] Both production D1 paths rely on OANDA's default alignment because neither specifies daily alignment parameters.
- [proven] The bounded live D probe observed completed daily candle starts at `21:00:00Z` during July 2026.
- [inferred] The observed `21:00:00Z` starts are compatible with the production requests because both the probe and production omit explicit alignment parameters and use the same OANDA practice endpoint family and midpoint price component.
- [proven] Sidecar `CanonicalCandle` now preserves an explicit optional `available_at` value.
- [proven] Completed normalized D1 candles without a provider-supplied close timestamp receive explicit availability at provider-aligned start plus 24 hours.
- [proven] Normalization rejects an intra-range D1 UTC alignment change instead of silently applying one period rule across a DST boundary.
- [proven] An integration test connects normalized D1 candles to `visible_candles` and proves the candle remains hidden until the explicit provider-aligned close boundary.
- [not proven] GitHub Actions validation of this D1 parity repair is pending.
- [not proven] D1 ranges crossing a provider alignment/DST transition are supported; current logic fails closed on such a transition.

## M15, H1, and H4 contract

- [proven] Production requests the native OANDA granularities directly; it does not aggregate M15 into H1 or H4.
- [proven] Production treats returned timestamps as candle start timestamps.
- [proven] Production removes incomplete candles before cache publication.
- [proven] The verified live probes returned 4 M15, 45 H1, and 12 H4 completed candles with matching raw and derived counts.
- [proven] The sidecar point-in-time implementation makes fixed-duration candles available at start plus 15 minutes, 1 hour, or 4 hours.
- [inferred] That availability rule is compatible with native completed OANDA fixed-duration candles, subject to boundary tests using the exact observed provider timestamps.
- [not proven] Exact first-candle/include-first behavior for multi-chunk full-window acquisition has not been reconciled with production's rolling `count=500` behavior.

## Updater contract

- [proven] Production updater scope defaults to pairs `EURUSD GBPUSD XAUUSD USDJPY EURJPY` and timeframes `M15 H1 H4 D1`.
- [proven] Production watcher scope is narrower and defaults to pairs `EURUSD GBPUSD` and timeframe `M15`.
- [proven] On fetch failure, the updater skips indicator rebuild and preserves staleness rather than overwriting indicators with degraded data.
- [proven] The historical replay scope of EURUSD and GBPUSD with M15/H1/H4/D1 is a subset of the production updater contract and matches the production watcher universe plus its context timeframes.

## Fusion contract

- [proven] Production fusion uses M15 as the base entry decision and H1 as confirmation/veto context.
- [proven] Production returns the M15 result immediately when M15 is rejected or not BUY/SELL; H1 is not evaluated in that path.
- [proven] Production reads H4 indicator cache as additional context for H1-neutral override logic.
- [proven] Production macro input defaults to neutral/off when `NEWS_ON` is not enabled.
- [not proven] The sidecar cycle replay currently reproduces the exact production scoring, quality-filter, H1-veto, H4-override, and macro ordering.
- [proven] Therefore sidecar cycle classifications cannot yet be called production-equivalent trading decisions.

## Watcher and freshness contract

- [proven] Production watcher authoritative freshness input is `cache/<PAIR>_<TF>.json`, not legacy cache and not indicator file mtime.
- [proven] Production fails closed when the raw cache or candle timestamp is missing or when candle age exceeds the configured ceiling.
- [proven] Production watcher defaults to `EURUSD GBPUSD` and `M15`.
- [proven] Historical replay must classify runtime opportunity only at M15 decision cycles and must expose H1/H4/D1 as context available at that cycle.
- [not proven] The sidecar has not yet reproduced the exact production freshness-age calculation against historical cycle times and runtime epochs.

## Accepted parity findings

- [proven] Pair scope matches the active production watcher universe.
- [proven] Timeframe scope matches production execution plus context timeframes.
- [proven] Provider, midpoint component, complete-candle filtering, and native granularity mappings match.
- [proven] Observed fixed-timeframe and daily timestamps are relevant to production because production relies on the same provider defaults.
- [proven] The previously identified D1 canonical-availability structural gap has been repaired in sidecar source and tests, pending CI proof.

## Blocking mismatches and incomplete mappings

1. [proven] Sidecar bounded `from`/`to` acquisition is not identical to production rolling `count=500` acquisition.
2. [not proven] Full-window chunk boundary behavior is equivalent to production cache chronology.
3. [not proven] Replay scoring/fusion ordering is equivalent to the production shell/Python pipeline.
4. [not proven] Historical freshness and runtime-outage classification is equivalent to production watcher behavior.
5. [not proven] Yahoo fallback behavior is represented in the replay; current primary forensic plan is OANDA-first with independent Dukascopy reconciliation, not Yahoo replay.
6. [not proven] The D1 availability repair passes GitHub Actions.

## Gate decision

- [proven] Provider/timeframe acquisition parity is partially established.
- [proven] D1 canonical visibility is structurally connected to provider-aligned timestamps in source and tests.
- [not proven] The D1 repair is CI-validated.
- [proven] Production-decision parity is not established.
- [proven] Full historical acquisition and final cycle conclusions remain blocked until exact replay-to-production fusion and freshness mappings are resolved or explicitly bounded as non-equivalent.
- [proven] The sidecar remains a verifier and must not be presented as a second production implementation.