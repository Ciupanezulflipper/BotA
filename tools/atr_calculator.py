#!/usr/bin/env python3

import json
import os

PIP_SIZE = 0.01  # USDJPY default

def calculate_atr(candles, period=14):
    """
    candles = list of dicts:
    {
        "high": float,
        "low": float,
        "close": float
    }
    """

    if len(candles) < period + 1:
        return None

    trs = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        trs.append(tr)

    # take last N TR values
    recent_trs = trs[-period:]

    atr = sum(recent_trs) / len(recent_trs)
    return atr


def atr_in_pips(atr_value):
    return atr_value / PIP_SIZE if atr_value else None


# --- TEST MODE ---
if __name__ == "__main__":
    # simple test dataset (mock candles)
    sample = [
        {"high": 100, "low": 99, "close": 99.5},
        {"high": 101, "low": 99.2, "close": 100},
        {"high": 102, "low": 100, "close": 101},
        {"high": 103, "low": 101, "close": 102},
        {"high": 104, "low": 102, "close": 103},
        {"high": 105, "low": 103, "close": 104},
        {"high": 106, "low": 104, "close": 105},
        {"high": 107, "low": 105, "close": 106},
        {"high": 108, "low": 106, "close": 107},
        {"high": 109, "low": 107, "close": 108},
        {"high": 110, "low": 108, "close": 109},
        {"high": 111, "low": 109, "close": 110},
        {"high": 112, "low": 110, "close": 111},
        {"high": 113, "low": 111, "close": 112},
        {"high": 114, "low": 112, "close": 113},
    ]

    atr = calculate_atr(sample)
    print(json.dumps({
        "atr_raw": atr,
        "atr_pips": atr_in_pips(atr)
    }, indent=2))
