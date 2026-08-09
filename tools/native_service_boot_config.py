#!/usr/bin/env python3
"""Render a single persistent Termux:Boot launcher for the native watchdog."""
from __future__ import annotations

import argparse
from pathlib import Path

BEGIN = "# BEGIN BOTA_NATIVE_SERVICE_WATCHDOG"
END = "# END BOTA_NATIVE_SERVICE_WATCHDOG"
LEGACY_TOKEN = "start_runsvdir_guard.sh"
WATCHDOG_TOKEN = "start_native_service_daemon_watchdog.sh"


class BootConfigError(RuntimeError):
    """Raised when a boot file cannot be changed without ownership ambiguity."""


def _active_token_lines(lines: list[str], token: str) -> list[int]:
    """Return 0-based non-comment line indexes containing ``token``."""
    return [
        index
        for index, line in enumerate(lines)
        if token in line and line.strip() and not line.lstrip().startswith("#")
    ]


def _managed_range(lines: list[str]) -> tuple[int, int] | None:
    starts = [index for index, line in enumerate(lines) if line.strip() == BEGIN]
    ends = [index for index, line in enumerate(lines) if line.strip() == END]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise BootConfigError(
            f"managed_block_invalid:starts={len(starts)}:ends={len(ends)}"
        )
    return starts[0], ends[0]


def render_boot_config(text: str, launcher: Path, log_path: Path) -> str:
    """Return boot text with exactly one BotA watchdog launcher block.

    Historical commented references are left untouched. Any active legacy or
    un-managed watchdog launcher fails closed rather than risking two control
    planes after reboot.
    """
    lines = text.splitlines()
    managed = _managed_range(lines)

    outside = list(lines)
    if managed is not None:
        start, end = managed
        outside = lines[:start] + lines[end + 1 :]

    legacy_active = _active_token_lines(outside, LEGACY_TOKEN)
    watchdog_active = _active_token_lines(outside, WATCHDOG_TOKEN)
    if legacy_active:
        raise BootConfigError(
            "active_legacy_guard_present:" + ",".join(str(i + 1) for i in legacy_active)
        )
    if watchdog_active:
        raise BootConfigError(
            "unmanaged_watchdog_launcher_present:"
            + ",".join(str(i + 1) for i in watchdog_active)
        )

    command = f'"{launcher}" >> "{log_path}" 2>&1'
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
    parser.add_argument("--launcher", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    source = args.source.read_text(encoding="utf-8")
    rendered = render_boot_config(source, args.launcher, args.log)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print("BOOT_WATCHDOG_BLOCK=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootConfigError as exc:
        print(f"BOOT_WATCHDOG_BLOCK=FAIL:{exc}")
        raise SystemExit(3) from exc
