#!/usr/bin/env python3
"""Launch the heartbeat runtime in the shadow producer's clock domain.

Android's CLOCK_BOOTTIME includes suspended time. The active shadow service
persists useful-progress timestamps in that domain, so deadman age must be
computed against the same clock. Delivery state still receives one consistent
same-boot value from the unified runtime cycle.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from types import ModuleType

try:
    from tools import heartbeat_runtime
except ModuleNotFoundError:  # Direct execution from tools/ on Termux.
    import heartbeat_runtime  # type: ignore[no-redef]


class _BootTimeClock:
    """Expose the monotonic interface expected by heartbeat_runtime."""

    @staticmethod
    def monotonic() -> float:
        """Return CLOCK_BOOTTIME when available, else standard monotonic time."""
        clock = getattr(time, "CLOCK_BOOTTIME", None)
        if clock is None:
            return time.monotonic()
        return time.clock_gettime(clock)


def run(root: Path) -> int:
    """Run one heartbeat cycle with a process-local boot-time clock adapter."""
    original_clock: ModuleType = heartbeat_runtime.time
    try:
        heartbeat_runtime.time = _BootTimeClock()  # type: ignore[assignment]
        return heartbeat_runtime.run_cycle(root)
    finally:
        heartbeat_runtime.time = original_clock


def main() -> int:
    """Parse the BotA root and run one clock-consistent heartbeat cycle."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("BOTA_ROOT", str(Path.home() / "BotA"))),
    )
    args = parser.parse_args()
    return run(args.root.expanduser())


if __name__ == "__main__":
    raise SystemExit(main())
