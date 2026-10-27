#!/usr/bin/env python3
"""Validate BotA's declared production Python runtime dependencies.

This checker intentionally uses only the Python standard library so it can
report a missing third-party dependency instead of failing for the same reason.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import json
import re
import os
import tempfile
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "requirements-runtime.txt"
REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)$")
IMPORT_NAMES = {
    "requests": "requests",
}


class DependencyContractError(RuntimeError):
    """Raised when the runtime dependency manifest itself is invalid."""


def normalized_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_manifest(path: Path) -> list[tuple[str, str]]:
    """Read exact package pins from the production runtime manifest."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DependencyContractError(
            f"manifest_unreadable:{type(exc).__name__}"
        ) from exc

    pins: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = REQUIREMENT_RE.fullmatch(line)
        if not match:
            raise DependencyContractError(f"manifest_not_exact_pin:line={line_number}")
        distribution, required = match.groups()
        normalized = normalized_distribution(distribution)
        if normalized in seen:
            raise DependencyContractError(f"manifest_duplicate:{normalized}")
        seen.add(normalized)
        pins.append((distribution, required))

    if not pins:
        raise DependencyContractError("manifest_empty")
    return pins


def dependency_result(distribution: str, required: str) -> dict[str, Any]:
    """Check both installed distribution version and real importability."""
    normalized = normalized_distribution(distribution)
    import_name = IMPORT_NAMES.get(normalized, normalized.replace("-", "_"))
    failures: list[str] = []

    try:
        installed = metadata.version(distribution)
    except metadata.PackageNotFoundError:
        installed = None
        failures.append(f"missing_distribution:{distribution}")
    except Exception as exc:  # pragma: no cover - defensive metadata boundary
        installed = None
        failures.append(f"metadata_error:{distribution}:{type(exc).__name__}")

    if installed is not None and installed != required:
        failures.append(
            f"version_mismatch:{distribution}:installed={installed}:required={required}"
        )

    try:
        importlib.import_module(import_name)
    except Exception as exc:
        failures.append(f"import_failed:{import_name}:{type(exc).__name__}:{exc}")

    return {
        "healthy": not failures,
        "distribution": distribution,
        "import_name": import_name,
        "required_version": required,
        "installed_version": installed,
        "failure_reasons": failures,
    }


def collect(manifest: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    """Return one machine-readable dependency contract snapshot."""
    try:
        pins = parse_manifest(manifest)
    except DependencyContractError as exc:
        return {
            "schema_version": "1.0",
            "healthy": False,
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "manifest": str(manifest),
            "dependencies": {},
            "failure_reasons": [str(exc)],
            "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    dependencies: dict[str, Any] = {}
    failures: list[str] = []
    for distribution, required in pins:
        result = dependency_result(distribution, required)
        dependencies[normalized_distribution(distribution)] = result
        failures.extend(result["failure_reasons"])

    return {
        "schema_version": "1.0",
        "healthy": not failures,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "manifest": str(manifest),
        "dependencies": dependencies,
        "failure_reasons": failures,
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def write_evidence(path: Path, result: dict[str, Any]) -> None:
    """Owner-only atomic evidence: fsync temp file, replace, fsync parent."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(result, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
        parent_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        tmp.unlink(missing_ok=True)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--evidence", type=Path)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    result = collect(args.manifest)
    if args.evidence is not None:
        try:
            write_evidence(args.evidence, result)
        except OSError as exc:
            result["healthy"] = False
            result["failure_reasons"].append(f"evidence_write_failed:{type(exc).__name__}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["healthy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
