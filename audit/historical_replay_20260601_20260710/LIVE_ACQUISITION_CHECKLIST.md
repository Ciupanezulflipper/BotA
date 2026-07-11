# Read-only OANDA historical acquisition checklist

## Scope lock

- [ ] Confirm the branch is `audit/historical-replay-20260601-20260710`.
- [ ] Confirm PR #6 remains draft and unmerged.
- [ ] Confirm no production BotA process, cron job, Telegram path, Supabase path, or strategy file will be invoked.
- [ ] Confirm the requested range is half-open: `2026-06-01T00:00:00Z` to `2026-07-11T00:00:00Z`.
- [ ] Confirm the request is read-only and limited to OANDA candle retrieval.

## Credential handling

- [ ] Use only the environment variable `BOTA_AUDIT_OANDA_TOKEN`.
- [ ] Do not place the token in shell history, a command argument, a file, GitHub, CI, logs, screenshots, or chat.
- [ ] Export the token only in the current shell session.
- [ ] Unset the token immediately after acquisition.
- [ ] Never use the production Telegram or Supabase credentials for this operation.

## Mandatory preview

Run the wrapper without `--execute` first. The preview must report `network_permitted=false`, show the exact request path and boundaries, and contain no secret value.

```bash
python -m audit.historical_replay_20260601_20260710.src.live_acquisition_cli \
  --output-root /absolute/path/outside/production/runtime \
  --run-id eurusd-m15-20260601-20260711 \
  --instrument EUR_USD \
  --granularity M15 \
  --start-utc 2026-06-01T00:00:00Z \
  --end-utc 2026-07-11T00:00:00Z
```

## Explicit execution gate

Live execution requires all three controls simultaneously:

1. `--execute`
2. the exact phrase `I_AUTHORIZE_READ_ONLY_OANDA_ACQUISITION`
3. a non-empty `BOTA_AUDIT_OANDA_TOKEN` environment variable

Example shape only; do not paste a real token into the command:

```bash
read -s BOTA_AUDIT_OANDA_TOKEN
export BOTA_AUDIT_OANDA_TOKEN
python -m audit.historical_replay_20260601_20260710.src.live_acquisition_cli \
  --output-root /absolute/path/outside/production/runtime \
  --run-id eurusd-m15-20260601-20260711 \
  --instrument EUR_USD \
  --granularity M15 \
  --start-utc 2026-06-01T00:00:00Z \
  --end-utc 2026-07-11T00:00:00Z \
  --execute \
  --authorization-phrase I_AUTHORIZE_READ_ONLY_OANDA_ACQUISITION
unset BOTA_AUDIT_OANDA_TOKEN
```

## Post-run verification

- [ ] Confirm raw response files, request metadata, response metadata, derived candles, artifact index, and manifest exist under the isolated output root.
- [ ] Confirm request metadata contains no bearer token.
- [ ] Run the sidecar verifier against the completed run.
- [ ] Record provider request IDs, artifact hashes, row counts, and any failed or empty responses.
- [ ] Do not classify an empty successful response as an operational failure without market-closure and coverage analysis.
- [ ] Do not merge PR #6 based only on successful acquisition.

## Stop conditions

Stop immediately if any request targets an unexpected host, contains `count=`, writes outside the audit root, exposes a token, invokes production code, or returns evidence that cannot be preserved immutably.
