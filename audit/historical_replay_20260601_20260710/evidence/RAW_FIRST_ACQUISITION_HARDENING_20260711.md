# Raw-First Acquisition Hardening — 2026-07-11

## Scope

- [proven] This increment is confined to the historical-replay sidecar.
- [proven] No production BotA module was imported, executed, or modified.
- [proven] No live provider request was required for this increment.

## Defect

- [proven] The prior transport layer rejected non-2xx and malformed responses before orchestration could persist provider bytes.
- [proven] The prior acquisition orchestration parsed the response body before writing the raw artifact.
- [proven] A provider error or malformed response could therefore disappear without immutable raw forensic evidence.

## Repair

- [proven] `src/live_oanda.py` now performs request validation and transport only, then returns redacted request metadata, response metadata, and raw provider bytes without semantic response validation.
- [proven] `src/multi_chunk_acquisition.py` now writes raw bytes and redacted request/response metadata before HTTP-status or payload parsing.
- [proven] After persistence, non-2xx responses and malformed payloads still fail closed.
- [proven] Failed acquisitions do not write derived candles or a completed-run manifest.
- [proven] Write-once artifact behavior prevents a rejected response from being overwritten under the same run ID.

## Synthetic proof added

- [proven] Transport tests prove HTTP-error and malformed bodies are returned for raw-first persistence.
- [proven] Orchestration tests prove a 401 body and metadata are persisted before `RuntimeError`.
- [proven] Orchestration tests prove malformed body and metadata are persisted before parse failure.
- [proven] Tests assert no derived candle artifact or completed-run manifest is produced for rejected responses.
- [proven] Tests assert authorization secrets remain redacted.

## Commits

- [proven] Transport change: `e43cee25ee68ddea86a3f2bc2e567f93325442e6`.
- [proven] Orchestration change: `355b043b99f374c32ff40f16d3fc2c9ffb592b7b`.
- [proven] Transport tests: `86214515d5849bb0b1ae55943cdddcace5a06976`.
- [proven] Raw-first orchestration tests: `afe622850ff1369308ad32ca2464356b38b9f2af`.

## Current gate

- [not proven] This hardening increment is not CI-validated until GitHub Actions succeeds at or after the final commit containing these changes.
