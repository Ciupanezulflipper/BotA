# Acquisition Dry-Run Validation — 2026-07-10

[proven] GitHub Actions workflow `Historical replay sidecar` run `29130768736` completed successfully for commit `fb17172202ff95d5be99cdbb0b3e54d784e1ac31`.

[proven] The dedicated `synthetic-validation` job completed successfully, including production-import prohibition, synthetic tests, acquisition dry-run construction, acquisition-plan validation, machine-readable integrity proof, proof validation, and evidence upload.

[proven] The retained workflow artifact ID is `8241941409`.

[proven] The retained workflow artifact digest is `sha256:58fae09001e141174cd65c8f3a4dc1bc5340a1a0f0a1d7297e03ed5684dc13ed`.

[proven] The artifact expiry timestamp is `2026-08-09T23:37:20Z`.

[proven] The no-network acquisition plan covers instruments `EUR_USD` and `GBP_USD` across granularities `M15`, `H1`, `H4`, and `D` for the half-open interval `2026-06-01T00:00:00Z` to `2026-07-11T00:00:00Z`.

[proven] The plan contains exactly `8` requests: one request for each instrument/granularity combination.

[proven] Each request uses method `GET`, explicit `from` and `to` bounds, midpoint pricing `price=M`, and no `count` parameter.

[proven] The deterministic acquisition-plan hash is `aaac6f58243b244377f7aa18392d1c5bb904227dd8a9e59f04cfd42b93e90d0c`.

[proven] The expected theoretical maximum candle counts per instrument are `3840` for M15, `960` for H1, `240` for H4, and `40` for D. These are upper bounds over elapsed time, not assertions of market-open candle counts.

[proven] The machine-readable integrity proof returned `PASS`, verified `4` artifacts, and detected deliberate tampering through an artifact-size mismatch.

[not proven] This dry run does not prove OANDA entitlement, provider retention depth, actual returned candle counts, provider alignment, or live historical-data integrity.

[not proven] No OANDA or Dukascopy network request was executed by this validation.
