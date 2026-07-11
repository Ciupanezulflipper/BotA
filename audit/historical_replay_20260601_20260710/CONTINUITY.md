# Historical Replay Continuity

## 2026-07-11 — Production-parity binding

- [proven] The historical-replay sidecar is an isolated verifier for BotA production behavior; it is not a second BotA.
- [proven] No sidecar increment is complete merely because it works inside the sidecar.
- [proven] Every increment must identify and map to the corresponding production BotA file, runtime behavior, data contract, provider behavior, timeframe alignment, or preserved operational evidence.
- [proven] Any mismatch between sidecar and production must be recorded explicitly and must fail closed.
- [proven] Silent adaptation of sidecar behavior to produce convenient replay results is prohibited.
- [proven] Merge readiness requires demonstrated production parity for every replay-critical contract used in final conclusions.
- [proven] The mandatory acceptance gates are defined in `PRODUCTION_PARITY_POLICY.md`.
- [not proven] Full production equivalence has not yet been established.
- [not proven] The sidecar is not merge-ready.

## Required acceptance sequence

1. [proven] Identify the production dependency represented by the increment.
2. [proven] Record the production reference file, contract, behavior, setting, or preserved evidence.
3. [proven] Verify sidecar behavior against that reference.
4. [proven] Preserve mismatches as unresolved rather than normalizing them away.
5. [proven] Preserve the mapping and verification evidence in repository state.
6. [proven] Refuse completion and merge readiness while the production connection remains unproven.

## Current boundary

- [proven] Production BotA remains at `/data/data/com.termux/files/home/BotA`.
- [proven] The audit worktree remains at `/data/data/com.termux/files/home/bota-worktrees/historical-replay`.
- [proven] The isolated worktree is a forensic safety boundary, not an independent implementation target.
- [proven] Live OANDA M15, H1, H4, and D observations must be reconciled with production BotA fetch and replay timing semantics before final conclusions.

## 2026-07-11 — Verified bounded OANDA probes

- [proven] EUR_USD M15 bounded read-only probe completed and was verified offline.
- [proven] EUR_USD H1 bounded read-only probe completed and was verified offline.
- [proven] EUR_USD H4 bounded read-only probe completed and was verified offline.
- [proven] EUR_USD D bounded read-only probe completed and was verified offline.
- [proven] H1 run ID `oanda-probe-eurusd-h1-20260711-v1` returned HTTP 200, 45 raw candles, 45 derived candles, and zero incomplete candles.
- [proven] H1 observed interval was `2026-07-09T00:00:00Z` through `2026-07-10T20:00:00Z`.
- [proven] H1 artifact hashes and production-parity caveat are preserved in `evidence/LIVE_OANDA_H1_PROBE_VERIFIED_20260711.md`.

## 2026-07-11 — Static production timeframe mapping

- [proven] Production contracts were inspected read-only at base commit `fa289ad3f7b6ff430f13609950e5af341aee2e9d`.
- [proven] Mapped production files are `tools/data_fetch_candles.sh`, `tools/indicators_updater.sh`, `tools/m15_h1_fusion.sh`, and `tools/signal_watcher_pro.sh`.
- [proven] Production and sidecar match on active pair scope, execution/context timeframe scope, OANDA midpoint component, complete-candle filtering, and native M15/H1/H4/D granularity use.
- [proven] Production uses rolling `count=500` acquisition, while the sidecar probe/acquisition contract uses explicit `from`/`to` bounds.
- [proven] Production relies on OANDA default D1 alignment, and the live D probe observed July 2026 daily starts at `21:00:00Z`.
- [proven] The prior D1 `available_at` structural gap was repaired in `CanonicalCandle` with fail-closed provider-alignment validation and point-in-time integration proof.
- [not proven] Sidecar replay scoring, quality filtering, H1 veto, H4 override, macro ordering, and runtime-outage classification are production-equivalent.
- [proven] Detailed mapping and blockers are preserved in `evidence/PRODUCTION_TIMEFRAME_CONTRACT_MAPPING_20260711.md`.

