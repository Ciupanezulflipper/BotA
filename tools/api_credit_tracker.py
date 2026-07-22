#!/usr/bin/env python3
"""Compatibility entrypoint for provider-specific API accounting.

The historical implementation incremented a counter after every successful
market-data fetch and labelled that counter "Twelve Data credits" even though
the live fetcher used OANDA with Yahoo fallback. That produced false quota
warnings. New code must use ``tools/provider_usage.py`` and identify the actual
provider for every request.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_STATE = ROOT / "logs" / "api_credits.json"


def provider_status() -> int:
    """Delegate status output to the provider-specific ledger."""
    sys.path.insert(0, str(ROOT / "tools"))
    from provider_usage import main as provider_main

    return provider_main(["status"])


def reset_legacy() -> int:
    """Archive the misleading legacy counter without touching real usage data."""
    if LEGACY_STATE.exists():
        archived = LEGACY_STATE.with_name("api_credits.legacy_misclassified.json")
        try:
            os.replace(LEGACY_STATE, archived)
            print(f"LEGACY_COUNTER_ARCHIVED={archived}")
        except OSError as exc:
            print(f"LEGACY_COUNTER_ARCHIVE_ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
            return 2
    else:
        print("LEGACY_COUNTER_PRESENT=NO")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the compatibility command."""
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "status"

    if command == "status":
        return provider_status()
    if command == "reset":
        return reset_legacy()
    if command == "increment":
        print(
            json.dumps(
                {
                    "result": "rejected",
                    "reason": "provider_required",
                    "message": (
                        "Generic increments are disabled because they previously "
                        "misclassified OANDA/Yahoo fetches as Twelve Data credits. "
                        "Use provider_usage.py record/reserve with an explicit provider."
                    ),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(f"UNKNOWN_COMMAND={command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
