# BotA Clock Drift Observability

This branch adds a reporting-only clock drift check for Android/Termux ship-time conditions.

## Files

- `tools/clock_drift_check.py` compares local Android UTC with server UTC from HTTPS Date headers.
- `tools/clock_drift_check.sh` is a safe wrapper.

## Usage

```bash
cd /data/data/com.termux/files/home/BotA || exit 1
bash tools/clock_drift_check.sh
```

## Status values

- `OK`: server time available and local clock drift is below threshold.
- `DRIFT_WARN`: server time available but local clock drift is above threshold.
- `SERVER_CLOCK_UNAVAILABLE`: not enough server Date headers were available.

## Guarantees

```text
STRATEGY_CHANGED=NO
THRESHOLDS_CHANGED=NO
H1_LOGIC_CHANGED=NO
SIGNAL_GENERATION_CHANGED=NO
TELEGRAM_ALERT_LOGIC_CHANGED=NO
CRON_CHANGED=NO
```

This is observability only. It does not change market-open logic, score rules, H1 rules, Telegram gates, or cron cadence.
