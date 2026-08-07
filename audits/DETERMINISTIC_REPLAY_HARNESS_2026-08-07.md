# BotA Deterministic Replay Harness Audit — 2026-08-07

Recorded: **2026-08-07 23:00 UTC**

## Objective

Build the first remaining strategy-verdict phase: a deterministic, read-only historical reconstruction of the current BotA production decision rules before any ADX/RSI strategy mutation.

This is not an outcome verdict yet. It is the executable decision-replay layer that Phase 2 will run against the validated June-July historical dataset.

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
TRACKED_WORKTREE_UNCHANGED=YES
REPLAY_DATASET_ELIGIBLE=YES
```

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

## Source integrity used to design replay

Frozen production source blobs:

```text
tools/scoring_engine.sh      09c42362a5c3c679696e86d4131ce5dfabd86608
tools/m15_h1_fusion.sh       c1de0312ed928f870b9a45df109b730d30888ee7
tools/quality_filter.py       18b76f908652d483c115c930373972836cea81dc
tools/build_indicators.py     2abce4a325d6d9da8bb0958b97a651d4288e1792
tools/sr_score.py             616b996a8ce439a19483762645a2247ca96fd066
tools/market_open.sh          a73ca97f3a63c3245311585e231e5e69eaffc506
tools/emit_snapshot.py        425c9adace57956981cf7e3111fd5df504c4f1ca
```

Replay code embeds these hashes in its summary so results remain tied to the exact inspected semantics.

## Harness files

Branch:

```text
feat/deterministic-production-replay-20260807
```

Added:

```text
tools/replay_semantics.py
tools/deterministic_replay.py
tests/test_deterministic_replay.py
```

CI workflow is extended to compile and run the replay test suite together with the existing historical acquisition / dataset-verifier suites.

## Exact semantics reconstructed

The replay:

- evaluates each M15 decision at the M15 candle completion instant;
- never exposes a candle whose completion is later than the historical decision time;
- reuses the production `build_indicators.py` module for EMA9/21, RSI14, MACD histogram, ADX14, ATR14 and Bollinger calculations;
- reuses the production `quality_filter.py` module with the frozen effective `FILTER_SCORE_MIN_ALL=65`;
- reuses the production `sr_score.py` swing/merge/proximity math on historical H1 candles;
- reconstructs `market_open.sh` historical UTC market gate as Mon-Fri 07:00-20:00 UTC with session bypass disabled;
- reconstructs scoring-engine historical session points from the historical decision timestamp;
- reproduces the current 1.0 ATR pullback buffer despite the older comment mentioning 0.3 ATR;
- reproduces ADX <20 hard HOLD;
- reproduces EMA/RSI/MACD/ADX/BB/session/SR score components;
- keeps volume contribution neutral because the current production indicator bundle does not retain a `candles` volume series;
- reproduces H1 quality rejection, neutral veto/override, opposite-direction veto semantics and H4 pre-check;
- reproduces H4+D1 opposition veto with the same vote formula;
- performs no Telegram, Supabase, provider, service, cron, production-cache, cooldown or strategy mutation.

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

Current `scoring_engine.sh` does not emit a top-level `adx` field. It emits ADX in the reasons string, and the replay records `adx_raw` for analysis, but the JSON field consumed by fusion is absent.

Therefore the effective input to this particular override is `0` under the inspected production contract. The replay deliberately reproduces that behavior. It does **not** silently substitute `adx_raw`.

This is a strategy/orchestration defect candidate, but no production change is approved in this phase.

## Fidelity limits declared rather than hidden

### Network-dependent H4/D1 snapshot votes

`m15_h1_fusion.sh` obtains the final H4/D1 vote through `emit_snapshot.py`, whose original live source may be TwelveData or Yahoo and is network dependent.

A deterministic historical replay cannot query what those providers returned at each past decision instant. The baseline replay therefore applies the exact vote formula to the validated historical OANDA H4/D1 bundles and labels the result:

```text
DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

It must not be described as byte-for-byte historical provider reconstruction.

### Runtime D1 trend cache

`scoring_engine.sh` reads `cache/d1_trend_<PAIR>.json` and fails open to `ANY` if unavailable. The tracked repository inspection used for this phase did not establish a historical writer or retained historical values for that runtime cache.

Baseline replay therefore uses:

```text
d1_filter_mode=ANY
```

which is the scoring engine's fail-open behavior. An explicit EMA sensitivity mode is available separately and must not be mixed into baseline results.

## No-lookahead rule

For replay timestamp `T`, a candle is available only if:

```text
candle_start + timeframe_duration <= T
```

This prevents using an H1/H4/D1 candle that had not completed when an M15 decision would have been made.

## Required Phase-1 acceptance

Before merge:

```text
PYTHON_COMPILE=PASS
REPLAY_UNIT_TESTS=PASS
HISTORICAL_ACQUISITION_TESTS=PASS
DATASET_VERIFIER_TESTS=PASS
SECURITY_SCAN=PASS
STATIC_ANALYSIS_MATERIAL_FINDINGS=0
```

The exact final PR head must be used for all gate claims.

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

Run the harness against r3 for the fixed June-July interval, prove deterministic identical output across repeated runs, measure replay-to-known-signal reconstruction coverage, then evaluate A/B/C outcomes. That is Phase 2; no production strategy change is allowed before it completes.
