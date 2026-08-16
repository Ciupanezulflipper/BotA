#!/usr/bin/env python3
"""Bound retained per-cycle watcher evidence without touching recent files.

Successful cycles remove their temporary evidence themselves. Failed/interrupted
cycles intentionally retain evidence for forensics; this helper prevents that
retention from growing without bound.

Safety rules:
- operate only on regular files directly inside the supplied state directory;
- only match BotA-owned watcher evidence filename prefixes;
- never follow symlinks;
- never delete files newer than the grace window;
- keep at least ``keep_per_kind`` files for each evidence kind;
- fail closed if a kind still exceeds ``hard_cap_per_kind`` after pruning.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
import time
from pathlib import Path

PATTERNS = (
    "watcher_cycle.*.log",
    "watcher_telegram.*.jsonl",
    "watcher_supabase.*.jsonl",
)


def _regular_candidates(state_dir: Path, pattern: str) -> list[tuple[int, Path]]:
    rows: list[tuple[int, Path]] = []
    for path in state_dir.glob(pattern):
        try:
            st = path.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(st.st_mode):
            continue
        rows.append((st.st_mtime_ns, path))
    rows.sort(key=lambda item: item[0], reverse=True)
    return rows


def prune(
    state_dir: Path,
    *,
    keep_per_kind: int = 200,
    hard_cap_per_kind: int = 400,
    grace_seconds: int = 6 * 60 * 60,
    now_ns: int | None = None,
) -> dict[str, int]:
    if keep_per_kind < 1:
        raise ValueError("keep_per_kind must be >= 1")
    if hard_cap_per_kind < keep_per_kind:
        raise ValueError("hard_cap_per_kind must be >= keep_per_kind")
    if grace_seconds < 0:
        raise ValueError("grace_seconds must be >= 0")

    state_dir = state_dir.resolve(strict=True)
    if not state_dir.is_dir():
        raise ValueError("state_dir is not a directory")

    now = time.time_ns() if now_ns is None else int(now_ns)
    grace_ns = int(grace_seconds) * 1_000_000_000
    removed = 0
    remaining_total = 0

    for pattern in PATTERNS:
        rows = _regular_candidates(state_dir, pattern)
        for index, (mtime_ns, path) in enumerate(rows):
            if index < keep_per_kind:
                continue
            if now - mtime_ns < grace_ns:
                continue
            # Revalidate immediately before deletion. Never follow or unlink a
            # symlink that replaced the regular file after enumeration.
            try:
                st = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            removed += 1

        remaining = len(_regular_candidates(state_dir, pattern))
        remaining_total += remaining
        if remaining > hard_cap_per_kind:
            raise RuntimeError(
                f"watcher evidence hard cap exceeded pattern={pattern} "
                f"remaining={remaining} hard_cap={hard_cap_per_kind}"
            )

    return {"removed": removed, "remaining": remaining_total}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--keep-per-kind", type=int, default=200)
    parser.add_argument("--hard-cap-per-kind", type=int, default=400)
    parser.add_argument("--grace-seconds", type=int, default=6 * 60 * 60)
    args = parser.parse_args()

    try:
        result = prune(
            Path(args.state_dir),
            keep_per_kind=args.keep_per_kind,
            hard_cap_per_kind=args.hard_cap_per_kind,
            grace_seconds=args.grace_seconds,
        )
    except Exception as exc:
        print(f"[WATCHER_EVIDENCE] retention_failed={type(exc).__name__}:{exc}", file=sys.stderr)
        return 67

    print(
        f"[WATCHER_EVIDENCE] retention_removed={result['removed']} "
        f"retention_remaining={result['remaining']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
