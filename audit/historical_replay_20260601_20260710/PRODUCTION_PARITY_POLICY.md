# Production-Parity Binding Policy

## Governing rule

- [proven] The historical-replay sidecar is an isolated verifier for BotA production behavior; it is not a second BotA and must not evolve into an independent strategy or runtime implementation.
- [proven] A sidecar increment is not complete merely because it works inside the sidecar.
- [proven] Every sidecar increment must be mapped to the corresponding production BotA file, runtime behavior, data contract, provider behavior, timeframe alignment, or preserved operational evidence.
- [proven] Any mismatch between sidecar and production must be recorded explicitly and must fail closed.
- [proven] Silent adaptation of the sidecar to produce convenient replay results is prohibited.
- [proven] Merge readiness requires demonstrated production parity for every replay-critical contract used in final conclusions.

## Mandatory acceptance gates

For every new replay component or conclusion:

1. [proven] Identify the exact production dependency being represented.
2. [proven] Record the production file, runtime behavior, data contract, provider setting, or preserved evidence that defines the reference behavior.
3. [proven] Verify the sidecar behavior against that production reference.
4. [proven] Record mismatches as unresolved rather than normalizing them away.
5. [proven] Preserve the mapping and verification evidence in repository state.
6. [proven] Refuse completion, merge readiness, and final historical conclusions while the connection remains unproven.

## Current application

- [proven] The isolated worktree is a safety boundary for forensic acquisition and replay execution.
- [proven] Production BotA remains at `/data/data/com.termux/files/home/BotA`.
- [proven] The audit worktree remains at `/data/data/com.termux/files/home/bota-worktrees/historical-replay`.
- [proven] Live OANDA M15, H4, and D probes are provider-contract evidence that must be reconciled with BotA production fetch behavior and replay timing semantics.
- [not proven] Full equivalence between the sidecar and BotA production semantics is not yet established.
- [not proven] The sidecar is not merge-ready and must remain a draft PR until parity gates, full acquisition, cycle conclusions, state preservation, and handoff verification are complete.

## Scope lock

- [proven] This policy does not authorize changes to strategy, score thresholds, ADX gates, H1 veto logic, pair scope, risk/reward rules, Telegram behavior, Supabase behavior, cron, or production runtime.
- [proven] Any such change requires separate explicit approval.
