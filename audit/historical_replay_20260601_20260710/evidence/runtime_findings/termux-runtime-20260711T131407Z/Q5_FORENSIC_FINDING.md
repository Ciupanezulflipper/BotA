# Q5 Signal-Pipeline Runtime Finding

## Finding

- [proven] The last located positive production watcher evidence before the long gap is `2026-06-22T17:16:01Z`.
- [proven] A preserved crontab snapshot at `2026-07-08T11:37:37Z` lacks the signal watcher, indicators updater, shadow manager, and supervisor.
- [proven] A second preserved crontab snapshot at `2026-07-08T11:41:32Z` also lacks those jobs.
- [proven] A preserved crontab snapshot at `2026-07-08T11:43:43Z` contains the restored runtime block.
- [proven] The first located positive supervisor evidence after restoration is `2026-07-08T11:45:00Z`.
- [proven] The first located positive watcher evidence after restoration is `2026-07-08T11:45:07Z`.
- [proven] Daily cron activity continued during part of the long watcher-family gap.
- [proven] Therefore this was not a complete Termux or complete `crond` outage.
- [proven] The preserved evidence establishes a partial crontab/runtime configuration failure affecting the production signal pipeline.

## Defensible boundaries

- [not proven] Continuous watcher downtime from `2026-06-22T17:16:01Z` to `2026-07-08T11:37:37Z`.
- [proven] Signal-pipeline configuration missing at the preserved snapshot instants `2026-07-08T11:37:37Z` and `2026-07-08T11:41:32Z`.
- [proven] Signal-pipeline configuration restored by `2026-07-08T11:43:43Z`.
- [proven] Watcher execution resumed by `2026-07-08T11:45:07Z`.
- [not proven] First successful indicators-updater execution after restoration.

## Classification

- [inferred] `2026-06-22T17:16:01Z` to `2026-07-08T11:37:37Z` remains runtime `UNKNOWN`.
- [proven] The two pre-restoration snapshots prove configuration failure at those exact observation instants.
- [inferred] `2026-07-08T11:43:43Z` to `2026-07-08T11:45:07Z` is a bounded recovery transition.
- [inferred] Runtime may be treated as `UP` from the first positive watcher execution, subject to candle freshness and subsequent cycle evidence.

## Scope boundary

- [proven] This finding concerns operational availability only.
- [proven] It does not determine whether any historical candle set would have generated an eligible trade.
- [proven] It does not alter strategy thresholds, scoring, fusion, risk, pair scope, or production behavior.
