from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from .canonical_candle import CanonicalCandle
from .path_guard import ensure_within_root
from .provider_reconciliation import reconcile_providers
from .raw_artifact import write_once


def _canonical_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def build_reconciliation_evidence(
    *,
    primary_rows: Iterable[CanonicalCandle],
    independent_rows: Iterable[CanonicalCandle],
    price_tolerance: float,
) -> dict:
    primary = list(primary_rows)
    independent = list(independent_rows)
    if not primary or not independent:
        raise ValueError("both providers require at least one canonical candle")
    scope = {
        (row.instrument, row.granularity) for row in primary + independent
    }
    if len(scope) != 1:
        raise ValueError("provider reconciliation requires one instrument/granularity scope")

    result = reconcile_providers(
        primary,
        independent,
        price_tolerance=price_tolerance,
    )
    instrument, granularity = next(iter(scope))
    differences = [asdict(item) for item in result.differences]
    report = {
        "schema_version": 1,
        "instrument": instrument,
        "granularity": granularity,
        "primary_provider": primary[0].provider,
        "independent_provider": independent[0].provider,
        "price_tolerance": price_tolerance,
        "primary_count": len(primary),
        "independent_count": len(independent),
        "matched_timestamps": result.matched_timestamps,
        "primary_only": list(result.primary_only),
        "independent_only": list(result.independent_only),
        "differences": differences,
        "exact_match": result.exact_match,
    }
    report["evidence_sha256"] = sha256(_canonical_bytes(report)).hexdigest()
    return report


def write_reconciliation_evidence(
    *,
    root: Path,
    run_id: str,
    report: dict,
) -> dict:
    if not run_id or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_." for ch in run_id):
        raise ValueError("unsafe run_id")
    root = root.resolve()
    target = ensure_within_root(root, root / "evidence" / run_id / "provider_reconciliation.json")
    artifact = write_once(root, target.relative_to(root).as_posix(), _canonical_bytes(report))
    return {
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "size_bytes": artifact.size_bytes,
        "evidence_sha256": report.get("evidence_sha256"),
    }
