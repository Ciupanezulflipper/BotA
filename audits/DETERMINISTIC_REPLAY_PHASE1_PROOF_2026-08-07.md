# BotA Deterministic Replay Phase-1 Proof — 2026-08-07

Recorded: **2026-08-07 23:25 UTC**

## Verdict

Phase 1 — deterministic production-rule replay harness — is complete and merged.

```text
PHASE=1_DETERMINISTIC_REPLAY_HARNESS
STATUS=PASS_MERGED
PR=64
FINAL_PR_HEAD=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8
MERGE_COMMIT=6b437179cc58021aa358b1d0b04c121d9304c660
MAIN_AFTER_MERGE=6b437179cc58021aa358b1d0b04c121d9304c660
```

The merge used `expected_head_sha=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8`, so GitHub would have rejected the merge if the reviewed head had moved.

## Exact final-head gates

All material gates below refer to the same immutable PR head:

```text
HEAD=ff77b2cc05b4c0bffe0ac13893ae6431264e08d8
```

GitHub Actions:

```text
HISTORICAL_AND_REPLAY_CI=PASS
WORKFLOW_RUN_NUMBER=39
WORKFLOW_RUN_ID=31226834369

SECURITY_SCAN=PASS
WORKFLOW_RUN_NUMBER=1065
WORKFLOW_RUN_ID=31226834370
```

Static/review services on that head:

```text
DEEPSOURCE_PYTHON=PASS
DEEPSOURCE_SHELL=PASS
DEEPSOURCE_SECRETS=PASS
CODERABBIT=SUCCESS
```

SonarCloud:

```text
SONAR_CHECK_ID=93022819471
SONAR_STATUS=COMPLETED
SONAR_CONCLUSION=SUCCESS
SONAR_QUALITY_GATE=PASS
SONAR_NEW_ISSUES=0
SONAR_SECURITY_HOTSPOTS=0
SONAR_STARTED_AT=2026-08-07T23:20:42Z
SONAR_COMPLETED_AT=2026-08-07T23:21:13Z
```

## Final diff proof

Immediately before merge, GitHub compare reported:

```text
BASE=main
HEAD=feat/deterministic-production-replay-20260807
STATUS=ahead
AHEAD_BY=16
BEHIND_BY=0
CHANGED_FILES=7
```

Exact files:

```text
.github/workflows/historical-candle-acquisition.yml
CONTINUITY_CURRENT.md
audits/DETERMINISTIC_REPLAY_HARNESS_2026-08-07.md
audits/HISTORICAL_CANDLE_ACQUISITION_2026-08-07.md
tests/test_deterministic_replay.py
tools/deterministic_replay.py
tools/replay_semantics.py
```

No production strategy file, score configuration, pair universe, Telegram, Supabase, service, cron or cooldown file was modified by Phase 1.

## Review findings disposition

The branch was intentionally not merged while intermediate analyzer heads were red. Important findings were fixed before the final head:

- replay complexity was split into smaller pure helpers;
- Git source provenance moved from literal-only reporting to executable validation of the actual pinned source files;
- direct Python SHA-1 use was removed; Git blob object IDs are obtained through Git itself;
- Git executable resolution is absolute before subprocess execution;
- CI path filters include all replay dependencies;
- market-closed rows use stable full event schema;
- market-closed rejection label is explicit;
- the replay summary records SHA-256 of the exact phone dataset manifest;
- all final review threads were resolved before merge.

One review suggestion was deliberately not adopted: normalizing ADX-block `volatility` to a string. Pinned production `tools/scoring_engine.sh` emits numeric `0.0` on ADX<20. Replay preserves that exact production quirk and has regression coverage for it.

## Pinned production semantics

Replay source provenance is tied to these production Git blob object IDs:

```text
tools/scoring_engine.sh      09c42362a5c3c679696e86d4131ce5dfabd86608
tools/m15_h1_fusion.sh       c1de0312ed928f870b9a45df109b730d30888ee7
tools/quality_filter.py       18b76f908652d483c115c930373972836cea81dc
tools/build_indicators.py     2abce4a325d6d9da8bb0958b97a651d4288e1792
tools/sr_score.py             616b996a8ce439a19483762645a2247ca96fd066
tools/market_open.sh          a73ca97f3a63c3245311585e231e5e69eaffc506
tools/emit_snapshot.py        425c9adace57956981cf7e3111fd5df504c4f1ca
```

At runtime, `tools/deterministic_replay.py` uses `git hash-object --no-filters` through an absolute resolved Git executable and fails before replay if any observed source object ID differs from the pinned map.

## Canonical dataset for Phase 2

```text
DATASET_ID=oanda-warmup-20240101-20260801-20260807-r3
RAW_RANGE=[2024-01-01T00:00:00Z,2026-08-01T00:00:00Z)
EVALUATION_RANGE=[2026-06-01T00:00:00Z,2026-08-01T00:00:00Z)
REPLAY_DATASET_ELIGIBLE=YES
```

The runner re-runs the canonical offline dataset verifier and records SHA-256 of the exact `manifest.json` bytes as `dataset_manifest_sha256` before the replay output is accepted.

## Fidelity declaration

The harness is intentionally labeled:

```text
DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION
```

It is not claimed to reproduce unrecoverable historical network responses byte-for-byte. The exact H4/D1 vote formula is applied to the verified OANDA historical bundles because historical TwelveData/Yahoo responses used by `emit_snapshot.py` were not retained.

The historical runtime `cache/d1_trend_<PAIR>.json` values are also not established. Baseline replay therefore uses the production scoring engine's fail-open `ANY` behavior. EMA D1 is sensitivity-only, not baseline.

## New live-code finding preserved for later decision

Current `m15_h1_fusion.sh` reads top-level:

```text
.adx // 0
```

for the H1-opposite override, but current `scoring_engine.sh` does not emit top-level `adx`. Under the inspected production contract this override receives `0`, so the intended `ADX>=40` opposite-trend override cannot activate as written.

Phase 1 reproduces this behavior; it does not fix production.

## Frozen Phase-2 policies

The policies were frozen before full June-July replay results are observed:

```text
A = current production acceptance
B = A AND score >=70 AND ADX <30
C = B AND no extreme RSI

SELL extreme RSI <=30
BUY  extreme RSI >=70
```

## Exactly one next action

Run the merged deterministic harness twice against canonical r3 and require identical event output hashes before interpreting strategy results:

```text
RUN1_EVENTS_SHA256 == RUN2_EVENTS_SHA256
EXPECTED_SOURCE_BLOBS == OBSERVED_SOURCE_BLOBS
DATASET_MANIFEST_SHA256_PRESENT=YES
PRODUCTION_CACHE_UNCHANGED=YES
TRACKED_WORKTREE_UNCHANGED=YES
```

Only after determinism passes should Phase 2 compare replay reconstruction to known published signals and evaluate A/B/C outcomes.

```text
PRODUCTION_STRATEGY_MUTATION=NO
```
