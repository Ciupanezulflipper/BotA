from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .runtime_epochs import RuntimeEpoch, RuntimeState, validate_runtime_epochs

UTC = timezone.utc
_ALLOWED_STATES = {state.value: state for state in RuntimeState}


@dataclass(frozen=True)
class RuntimeEvidenceDocument:
    schema_version: int
    window_start_utc: datetime
    window_end_utc: datetime
    source_commit: str
    evidence_files: tuple[str, ...]
    epochs: tuple[RuntimeEpoch, ...]


def _parse_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty UTC timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _non_empty_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return value.strip()


def parse_runtime_evidence(payload: Mapping[str, Any]) -> RuntimeEvidenceDocument:
    """Parse explicit runtime evidence without inferring uncovered intervals.

    The document is only an evidence carrier. It does not derive UP or DOWN from
    missing logs, repository commits, or market-data availability.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("runtime evidence payload must be an object")
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported runtime evidence schema_version")

    start = _parse_utc(payload.get("window_start_utc"), "window_start_utc")
    end = _parse_utc(payload.get("window_end_utc"), "window_end_utc")
    if start >= end:
        raise ValueError("runtime evidence window requires start < end")

    source_commit = _non_empty_text(payload.get("source_commit"), "source_commit")
    raw_files = payload.get("evidence_files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("evidence_files must be a non-empty list")
    evidence_files = tuple(_non_empty_text(item, "evidence_files item") for item in raw_files)
    if len(set(evidence_files)) != len(evidence_files):
        raise ValueError("evidence_files must not contain duplicates")

    raw_epochs = payload.get("epochs")
    if not isinstance(raw_epochs, list):
        raise ValueError("epochs must be a list")

    epochs: list[RuntimeEpoch] = []
    for index, raw in enumerate(raw_epochs):
        if not isinstance(raw, Mapping):
            raise ValueError(f"epochs[{index}] must be an object")
        state_text = _non_empty_text(raw.get("state"), f"epochs[{index}].state").upper()
        if state_text not in _ALLOWED_STATES:
            raise ValueError(f"epochs[{index}].state is unsupported")
        epoch = RuntimeEpoch(
            start_utc=_parse_utc(raw.get("start_utc"), f"epochs[{index}].start_utc"),
            end_utc=_parse_utc(raw.get("end_utc"), f"epochs[{index}].end_utc"),
            state=_ALLOWED_STATES[state_text],
            evidence_id=_non_empty_text(raw.get("evidence_id"), f"epochs[{index}].evidence_id"),
        )
        if epoch.start_utc < start or epoch.end_utc > end:
            raise ValueError(f"epochs[{index}] falls outside the declared evidence window")
        epochs.append(epoch)

    validated = validate_runtime_epochs(epochs)
    evidence_ids = [row.evidence_id for row in validated]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ValueError("runtime epoch evidence_id values must be unique")

    return RuntimeEvidenceDocument(
        schema_version=1,
        window_start_utc=start,
        window_end_utc=end,
        source_commit=source_commit,
        evidence_files=evidence_files,
        epochs=validated,
    )


def load_runtime_evidence(path: Path) -> RuntimeEvidenceDocument:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("runtime evidence file is not valid UTF-8 JSON") from exc
    return parse_runtime_evidence(payload)
