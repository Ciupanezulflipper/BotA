# BotA Deterministic Replay Harness Audit — 2026-08-07

Recorded: **2026-08-07 23:15 UTC**

## Objective

Build the first remaining strategy-verdict phase: a deterministic, read-only historical reconstruction of current BotA production decision rules before any ADX/RSI strategy mutation.

This is not an outcome verdict. It is the executable decision-replay layer that Phase 2 will run against the validated June-July historical dataset.

## Historical dataset gate — passed

The third immutable acquisition succeeded after the provider-alignment and transport-retry collector fixes.

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
RAW_RANGE=[2024-01-01T00:00:00Z, 2026-08-01T00:00:00Z)
EVALUATION_RANGE=[2026-06-01T00:00:00Z, 2026-08-01T00:00:00Z)
COLLECTOR_EXECUTION=PASS
VERIFIER_STATUS=PASS
MANIFEST_STATUS=COMPLETE
STREAM_COUNT=8
ARTIFACT_COUNT=128
ARTIFACT_HASH_FAILURES=0
OFFLINE_VERIFICATION=PASS
PRODUCTION_CACHE_UNCHANGED=YES
ACQUISITION_TRACKED_DIFF_UNCHANGED=YES
REPLAY_DATASET_ELIGIBLE=YES
```

`ACQUISITION_TRACKED_DIFF_UNCHANGED=YES` is scoped only to the phone acquisition command: the wrapper hashed the tracked staged+unstaged diff before and after the run and found it identical. The r3 wrapper did not re-print the phone Git revision, so no unobserved before/after revision is invented here.

Verified per-stream rows / pre-evaluation warm-up / evaluation rows:

```text
EURUSD D1  rows=670   warmup=626   evaluation=44
EURUSD H1  rows=16078 warmup=15001 evaluation=1077
EURUSD H4  rows=4020  warmup=3751  evaluation=269
EURUSD M15 rows=64309 warmup=60001 evaluation=4308
GBPUSD D1  rows=670   warmup=626   evaluation=44
GBPUSD H1  rows=16078 warmup=15001 evaluation=1077
GBPUSD H4  rows=4020  warmup=3751  evaluation=269
GBPUSD M15 rows=64306 warmup=59998 evaluation=4308
```

All provider requests completed on the first HTTP attempt in the successful r3 run.

### Dataset byte identity at replay time

The original r3 terminal proof verified every manifest artifact SHA-256 but did not print a SHA-256 of `manifest.json` itself. The dataset exists only on the phone and is intentionally not committed to GitHub, so this audit does not fabricate a digest that was never observed.

The Phase-1 replay runner now closes that provenance gap automatically. Before any replay decisions are used, it:

1. runs the canonical offline dataset verifier;
2. computes SHA-256 over the exact `manifest.json` bytes from r3;
3. records that value as `dataset_manifest_sha256` in the deterministic replay summary.

Therefore Phase 2 must expose and persist:

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
DATASET_MANIFEST_SHA256=<computed from exact verified phone manifest bytes>
```

That digest binds the replay result to a manifest which in turn contains byte-size/SHA-256 records for the dataset artifacts.

## Source integrity used to design replay

Frozen production Git blob SHA-1 values:

```text
tools/scoring_engine.sh      09c42362a5c3c679696e86d4131ce5dfabd86608
tools/m15_h1_fusion.sh       c1de0312ed928f870b9a45df109b730d30888ee7
tools/quality_filter.py       18b76f908652d483c115c930373972836cea81dc
tools/build_indicators.py     2abce4a325d6d9da8bb0958b97a651d4288e1792
tools/sr_score.py             616b996a8ce439a19483762645a2247ca96fd066
tools/market_open.sh          a73ca97f3a63c3245311585e231e5e69eaffc506
tools/emit_snapshot.py        425c9adace57956981cf7e3111fd5df504c4f1ca
```

The runner does not merely print these literals. It computes Git blob SHA-1 for every pinned file under `--source-root`, fails before replay on any mismatch, and records both expected and observed maps in the summary:

```text
production_source_hash_algorithm=git_blob_sha1
production_source_blobs=<expected map>
observed_production_source_blobs=<computed map>
```

CI path filters also include every pinned dependency, so changes to scoring/fusion/indicator/filter/SR/market/snapshot sources trigger replay regression tests.

## Harness files

PR #64 branch:

```text
feat/deterministic-production-replay-20260807
```

Added:

```text
tools/replay_semantics.py
tools/deterministic_replay.py
tests/test_deterministic_replay.py
```

Modified:

```text
.github/workflows/historical-candle-acquisition.yml
CONTINUITY_CURRENT.md
audits/HISTORICAL_CANDLE_ACQUISITION_2026-08-07.md
```

## Exact semantics reconstructed

The replay:

