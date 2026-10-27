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
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "1.0"
MANIFEST = "handoff-manifest.json"
HASH_RE = re.compile(r"logs/state/last_hash_[A-Z]{6}_M15\.txt$")
TG_RE = re.compile(r"state/telegram_delivery/[0-9a-f]{64}\.json$")
ALERTS_RELATIVE = "logs/alerts.csv"
CURSOR_RELATIVE = "state/profitlab_delivery_cursor.json"
PAUSE_RELATIVE = "state/pause"
FIXED = {
    ALERTS_RELATIVE: "decision_journal",
    CURSOR_RELATIVE: "profitlab_cursor",
    PAUSE_RELATIVE: "circuit_breaker",
}
VALID_TG = {"intent", "sent", "unknown_outcome", "definite_failure"}
PAUSE_LINE_RE = re.compile(r"export (PAUSE_(?:EURUSD|GBPUSD|USDJPY))=1")


class HandoffError(RuntimeError):
    pass


def _safe_relative(relative: str) -> PurePosixPath:
    if relative == ALERTS_RELATIVE:
        return PurePosixPath("logs", "alerts.csv")
    if relative == CURSOR_RELATIVE:
        return PurePosixPath("state", "profitlab_delivery_cursor.json")
    if relative == PAUSE_RELATIVE:
        return PurePosixPath("state", "pause")
    telegram = re.fullmatch(r"state/telegram_delivery/([0-9a-f]{64}\.json)", relative)
    if telegram:
        return PurePosixPath("state", "telegram_delivery", telegram.group(1))
    watcher = re.fullmatch(r"logs/state/(last_hash_[A-Z]{6}_M15\.txt)", relative)
    if watcher:
        return PurePosixPath("logs", "state", watcher.group(1))
    raise HandoffError("path_escape")


def _normalized_cli_path(path: Path) -> Path:
    if not path.is_absolute():
        raise HandoffError("cli_path_must_be_absolute")
    normalized = Path(os.path.normpath(os.fspath(path)))
    if normalized != path or ".." in path.parts:
        raise HandoffError("cli_path_not_normalized")
    return normalized


def _within(root: Path, candidate: Path) -> bool:
    return candidate == root or root in candidate.parents


def _existing_under(root: Path, relative: str) -> Path:
    rel = _safe_relative(relative)
    try:
        root_real = root.resolve(strict=True)
    except OSError as exc:
        raise HandoffError("root_unavailable") from exc
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise HandoffError(f"path_escape:{relative}")
    candidate = root.joinpath(*rel.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise HandoffError(f"unsafe_source:{relative}") from exc
    if not _within(root_real, resolved):
        raise HandoffError(f"path_escape:{relative}")
    return candidate


def _target_under(root: Path, relative: str) -> Path:
    rel = _safe_relative(relative)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root_real = root.resolve(strict=True)
    except OSError as exc:
        raise HandoffError("destination_unavailable") from exc
    cursor = root
    for part in rel.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise HandoffError(f"unsafe_target:{relative}")
        cursor.mkdir(exist_ok=True, mode=0o700)
        if not _within(root_real, cursor.resolve(strict=True)):
            raise HandoffError(f"unsafe_target:{relative}")
    target = root.joinpath(*rel.parts)
    if target.is_symlink():
        raise HandoffError(f"unsafe_target:{relative}")
    if not _within(root_real, target.parent.resolve(strict=True)):
        raise HandoffError(f"unsafe_target:{relative}")
    return target


def _write_target_bytes(root: Path, relative: str, data: bytes) -> Path:
    rel = _safe_relative(relative)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)

    directory_flags = os.O_RDONLY
    directory_flags |= getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    file_flags |= getattr(os, "O_NOFOLLOW", 0)

    opened_fds: list[int] = []
    try:
        try:
            current_fd = os.open(root, directory_flags)
        except OSError as exc:
            raise HandoffError("destination_unavailable") from exc
        opened_fds.append(current_fd)

        for part in rel.parts[:-1]:
            try:
                os.mkdir(part, 0o700, dir_fd=current_fd)
            except FileExistsError:
                pass
            except OSError as exc:
                raise HandoffError(f"unsafe_target:{relative}") from exc

            try:
                next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            except OSError as exc:
                raise HandoffError(f"unsafe_target:{relative}") from exc
            opened_fds.append(next_fd)
            current_fd = next_fd

        try:
            file_fd = os.open(rel.name, file_flags, 0o600, dir_fd=current_fd)
        except OSError as exc:
            raise HandoffError(f"unsafe_target:{relative}") from exc

        try:
            with os.fdopen(file_fd, "wb", closefd=True) as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise HandoffError(f"unsafe_target:{relative}") from exc

        target = root.joinpath(*rel.parts)
        os.chmod(target, 0o600, follow_symlinks=False)
        return target
    finally:
        for fd in reversed(opened_fds):
            try:
                os.close(fd)
            except OSError:
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
    except (OSError, ValueError) as exc:
        raise HandoffError(f"malformed_json:{path.name}") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"malformed_json:{path.name}")
    return value