## 2026-07-11 — Raw-first acquisition hardening

- [proven] OANDA transport now returns unvalidated response bytes and redacted metadata to orchestration.
- [proven] Acquisition orchestration writes immutable raw bytes and request/response metadata before HTTP or payload validation.
- [proven] Non-2xx and malformed responses remain fail-closed after evidence persistence.
- [proven] Rejected responses do not produce derived candles or a completed-run manifest.
- [proven] Synthetic tests cover 401 and malformed response persistence, secret redaction, and absence of false completion artifacts.
- [proven] Detailed evidence is preserved in `evidence/RAW_FIRST_ACQUISITION_HARDENING_20260711.md`.
- [proven] Raw-first hardening passed Historical replay sidecar and Security Scan workflows at commit `056c3ad8e10b1c48d5cc87e1401e12fddea730a9`.

## 2026-07-11 — Production watcher freshness parity

- [proven] Production watcher freshness semantics were mapped from `tools/signal_watcher_pro.sh` at base commit `fa289ad3f7b6ff430f13609950e5af341aee2e9d`.
- [proven] Raw-cache last candle timestamp is authoritative; indicator mtime is non-authoritative.
- [proven] Trusted server time is mandatory and unavailable trusted time fails closed.
- [proven] Missing, invalid, future, or non-monotonic candle timestamps fail closed.
- [proven] The production stale boundary is strict: `age > CANDLE_MAX_AGE_SECS`; exact equality remains fresh.
- [proven] `src/watcher_freshness.py` now models this gate without importing or invoking production code.
- [proven] Synthetic tests cover exact ceiling, one-second-over, missing clock, missing timestamp, future timestamp, latest-start selection, monotonicity, and timezone awareness.
- [proven] Detailed evidence is preserved in `evidence/PRODUCTION_WATCHER_FRESHNESS_PARITY_20260711.md`.
- [proven] Watcher-freshness parity passed Historical replay sidecar and Security Scan workflows at commit `4888275495e8f6444100c5a2bedef4f214c5ee24`.

## 2026-07-11 — Runtime epoch and cycle operability contract

- [proven] `src/runtime_epochs.py` defines explicit half-open `UP`, `DOWN`, and `UNKNOWN` runtime evidence intervals.
- [proven] An uncovered cycle resolves to `UNKNOWN`; absence of evidence never defaults to watcher availability or outage.
- [proven] Epoch overlap, invalid ranges, timezone-naive values, and empty evidence identifiers fail closed.
- [proven] `src/cycle_operability.py` combines runtime state with the production-equivalent raw-cache freshness decision.
- [proven] Only runtime `UP` plus freshness `FRESH` resolves to `OPERABLE`.
- [proven] Runtime `DOWN` takes precedence over candle freshness, and runtime `UNKNOWN` remains not proven even when data is fresh.
- [proven] Runtime and freshness evidence must refer to the exact same cycle instant.
- [proven] Synthetic tests cover runtime boundaries, evidence gaps, overlap rejection, and the complete runtime/freshness operability matrix.
- [proven] Detailed evidence is preserved in `evidence/RUNTIME_EPOCH_OPERABILITY_CONTRACT_20260711.md`.
- [not proven] Exact historical watcher `UP` and `DOWN` epochs have not yet been reconstructed from preserved runtime logs.

## Remaining gates

- [not proven] Exact semantic equivalence between sidecar replay scoring/fusion and production BotA.
- [not proven] Full-window acquisition for EURUSD and GBPUSD.
- [not proven] Independent Dukascopy acquisition and provider reconciliation.
- [not proven] Runtime outage boundaries and cycle-level final conclusions.
- [not proven] Root closure files and `handoff_pack.sh` output verification.
