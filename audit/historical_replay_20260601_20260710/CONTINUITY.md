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
- [proven] Live OANDA M15, H4, and D observations must be reconciled with production BotA fetch and replay timing semantics before final conclusions.