def _validate_source(relative: str, path: Path, alerts_size: int | None) -> None:
    if not path.is_file() or path.is_symlink():
        raise HandoffError(f"unsafe_source:{relative}")
    if relative == CURSOR_RELATIVE:
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
        hash_text = path.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[0-9a-f]{32,64}", hash_text):
            raise HandoffError(f"watcher_hash_invalid:{path.name}")
    elif relative == PAUSE_RELATIVE:
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
            safe_relative = _safe_relative(relative).as_posix()
            selected.append((safe_relative, path, classification))
    return sorted(selected)


def build(source: Path, bundle: Path) -> dict[str, Any]:
    if bundle.exists():
        raise HandoffError("bundle_exists")
    alerts = source / ALERTS_RELATIVE
    cursor = source / CURSOR_RELATIVE
    if alerts.exists() != cursor.exists():
        raise HandoffError("profitlab_continuity_pair_incomplete")
    if alerts.exists():
        alerts = _existing_under(source, ALERTS_RELATIVE)
        cursor = _existing_under(source, CURSOR_RELATIVE)
    alerts_size = alerts.stat().st_size if alerts.is_file() else None
    selected = _files(source)
    if not selected:
        raise HandoffError("handoff_empty")
    staging = Path(tempfile.mkdtemp(prefix=f".{bundle.name}.", dir=bundle.parent))
    records = []
    try:
        for relative, path, classification in selected:
            path = _existing_under(source, relative)
            _validate_source(relative, path, alerts_size)
            data = path.read_bytes()
            _write_target_bytes(staging, relative, data)
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
        relative = _safe_relative(relative).as_posix()
        path = _existing_under(bundle, relative)
        data = path.read_bytes()
        if len(data) != record.get("size") or hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise HandoffError(f"manifest_digest_mismatch:{relative}")
        if relative == ALERTS_RELATIVE:
            alerts_size = len(data)
        listed.add(relative)
    for candidate in bundle.rglob("*"):
        if candidate.is_symlink():
            raise HandoffError("bundle_symlink_rejected")
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()} - {MANIFEST}
    if actual != listed:
        raise HandoffError("bundle_contains_unlisted_files")
    for relative in sorted(listed):
        _validate_source(relative, _existing_under(bundle, relative), alerts_size)
    return manifest


def apply(bundle: Path, destination: Path) -> dict[str, Any]:
    manifest = validate(bundle)
    destination.mkdir(parents=True, exist_ok=True)
    for record in manifest["files"]:
        relative = record["path"]
        if not isinstance(relative, str):
            raise HandoffError("manifest_path_not_allowed")
        relative = _safe_relative(relative).as_posix()
        source = _existing_under(bundle, relative)
        target = _target_under(destination, relative)
        fd, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(source.read_bytes())
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
        source = _normalized_cli_path(args.source)
        destination = _normalized_cli_path(args.destination) if args.command != "validate" else None
        result = (build(source, destination) if args.command == "build" else
                  apply(source, destination) if args.command == "apply" else validate(source))
    except (HandoffError, OSError) as exc:
        print(json.dumps({"STATE_HANDOFF_CONTRACT": "FAIL", "reason": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"STATE_HANDOFF_CONTRACT": "PASS", "handoff_id": result["handoff_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