- evaluates each M15 decision at M15 candle completion;
- never exposes a candle whose completion is later than the historical decision time;
- reuses production `build_indicators.py` for EMA9/21, RSI14, MACD histogram, ADX14, ATR14 and Bollinger math;
- reuses production `quality_filter.py` with frozen effective `FILTER_SCORE_MIN_ALL=65` and all quality-filter environment inputs relevant to the path;
- reuses production `sr_score.py` swing/merge/proximity math on historical H1 candles;
- reconstructs `market_open.sh` historical UTC gate as Mon-Fri 07:00-20:00 UTC with session bypass disabled;
- reconstructs scoring-engine historical session points from the historical decision timestamp;
- reproduces the current 1.0 ATR pullback buffer despite the older comment mentioning 0.3 ATR;
- reproduces ADX <20 hard HOLD;
- reproduces EMA/RSI/MACD/ADX/BB/session/SR score components;
- keeps volume contribution neutral because the current production indicator bundle does not retain a `candles` volume series;
- reproduces H1 quality rejection, neutral veto/override, opposite-direction veto semantics and H4 pre-check;
- reproduces H4+D1 opposition veto with the same vote formula;
- emits stable full-shaped synthetic rows for market-closed replay timestamps so downstream tabular analysis does not depend on rejection mix;
- performs no Telegram, Supabase, provider, service, cron, production-cache, cooldown or strategy mutation.

### Preserved production quirk: ADX-block volatility field

Current `scoring_engine.sh` explicitly emits numeric `volatility: 0.0` on the ADX<20 hard-HOLD branch even though other branches normally use string volatility buckets. The replay preserves that live contract instead of silently normalizing it. A regression test locks this behavior.

## Frozen candidate policies

Policies are encoded before viewing June-July replay outcomes:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI
```

Extreme RSI remains the definition fixed by the March audit:

```text
SELL extreme: RSI <=30
BUY  extreme: RSI >=70
```

## New live-code finding — H1 opposite override ADX input

Current fusion code reads:

```text
m15_adx = .adx // 0
```

for the H1-opposite override.

Current `scoring_engine.sh` does not emit a top-level `adx` field. It emits ADX in the reasons string; later observability fields expose raw ADX, but the JSON field consumed by fusion is absent.

Therefore the effective input to this particular override is `0` under the inspected production contract. The replay deliberately reproduces that behavior and does **not** silently substitute `adx_raw`.

This is a strategy/orchestration defect candidate. No production change is approved in Phase 1.

## Fidelity limits declared rather than hidden

### Network-dependent H4/D1 snapshot votes

`m15_h1_fusion.sh` obtains the final H4/D1 vote through `emit_snapshot.py`, whose live source may be TwelveData or Yahoo and is network-dependent.

A deterministic historical replay cannot query what those providers returned at each past decision instant. Baseline replay applies the exact vote formula to the validated historical OANDA H4/D1 bundles and labels the result:

```text
DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

It must not be described as byte-for-byte historical provider reconstruction.

### Runtime D1 trend cache

`scoring_engine.sh` reads `cache/d1_trend_<PAIR>.json` and fails open to `ANY` if unavailable. Tracked repository inspection did not establish a historical writer or retained historical values for that runtime cache.

Baseline replay therefore uses:

```text
d1_filter_mode=ANY
```

which is the scoring engine's fail-open behavior. Explicit EMA sensitivity mode is separate and must not be mixed into baseline results.

## No-lookahead rule

For replay timestamp `T`, a candle is available only if:

```text
candle_start + timeframe_duration <= T
```

This prevents using an H1/H4/D1 candle that had not completed when an M15 decision would have been made.

## Phase-1 analyzer history

Intermediate PR head `d83700d84f8be666a6a3a050d7c9f682c830bf91` had functional/security CI green but was intentionally not merged because static analysis found replay-code complexity issues:

```text
HISTORICAL_ACQUISITION_AND_REPLAY_CI=PASS
SECURITY_SCAN=PASS
DEEPSOURCE_PYTHON=FAIL
SONAR_NEW_ISSUES=10
```

The affected replay-only functions were refactored into smaller pure helpers. Additional review findings led to executable source-blob validation, dependency-triggered CI, stable market-closed row schema, and replay-time dataset-manifest SHA-256 capture.

## Required Phase-1 acceptance

Before merge, the exact final PR head must prove:

```text
PYTHON_COMPILE=PASS
REPLAY_UNIT_TESTS=PASS
HISTORICAL_ACQUISITION_TESTS=PASS
DATASET_VERIFIER_TESTS=PASS
SECURITY_SCAN=PASS
DEEPSOURCE_PYTHON=PASS
DEEPSOURCE_SHELL=PASS
DEEPSOURCE_SECRETS=PASS
SONAR_QUALITY_GATE=PASS
SONAR_NEW_MATERIAL_ISSUES=0
```

The final PR head SHA cannot be embedded in the same commit whose SHA it would identify: changing this file would create a different SHA. The immutable final head and workflow run IDs are therefore authoritative in PR #64/GitHub check metadata and must be copied into canonical continuity after merge. No gate claim may be made against an earlier head.

## Scope lock remains

```text
STRATEGY_MUTATION=NO
ADX_RULE_MUTATION=NO
RSI_RULE_MUTATION=NO
H1_OVERRIDE_FIX=NO
PAIR_LIST_MUTATION=NO
COOLDOWN_MUTATION=NO
TELEGRAM_MUTATION=NO
SUPABASE_MUTATION=NO
```

## Next phase after merge

Run the exact merged harness against r3 for the fixed June-July interval twice. Require:

```text
RUN1_EVENTS_SHA256 == RUN2_EVENTS_SHA256
RUN1_SUMMARY_CORE == RUN2_SUMMARY_CORE
EXPECTED_PRODUCTION_SOURCE_BLOBS == OBSERVED_PRODUCTION_SOURCE_BLOBS
DATASET_MANIFEST_SHA256_PRESENT=YES
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
```

Then measure replay-to-known-signal reconstruction coverage and evaluate A/B/C outcomes. That is Phase 2; no production strategy change is allowed before it completes.
