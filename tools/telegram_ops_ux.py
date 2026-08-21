#!/usr/bin/env python3
"""Format BotA operational Telegram alerts without exposing raw diagnostics.

Raw failure codes remain in runtime_health.json and supervisor logs. This helper
only decides whether a subscriber-facing transition should be suppressed or
rendered as a concise scan/system message.
"""

from __future__ import annotations

import argparse

ZOMBIE_ONLY_PREFIX = "control_plane:zombie_runsv_count:"
VALID_CLASSES = {"scan", "system", "suppress"}


def split_failures(raw: str) -> list[str]:
    """Return non-empty pipe-delimited failure tokens."""
    return [part.strip() for part in str(raw).split("|") if part.strip()]


def classify_failure(raw: str) -> str:
    """Classify raw failures for subscriber-facing operational messaging."""
    failures = split_failures(raw)
    if failures and all(item.startswith(ZOMBIE_ONLY_PREFIX) for item in failures):
        return "suppress"

    has_pipeline = any(item.startswith("pipeline:") for item in failures)
    has_real_control = any(
        item.startswith("control_plane:") and not item.startswith(ZOMBIE_ONLY_PREFIX)
        for item in failures
    )
    has_other = any(
        not item.startswith("pipeline:")
        and not item.startswith("control_plane:")
        for item in failures
    )

    if has_real_control or has_other:
        return "system"
    if has_pipeline:
        return "scan"
    return "system"


def classify_flag(value: str) -> str:
    """Read the new compact flag format while supporting legacy raw flags."""
    normalized = str(value).strip()
    if normalized in VALID_CLASSES:
        return normalized
    return classify_failure(normalized)


def issue_message(kind: str) -> str:
    """Return a concise subscriber-facing issue transition."""
    if kind == "scan":
        return (
            "⚠️ BOTA · SCAN DELAYED\n"
            "Fresh market scanning is delayed or incomplete.\n"
            "BotA will not present stale data as a valid setup."
        )
    if kind == "system":
        return (
            "⚠️ BOTA · SYSTEM ISSUE\n"
            "BotA detected an operational health problem.\n"
            "Trading safeguards remain active. Details are logged internally."
        )
    return ""


def recovery_message(kind: str) -> str:
    """Return a concise subscriber-facing recovery transition."""
    if kind == "scan":
        return "✅ BOTA · SCAN RESTORED\nFresh market scanning has resumed."
    if kind == "system":
        return "✅ BOTA · SYSTEM RESTORED\nBotA operational health checks are back to normal."
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("classify", "classify-flag", "issue-message", "recovery-message"),
    )
    parser.add_argument("value", nargs="?", default="")
    args = parser.parse_args()

    if args.action == "classify":
        print(classify_failure(args.value))
    elif args.action == "classify-flag":
        print(classify_flag(args.value))
    elif args.action == "issue-message":
        print(issue_message(args.value))
    else:
        print(recovery_message(args.value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
