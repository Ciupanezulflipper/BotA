#!/usr/bin/env python3
"""Build, validate, and atomically apply an offline BotA continuity handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "1.0"
MANIFEST = "handoff-manifest.json"
HASH_RE = re.compile(r"logs/state/last_hash_[A-Z]{6}_M15\.txt$")
TG_RE = re.compile(r"state/telegram_delivery/[0-9a-f]{64}\.json$")
FIXED = {
    "logs/alerts.csv": "decision_journal",
    "state/profitlab_delivery_cursor.json": "profitlab_cursor",
    "state/pause": "circuit_breaker",
}
VALID_TG = {"intent", "sent", "unknown_outcome", "definite_failure"}
PAUSE_LINE_RE = re.compile(r"export (PAUSE_(?:EURUSD|GBPUSD|USDJPY))=1")


class HandoffError(RuntimeError):
    pass


def _classification(relative: str) -> str | None:
    if relative in FIXED:
        return FIXED[relative]
    if TG_RE.fullmatch(relative):
        return "telegram_delivery"
    if HASH_RE.fullmatch(relative):
        return "watcher_content_hash"
    return None


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise HandoffError(f"malformed_json:{path.name}") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"malformed_json:{path.name}")
    return value


def _validate_source(relative: str, path: Path, alerts_size: int | None) -> None:
    if not path.is_file() or path.is_symlink():
        raise HandoffError(f"unsafe_source:{relative}")
    if relative == "state/profitlab_delivery_cursor.json":
        value = _json(path)
        try:
            offset = int(value["offset"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HandoffError("profitlab_cursor_invalid") from exc
        if alerts_size is None or offset < 0 or offset > alerts_size:
            raise HandoffError("profitlab_cursor_out_of_range")
    elif TG_RE.fullmatch(relative):
        value = _json(path)
        if value.get("status") not in VALID_TG:
            raise HandoffError(f"telegram_state_invalid:{path.name}")
    elif HASH_RE.fullmatch(relative):
        value = path.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[0-9a-f]{32,64}", value):
            raise HandoffError(f"watcher_hash_invalid:{path.name}")
    elif relative == "state/pause":
        if path.stat().st_size > 65536:
            raise HandoffError("pause_state_too_large")
        lines = path.read_text(encoding="utf-8").splitlines()
        keys: set[str] = set()
        for line in lines:
            matched = PAUSE_LINE_RE.fullmatch(line)
            if not matched:
                raise HandoffError("pause_state_invalid")
            if matched.group(1) in keys:
                raise HandoffError("pause_state_duplicate")
            keys.add(matched.group(1))


def _files(root: Path) -> list[tuple[str, Path, str]]:
    selected: list[tuple[str, Path, str]] = []
    candidates = [root / p for p in FIXED]
    candidates += list((root / "state/telegram_delivery").glob("*.json"))
    candidates += list((root / "logs/state").glob("last_hash_*_M15.txt"))
    for path in candidates:
        if not path.exists():
            continue
        relative = path.relative_to(root).as_posix()
        classification = _classification(relative)
        if classification:
            selected.append((relative, path, classification))
    return sorted(selected)


def build(source: Path, bundle: Path) -> dict[str, Any]:
    if bundle.exists():
        raise HandoffError("bundle_exists")
    alerts = source / "logs/alerts.csv"
    cursor = source / "state/profitlab_delivery_cursor.json"
    if alerts.exists() != cursor.exists():
        raise HandoffError("profitlab_continuity_pair_incomplete")
    alerts_size = alerts.stat().st_size if alerts.is_file() else None
    selected = _files(source)
    if not selected:
        raise HandoffError("handoff_empty")
    staging = Path(tempfile.mkdtemp(prefix=f".{bundle.name}.", dir=bundle.parent))
    records = []
    try:
        for relative, path, classification in selected:
            _validate_source(relative, path, alerts_size)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            data = path.read_bytes()
            target.write_bytes(data)
            os.chmod(target, 0o600)
            records.append({"path": relative, "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "mode": "0600", "classification": classification})
        manifest = {"schema_version": SCHEMA, "handoff_id": str(uuid.uuid4()),
                    "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "files": records}
        (staging / MANIFEST).write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(staging / MANIFEST, 0o600)
        os.replace(staging, bundle)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def validate(bundle: Path) -> dict[str, Any]:
    manifest = _json(bundle / MANIFEST)
    if manifest.get("schema_version") != SCHEMA or not isinstance(manifest.get("files"), list):
        raise HandoffError("manifest_invalid")
    listed: set[str] = set()
    alerts_size = None
    for record in manifest["files"]:
        relative = record.get("path") if isinstance(record, dict) else None
        if not isinstance(relative, str) or _classification(relative) != record.get("classification"):
            raise HandoffError("manifest_path_not_allowed")
        path = bundle / relative
        data = path.read_bytes()
        if len(data) != record.get("size") or hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise HandoffError(f"manifest_digest_mismatch:{relative}")
        if relative == "logs/alerts.csv":
            alerts_size = len(data)
        listed.add(relative)
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()} - {MANIFEST}
    if actual != listed:
        raise HandoffError("bundle_contains_unlisted_files")
    for relative in sorted(listed):
        _validate_source(relative, bundle / relative, alerts_size)
    return manifest


def apply(bundle: Path, destination: Path) -> dict[str, Any]:
    manifest = validate(bundle)
    destination.mkdir(parents=True, exist_ok=True)
    for record in manifest["files"]:
        relative = record["path"]
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write((bundle / relative).read_bytes())
                handle.flush(); os.fsync(handle.fileno())
            os.chmod(name, 0o600)
            os.replace(name, target)
            parent_fd = os.open(target.parent, os.O_RDONLY)
            try: os.fsync(parent_fd)
            finally: os.close(parent_fd)
        finally:
            Path(name).unlink(missing_ok=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "validate", "apply"):
        p = sub.add_parser(name)
        p.add_argument("source", type=Path)
        if name != "validate": p.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        result = (build(args.source, args.destination) if args.command == "build" else
                  apply(args.source, args.destination) if args.command == "apply" else validate(args.source))
    except (HandoffError, OSError) as exc:
        print(json.dumps({"STATE_HANDOFF_CONTRACT": "FAIL", "reason": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"STATE_HANDOFF_CONTRACT": "PASS", "handoff_id": result["handoff_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
