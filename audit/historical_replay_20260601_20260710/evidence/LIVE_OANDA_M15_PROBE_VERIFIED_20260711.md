# Live OANDA M15 Probe Verification — 2026-07-11

Status: proven

## Scope

- Repository worktree: isolated historical replay worktree
- Production BotA checkout remained separate at commit `fa289ad3f7b6ff430f13609950e5af341aee2e9d`
- Audit branch commit at execution: `0db969713bb60ec26e8e16389eb8331c2816784b`
- Run ID: `oanda-probe-eurusd-m15-20260711`
- Instrument: `EUR_USD`
- Granularity: `M15`
- Interval: `2026-07-10T18:00:00Z` to `2026-07-10T19:00:00Z`
- Endpoint class: OANDA practice
- Price component: midpoint (`M`)
- Request form: explicit `from` and `to`; no `count` parameter

## Verified evidence

Required files were present:

- raw payload
- sanitized request metadata
- sanitized response metadata
- derived candles
- run manifest

Observed hashes:

- raw: `6b2cb1561ddb7a13a04444d1280087c891dd237d3e3bab7c48ba461270f19811`
- request metadata: `2267a77f610ed5ded72b2f19ff23a3a8c584952cf5ed4df38dcef5267131c2aa`
- response metadata: `f7ba6247a932dfeebe56b617098099e14c36b58e4115cf85d43646e97acc4413`
- derived candles: `ed801158f16ed0d76c3619294f37b4f773fa6fe9885a163dcf51ee997f99eb5e`
- manifest: `3d96e1d83e88679578e1181f6f17d4f7f7932450cd0d8bb240cf15def67f4380`

Observed sizes:

- raw: 598 bytes
- request metadata: 322 bytes
- response metadata: 358 bytes
- derived candles: 485 bytes
- manifest: 1288 bytes

Observed result:

- HTTP response status: `200`
- raw JSON valid: yes
- raw candle count: `4`
- derived candle count: `4`
- first candle: `2026-07-10T18:00:00.000000000Z`
- last candle: `2026-07-10T18:45:00.000000000Z`
- instrument reported: `EUR_USD`
- granularity reported: `M15`
- manifest schema version: `1`
- manifest run ID matched expected run ID
- offline inspection exit code: `0`
- request contained no `count=` parameter

## Security note

The request metadata inspection matched the string `Authorization`, but this does not by itself prove that a secret token was persisted. The sidecar is intended to redact authorization values. Exact redaction content still requires direct inspection of the sanitized request metadata file without printing secrets.

## Conclusion

The bounded M15 read-only acquisition completed and produced a complete evidence set that passed offline structural verification. Overwrite protection also refused a later attempt to reuse the same run ID.
