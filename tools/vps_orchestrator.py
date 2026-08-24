#!/usr/bin/env python3
"""Reusable VPS runtime-contract foundation (no scheduler implementation)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "production-vps.env"
DEPENDENCY_PATH = ROOT / "requirements-runtime.txt"
PYPROJECT_PATH = ROOT / "pyproject.toml"
SOURCE_GENERATION = "0212d9848ecb8e8b464da215c2ac115d62dae2f4"
POLICY_KEYS = (
    "PAIRS", "TIMEFRAMES", "POLICY_B_ENABLED", "POLICY_B_SCORE_MIN",
    "POLICY_B_ADX_MAX", "FILTER_SCORE_MIN", "FILTER_SCORE_MIN_ALL",
    "NEWS_ON", "TELEGRAM_MIN_SCORE", "TELEGRAM_TIER_YELLOW_MIN",
    "TELEGRAM_TIER_YELLOW_MIN_INT", "TELEGRAM_TIER_GREEN_MIN",
    "TELEGRAM_TIER_GREEN_MIN_INT", "TELEGRAM_COOLDOWN_SECONDS",
    "CANDLE_MAX_AGE_SECS",
)
REQUIRED_COMMANDS = (
    "bash", "python3", "curl", "flock", "timeout", "git", "systemctl", "jq",
    "cat", "chmod", "date", "find", "grep", "head", "mkdir", "mktemp",
    "rm", "sed", "sort", "stat", "tail", "tee", "tr",
)
PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)$")
ENV_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


class ContractError(RuntimeError):
    """A versioned runtime contract is missing or malformed."""


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def load_frozen_policy(
    path: Path = POLICY_PATH, ambient: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Load the allowlisted policy; versioned values override ambient values."""
    effective = dict(ambient if ambient is not None else os.environ)
    parsed: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ENV_RE.fullmatch(line)
        if not match:
            raise ContractError(f"policy_malformed:line={number}")
        key, value = match.groups()
        if key not in POLICY_KEYS:
            raise ContractError(f"policy_key_not_allowed:{key}")
        if key in parsed:
            raise ContractError(f"policy_duplicate:{key}")
        parsed[key] = _unquote(value)
    missing = sorted(set(POLICY_KEYS) - parsed.keys())
    if missing:
        raise ContractError(f"policy_missing:{','.join(missing)}")
    effective.update(parsed)
    return {key: effective[key] for key in POLICY_KEYS}


def parse_dependency_manifest(path: Path = DEPENDENCY_PATH) -> list[dict[str, str]]:
    """Parse an exact-pin-only direct production dependency manifest."""
    dependencies: list[dict[str, str]] = []
    seen: set[str] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN_RE.fullmatch(line)
        if not match:
            raise ContractError(f"dependency_not_exact_pin:line={number}")
        name, version = match.groups()
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in seen:
            raise ContractError(f"dependency_duplicate:{normalized}")
        seen.add(normalized)
        dependencies.append({"name": normalized, "version": version})
    if not dependencies:
        raise ContractError("dependency_manifest_empty")
    return sorted(dependencies, key=lambda item: item["name"])


def command_preflight(
    commands: Sequence[str] = REQUIRED_COMMANDS,
    *,
    path: str | None = None,
) -> dict[str, object]:
    """Return fail-closed, machine-readable command availability evidence."""
    resolved = {command: shutil.which(command, path=path) for command in commands}
    missing = sorted(command for command, location in resolved.items() if not location)
    return {
        "schema_version": "1.0",
        "healthy": not missing,
        "commands": {key: resolved[key] for key in sorted(resolved)},
        "missing": missing,
    }


def declared_python_contract(path: Path = PYPROJECT_PATH) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    try:
        contract = data["project"]["requires-python"]
    except (KeyError, TypeError) as exc:
        raise ContractError("python_contract_missing") from exc
    if contract != ">=3.14,<3.15":
        raise ContractError(f"python_contract_unsupported:{contract}")
    return contract


def runtime_python_result() -> dict[str, object]:
    healthy = sys.version_info[:2] == (3, 14)
    return {
        "contract": declared_python_contract(),
        "executable": sys.executable,
        "healthy": healthy,
        "version": ".".join(map(str, sys.version_info[:3])),
    }


def effective_config_document(
    *,
    ambient: Mapping[str, str] | None = None,
    policy_path: Path = POLICY_PATH,
    dependency_path: Path = DEPENDENCY_PATH,
    commands: Sequence[str] = REQUIRED_COMMANDS,
) -> dict[str, object]:
    """Build an allowlist-only document; credential-bearing input is ignored."""
    return {
        "schema_version": "1.0",
        "release": {"source_generation": SOURCE_GENERATION},
        "runtime": {
            "python_contract": declared_python_contract(),
            "dependencies": parse_dependency_manifest(dependency_path),
            "required_commands": sorted(commands),
        },
        "strategy_policy": load_frozen_policy(policy_path, ambient),
    }


def effective_config_evidence(**kwargs: object) -> dict[str, object]:
    document = effective_config_document(**kwargs)
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": "1.0",
        "effective_config": document,
        "fingerprint_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
