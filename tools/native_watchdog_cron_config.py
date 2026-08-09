#!/usr/bin/env python3
"""Render one managed cron guardian for the native watchdog."""
from __future__ import annotations

import argparse
from pathlib import Path

BEGIN = "# BEGIN BOTA_NATIVE_WATCHDOG_GUARD"
END = "# END BOTA_NATIVE_WATCHDOG_GUARD"
GUARD_TOKEN = "native_watchdog_guard.py"


class CronConfigError(RuntimeError):
    """Raised when guardian cron ownership is ambiguous."""


def _managed_range(lines: list[str]) -> tuple[int, int] | None:
    starts = [index for index, line in enumerate(lines) if line.strip() == BEGIN]
    ends = [index for index, line in enumerate(lines) if line.strip() == END]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise CronConfigError(
            f"managed_block_invalid:starts={len(starts)}:ends={len(ends)}"
        )
    return starts[0], ends[0]


def _active_guard_lines(lines: list[str]) -> list[int]:
    return [
        index
        for index, line in enumerate(lines)
        if GUARD_TOKEN in line
        and line.strip()
        and not line.lstrip().startswith("#")
    ]


def render_crontab(
    text: str,
    *,
    python: Path,
    guard: Path,
    root: Path,
    log: Path,
) -> str:
    """Return crontab text with exactly one managed watchdog guardian."""
    lines = text.splitlines()
    managed = _managed_range(lines)

    outside = list(lines)
    if managed is not None:
        start, end = managed
        outside = lines[:start] + lines[end + 1 :]

    unmanaged = _active_guard_lines(outside)
    if unmanaged:
        raise CronConfigError(
            "unmanaged_guard_present:" + ",".join(str(i + 1) for i in unmanaged)
        )

    command = (
        f'* * * * * cd "{root}" && "{python}" "{guard}" --ensure '
        f'>> "{log}" 2>&1'
    )
    block = [BEGIN, command, END]

    if managed is None:
        rendered = list(lines)
        if rendered and rendered[-1].strip():
            rendered.append("")
        rendered.extend(block)
    else:
        start, end = managed
        rendered = lines[:start] + block + lines[end + 1 :]

    return "\n".join(rendered).rstrip("\n") + "\n"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--guard", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    source = args.source.read_text(encoding="utf-8") if args.source.exists() else ""
    rendered = render_crontab(
        source,
        python=args.python,
        guard=args.guard,
        root=args.root,
        log=args.log,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print("WATCHDOG_GUARD_CRON_BLOCK=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CronConfigError as exc:
        print(f"WATCHDOG_GUARD_CRON_BLOCK=FAIL:{exc}")
        raise SystemExit(3) from exc
