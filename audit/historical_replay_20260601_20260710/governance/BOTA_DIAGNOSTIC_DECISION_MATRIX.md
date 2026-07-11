# BotA Diagnostic Decision Matrix

## Purpose

- [proven] This matrix determines whether BotA needs runtime repair, data repair, strategy investigation, or no change.
- [proven] Strategy changes are prohibited until runtime and data integrity gates pass.

## Decision sequence

### Gate 1 — Was the expected cycle operational?

- [inferred] `RUNTIME_DOWN`:
  - [inferred] action: runtime repair;
  - [inferred] strategy conclusion: prohibited;
  - [inferred] replay conclusion: cycle not evaluated.

- [inferred] `UNKNOWN`:
  - [inferred] action: preserve uncertainty and seek evidence only when it could change the decision;
  - [inferred] strategy conclusion: prohibited;
  - [inferred] replay conclusion: indeterminate.

- [inferred] `UP`:
  - [inferred] continue to Gate 2.

### Gate 2 — Was required data usable?

- [inferred] `MISSING`, `STALE`, `MALFORMED`, `LOOK_AHEAD`, or `UNRECONCILED`:
  - [inferred] action: data repair;
  - [inferred] strategy conclusion: prohibited;
  - [inferred] cycle classification: `DATA_UNUSABLE`.

- [inferred] `FRESH`, point-in-time valid, and reconciled:
  - [inferred] continue to Gate 3.

### Gate 3 — Did production-equivalent decision logic execute completely?

- [inferred] No:
  - [inferred] action: decision-pipeline repair;
  - [inferred] strategy conclusion: prohibited.

- [inferred] Yes:
  - [inferred] continue to Gate 4.

### Gate 4 — What was the decision?

- [inferred] Valid rejection with complete reasons:
  - [inferred] action: no operational repair;
  - [inferred] continue accumulating representative sample;
  - [inferred] strategy investigation allowed only after adequate sample size.

- [inferred] Eligible signal produced but notification suppressed or failed:
  - [inferred] action: delivery/deduplication repair;
  - [inferred] strategy change prohibited.

- [inferred] Eligible signal delivered correctly:
  - [inferred] action: no operational change.

### Gate 5 — Is strategy improvement justified?

- [inferred] Strategy investigation is allowed only when:
  - [inferred] runtime coverage is proven;
  - [inferred] data integrity passes;
  - [inferred] production/replay parity passes;
  - [inferred] every expected cycle has a terminal record;
  - [inferred] rejection reasons are complete;
  - [inferred] sample size is representative;
  - [inferred] proposed changes are evaluated out-of-sample.

- [inferred] If all gates pass and valid setups remain rare:
  - [inferred] action: strategy investigation.

- [inferred] If all gates pass and low signal volume is consistent with approved rules:
  - [inferred] action: no change.

## User-facing diagnosis labels

- [inferred] `RUNTIME REPAIR REQUIRED`
- [inferred] `DATA REPAIR REQUIRED`
- [inferred] `DECISION PIPELINE REPAIR REQUIRED`
- [inferred] `DELIVERY REPAIR REQUIRED`
- [inferred] `STRATEGY INVESTIGATION ALLOWED`
- [inferred] `NO CHANGE REQUIRED`
- [inferred] `INSUFFICIENT EVIDENCE`

## Current forensic diagnosis

- [proven] A partial runtime configuration failure occurred.
- [proven] Runtime repair safeguards are required.
- [not proven] Full historical data integrity is complete.
- [not proven] Exact production/replay parity is complete.
- [not proven] Strategy improvement is currently justified.
- [inferred] Current diagnosis: `RUNTIME REPAIR REQUIRED`.
- [inferred] Secondary diagnosis: `INSUFFICIENT EVIDENCE` for strategy conclusions.
