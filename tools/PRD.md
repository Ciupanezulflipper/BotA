# BotA Product Requirements — Current Router

Status: **CURRENT PRD ROUTER**
Last updated: 2026-09-27 UTC

The previous Termux-era PRD that lived in this file is preserved in Git history and is historical evidence only.

The current forward product and recovery requirements are defined in:

`docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md`

Current product scope:

```text
PAIRS=EURUSD,GBPUSD,USDJPY
EXECUTION_TF=M15
PRIMARY_RUNTIME=HETZNER
ANDROID_ROLE=CONTROL_AND_OBSERVATION_ONLY
LIVE_MONEY_TRADING=NO
STRATEGY_TUNING_DURING_RECOVERY=NO
REAL_TELEGRAM_SIGNAL_REQUIRED=YES
REAL_TELEGRAM_CLOSE_REQUIRED=YES
REAL_DAILY_REPORT_REQUIRED=YES
```

Current acceptance requires a working three-pair scan/decision/delivery lifecycle, clean restart recovery, duplicate suppression, and GitHub/Obsidian runtime consistency.

Do not use the old four-pair Termux mission as current authority.

For current operational handoff, read `CONTINUITY_CURRENT.md`.
For the full recovery requirements, read `docs/BOTA_EXECUTION_RECOVERY_PRD_2026-09-27.md`.