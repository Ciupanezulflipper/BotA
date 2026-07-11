# Runtime Evidence Ingestion Contract — 2026-07-11

## Status

- [proven] The runtime-epoch model previously accepted in-memory epochs but had no repository-defined loader for preserved evidence documents.
- [proven] `src/runtime_evidence.py` now provides a fail-closed JSON ingestion contract.
- [proven] This increment does not claim any historical BotA outage boundary.
- [proven] This increment does not infer runtime state from missing logs, market-data availability, repository commits, or later recovery evidence.

## Required document fields

- [proven] `schema_version` must equal `1`.
- [proven] `window_start_utc` and `window_end_utc` must be timezone-aware ISO-8601 timestamps with `start < end`.
- [proven] `source_commit` must be non-empty.
- [proven] `evidence_files` must be a non-empty, duplicate-free list of preserved source identifiers or paths.
- [proven] `epochs` must be a list; it may be empty when no runtime interval has yet been proven.

## Epoch rules

- [proven] Each epoch must contain `start_utc`, `end_utc`, `state`, and `evidence_id`.
- [proven] Allowed states are exactly `UP`, `DOWN`, and `UNKNOWN`.
- [proven] Epochs must be half-open, ordered, non-overlapping, and contained inside the declared investigation window.
- [proven] Every `evidence_id` must be non-empty and unique within the document.
- [proven] Uncovered time remains unresolved by `runtime_epochs.resolve_runtime_state`; the loader does not fill gaps.

## Tests

- [proven] Tests cover valid explicit epochs, empty epoch lists with preserved provenance, out-of-window epochs, overlap, duplicate evidence identifiers, unsupported states, naive timestamps, unsupported schema versions, valid UTF-8 JSON loading, and malformed JSON rejection.

## Boundary

- [not proven] Actual watcher/cron `UP` or `DOWN` intervals for 2026-06-01 through 2026-07-11 remain unreconstructed.
- [proven] The next evidence step must collect preserved logs or other direct runtime artifacts and translate only supported intervals into this schema.
- [proven] Absence of a log line is not sufficient proof of runtime `DOWN`.
