#!/usr/bin/env python3
"""Run deterministic BotA production-rule replay on an immutable candle dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import replay_semantics as semantics
import verify_replay_dataset as verifier


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _load_series(
    dataset_root: Path, pairs: list[str]
) -> dict[tuple[str, str], semantics.HistoricalSeries]:
    streams: dict[tuple[str, str], semantics.HistoricalSeries] = {}
    for pair in pairs:
        for timeframe in ("M15", "H1", "H4", "D1"):
            path = dataset_root / "candles" / f"{pair}_{timeframe}.csv"
            streams[(pair, timeframe)] = semantics.HistoricalSeries(
                pair,
                timeframe,
                semantics.load_candle_csv(path),
            )
    return streams


def _iter_m15(
    series: semantics.HistoricalSeries,
    evaluation_start,
    evaluation_end,
):
    for candle in series.candles:
        decision_time = semantics.candle_completion(candle, "M15")
        if evaluation_start <= decision_time < evaluation_end:
            yield candle


def _summary(
    events: list[dict[str, Any]],
    *,
    source_commit: str,
    dataset_id: str,
    config: semantics.ReplayConfig,
) -> dict[str, Any]:
    rejection_counts = Counter(str(event.get("reject_stage", "")) for event in events)
    accepted = [event for event in events if event.get("policy_a_current")]
    policy_b = [event for event in events if event.get("policy_b_score70_adx_lt30")]
    policy_c = [
        event for event in events
        if event.get("policy_c_score70_adx_lt30_no_extreme")
    ]
    return {
        "schema_version": 1,
        "status": "COMPLETE",
        "replay_grade": "DETERMINISTIC_PRODUCTION_RULES_WITH_PROVIDER_SUBSTITUTION",
        "source_commit": source_commit,
        "production_source_blobs": semantics.PRODUCTION_SOURCE_BLOBS,
        "dataset_id": dataset_id,
        "config": {
            "filter_score_min": config.filter_score_min,
            "h1_trend_min_score": config.h1_trend_min_score,
            "h1_veto_override_score": config.h1_veto_override_score,
            "h1_veto_override_adx": config.h1_veto_override_adx,
            "macro6": config.macro6,
            "d1_filter_mode": config.d1_filter_mode,
        },
        "fidelity": {
            "indicator_math": "production_build_indicators_exact_module",
            "quality_filter": "production_quality_filter_exact_module",
            "support_resistance": "production_sr_score_exact_module_on_historical_H1",
            "market_hours": "historical_UTC_reconstruction_of_market_open_sh",
            "session_score": "historical_UTC_reconstruction_of_scoring_engine",
            "macro6": "frozen_neutral_3",
            "d1_runtime_trend_cache": (
                "fail_open_ANY_by_default; tracked writer not established"
            ),
            "emit_snapshot_votes": (
                "same vote formula on OANDA historical H4/D1 bundles; "
                "original live provider was network-dependent"
            ),
            "volume_component": (
                "neutral_0 because production build_indicators bundle does not "
                "carry candle volume"
            ),
        },
        "decision_rows": len(events),
        "accepted_current": len(accepted),
        "accepted_policy_b": len(policy_b),
        "accepted_policy_c": len(policy_c),
        "rejection_stages": dict(sorted(rejection_counts.items())),
        "pairs": dict(sorted(Counter(str(e["pair"]) for e in events).items())),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    dataset_root = Path(args.dataset_root).resolve()
    evaluation_start = semantics.parse_utc(args.evaluation_start_utc)
    evaluation_end = semantics.parse_utc(args.evaluation_end_utc)
    raw_start = semantics.parse_utc(args.raw_start_utc)
    raw_end = semantics.parse_utc(args.raw_end_utc)
    if not evaluation_start < evaluation_end:
        raise ValueError("evaluation end must be after evaluation start")

    dataset_id = dataset_root.name
    verifier.verify_dataset(
        dataset_root=dataset_root,
        expected_dataset_id=dataset_id,
        raw_start=raw_start,
        raw_end=raw_end,
        evaluation_start=evaluation_start,
        pairs=args.pairs,
        timeframes=["M15", "H1", "H4", "D1"],
        min_warmup_bars=args.min_warmup_bars,
    )

    config = semantics.ReplayConfig(
        filter_score_min=args.filter_score_min,
        h1_trend_min_score=args.h1_trend_min_score,
        h1_veto_override_score=args.h1_veto_override_score,
        h1_veto_override_adx=args.h1_veto_override_adx,
        scalp_sl_atr_mult=args.scalp_sl_atr_mult,
        scalp_tp_atr_mult=args.scalp_tp_atr_mult,
        max_sl_pips=args.max_sl_pips,
        max_tp_pips=args.max_tp_pips,
        macro6=args.macro6,
        d1_filter_mode=args.d1_filter_mode,
    )

    streams = _load_series(dataset_root, args.pairs)
    events: list[dict[str, Any]] = []
    for pair in args.pairs:
        m15 = streams[(pair, "M15")]
        h1 = streams[(pair, "H1")]
        h4 = streams[(pair, "H4")]
        d1 = streams[(pair, "D1")]
        for candle in _iter_m15(m15, evaluation_start, evaluation_end):
            events.append(
                semantics.replay_decision(
                    pair=pair,
                    m15_candle=candle,
                    m15_series=m15,
                    h1_series=h1,
                    h4_series=h4,
                    d1_series=d1,
                    config=config,
                )
            )

    events.sort(key=lambda row: (row["decision_time"], row["pair"]))
    output_path = Path(args.output).resolve()
    summary_path = Path(args.summary_output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(
                json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
            )

    summary = _summary(
        events,
        source_commit=args.source_commit,
        dataset_id=dataset_id,
        config=config,
    )
    summary["evaluation_start_utc"] = semantics.iso_z(evaluation_start)
    summary["evaluation_end_utc_exclusive"] = semantics.iso_z(evaluation_end)
    summary["events_sha256"] = _sha256(output_path)
    summary["events_bytes"] = output_path.stat().st_size
    summary_path.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic BotA production-rule historical replay"
    )
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--raw-start-utc", required=True)
    parser.add_argument("--raw-end-utc", required=True)
    parser.add_argument("--evaluation-start-utc", required=True)
    parser.add_argument("--evaluation-end-utc", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--pairs", nargs="+", default=["EURUSD", "GBPUSD"])
    parser.add_argument("--min-warmup-bars", type=int, default=500)
    parser.add_argument("--filter-score-min", type=float, default=65.0)
    parser.add_argument("--h1-trend-min-score", type=float, default=40.0)
    parser.add_argument("--h1-veto-override-score", type=float, default=75.0)
    parser.add_argument("--h1-veto-override-adx", type=float, default=40.0)
    parser.add_argument("--scalp-sl-atr-mult", type=float, default=2.0)
    parser.add_argument("--scalp-tp-atr-mult", type=float, default=4.0)
    parser.add_argument("--max-sl-pips", type=float, default=30.0)
    parser.add_argument("--max-tp-pips", type=float, default=60.0)
    parser.add_argument("--macro6", type=int, choices=range(0, 7), default=3)
    parser.add_argument("--d1-filter-mode", choices=["ANY", "EMA"], default="ANY")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        summary = run(args)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
