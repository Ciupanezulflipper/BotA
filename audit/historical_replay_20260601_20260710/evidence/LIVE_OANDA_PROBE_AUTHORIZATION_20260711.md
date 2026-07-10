# Live OANDA probe authorization boundary — 2026-07-11

- [proven] The operator explicitly authorized proceeding to the next step and authorized one minimal read-only OANDA probe.
- [proven] Authorization applies only to a bounded historical-candle read request through the isolated historical-replay sidecar.
- [proven] Authorization does not permit order placement, account mutation, production BotA execution, Telegram changes, Supabase changes, strategy changes, threshold changes, pair expansion, or timeframe expansion.
- [proven] The approved probe target is EUR_USD, M15, OANDA practice endpoint, midpoint price `M`, with an explicit `from` and `to` range and no `count` parameter.
- [proven] The live acquisition wrapper remains fail-closed and requires the exact phrase `I_AUTHORIZE_READ_ONLY_OANDA_ACQUISITION` plus an ephemeral `BOTA_AUDIT_OANDA_TOKEN` environment variable.
- [not proven] No usable OANDA token is available to the current execution environment.
- [proven] No live provider request was executed while the credential was absent.
- [proven] The next execution gate is receipt of the token through a non-persistent environment variable on the operator-controlled machine or an explicitly configured secret-bearing runner.
- [proven] The token must never be committed, pasted into repository files, included in command history, or printed in logs.
