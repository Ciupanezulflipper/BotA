# BotA — Forex Signal Bot

Production Forex signal bot running on Android/Termux.

## Current production status

```text
DEPLOYED_RELEASE=8728de6b5a2ed0f4647374ef4fa6ed72f9eb03c0
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
PACKAGE_1_CLOCK_SESSION=PASS
CURRENT_CONTROL_PLANE=HEALTHY_7_OF_7
PACKAGE_2_PRE_MARKET_INTEGRITY=PENDING
OPEN_MARKET_THREE_PAIR_PROOF=PENDING
MONDAY_READY=NO
```

Do not infer current production state from old backtests, `BOTLOG.md`, historical continuity entries, or the Android Git worktree HEAD.

## Start here

For every new engineering/audit session, read in this order:

1. `AI_START_HERE.md` — authoritative current operating rules and status.
2. `CONTINUITY_CURRENT.md` — current production handoff and next action.
3. `CHAT_HANDOFF_BOTA.md` — compact cross-chat handoff.
4. `state/STATE.json` — machine-readable repository handoff snapshot.
5. `DECISIONS.md` — currently locked decisions.
6. `ERRORS.md` and `audits/ERROR_LOG.md` — failure classes, fixes, and prevention rules.
7. `audits/PACKAGE1_CLOCK_AND_PACKAGE2_CONTROL_PLANE_2026-08-09.md` — latest immutable Package #1/#2 evidence.

Older dated audits, `BOTLOG.md`, `BOOTLOG.md`, and `CONTINUITY.md` remain historical evidence. They do not override the current files above.

## Current production scope

```text
PAIRS=EURUSD GBPUSD USDJPY
TIMEFRAMES=M15
POLICY_B_ENABLED=1
POLICY_B_SCORE_MIN=70
POLICY_B_ADX_MAX=30
NEWS_ON=0
TELEGRAM_ENABLED=1
DRY_RUN_MODE=0
```

Do not lower strategy thresholds or force signals to compensate for operational problems.

## Current engineering gate

Package #1 — trusted clock/session semantics — is deployed and live-proven.

Package #2 must still harden persistent Termux service-manager/watchdog recovery, including PID-1 orphan supervisors and the exact stale-live-singleton-child/resource-owner condition discovered with `crond`, before the final natural `MARKET_OPEN` three-pair production proof.
