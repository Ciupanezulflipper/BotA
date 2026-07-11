# Runtime Epoch and Cycle Operability Contract — 2026-07-11

## Status

- [proven] This increment defines how preserved watcher-runtime evidence is combined with the production-equivalent raw-cache freshness gate.
- [proven] No historical outage boundary is invented by this implementation.
- [proven] Absence of a preserved runtime epoch resolves to `UNKNOWN`, never silently to watcher `UP` or `DOWN`.
- [proven] Runtime epochs are explicit half-open intervals: `start_utc <= cycle_utc < end_utc`.
- [proven] Every non-unknown epoch requires a non-empty evidence identifier.

## Runtime states

- [proven] `UP` means preserved evidence proves the watcher was available for execution during the interval.
- [proven] `DOWN` means preserved evidence proves the watcher was unavailable during the interval.
- [proven] `UNKNOWN` means the available evidence cannot prove either state.
- [proven] Overlapping epochs are rejected fail closed.
- [proven] Timezone-naive, zero-length, reversed, or evidence-free epochs are rejected.

## Cycle operability matrix

- [proven] Runtime `UP` plus freshness `FRESH` resolves to `OPERABLE`.
- [proven] Runtime `UP` plus freshness `STALE` or `MISSING` resolves to `DATA_UNUSABLE`.
- [proven] Runtime `DOWN` resolves to `RUNTIME_DOWN` regardless of candle freshness.
- [proven] Runtime `UNKNOWN` remains `UNKNOWN` even if candle data is fresh.
- [proven] Runtime and freshness evidence must refer to the exact same cycle instant.

## Production connection

- [proven] Production watcher freshness is evaluated before fusion from the latest timestamp in `cache/<PAIR>_<TF>.json` using trusted server UTC.
- [proven] Production skips the cycle when raw-cache time is missing, in the future, or older than `CANDLE_MAX_AGE_SECS`.
- [proven] This increment preserves runtime availability as a separate evidence dimension and does not reinterpret absence of a decision record as a strategy rejection.
- [proven] This is an isolated verifier contract, not a second watcher implementation.

## Tests

- [proven] Runtime tests cover half-open boundaries, `UP`, `DOWN`, explicit `UNKNOWN`, uncovered cycles, overlapping epochs, ordering errors, timezone-naive values, invalid ranges, and empty evidence identifiers.
- [proven] Operability tests cover the full runtime/freshness matrix and reject mismatched cycle instants.

## Remaining boundary

- [not proven] Exact BotA watcher `UP` and `DOWN` epochs for the full investigation period are not yet reconstructed.
- [not proven] No cycle may be classified as operationally missed until its runtime epoch is proven `UP`, its data is proven usable, and the absence or presence of a decision record is evaluated separately.
