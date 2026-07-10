from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .acquisition_dry_run import build_acquisition_plan
from .multi_chunk_acquisition import acquire_oanda_range

TOKEN_ENV = "BOTA_AUDIT_OANDA_TOKEN"
EXECUTION_PHRASE = "I_AUTHORIZE_READ_ONLY_OANDA_ACQUISITION"
_ALLOWED_PAIRS = {"EUR_USD", "GBP_USD"}
_ALLOWED_GRANULARITIES = {"M15", "H1", "H4", "D"}


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed read-only OANDA historical acquisition wrapper."
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--instrument", choices=sorted(_ALLOWED_PAIRS), required=True)
    parser.add_argument("--granularity", choices=sorted(_ALLOWED_GRANULARITIES), required=True)
    parser.add_argument("--start-utc", required=True)
    parser.add_argument("--end-utc", required=True)
    parser.add_argument("--base-url", default="https://api-fxpractice.oanda.com")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-candles-per-chunk", type=int, default=5000)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--authorization-phrase", default="")
    return parser


def build_preview(args: argparse.Namespace) -> dict:
    plan = build_acquisition_plan(
        start_utc=_utc(args.start_utc),
        end_utc=_utc(args.end_utc),
        instruments=(args.instrument,),
        granularities=(args.granularity,),
        max_candles=args.max_candles_per_chunk,
    )
    return {
        "mode": "preview",
        "network_permitted": False,
        "token_environment_variable": TOKEN_ENV,
        "authorization_phrase_required": EXECUTION_PHRASE,
        "run_id": args.run_id,
        "output_root": str(Path(args.output_root)),
        "base_url": args.base_url,
        "plan": plan,
    }


def _token_from_environment(environ: dict[str, str]) -> str:
    token = environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise PermissionError(f"missing ephemeral token environment variable: {TOKEN_ENV}")
    return token


def execute(args: argparse.Namespace, *, environ: dict[str, str] | None = None) -> dict:
    if args.execute is not True:
        return build_preview(args)
    if args.authorization_phrase != EXECUTION_PHRASE:
        raise PermissionError("explicit authorization phrase missing or incorrect")
    token = _token_from_environment(dict(os.environ if environ is None else environ))
    result = acquire_oanda_range(
        output_root=Path(args.output_root),
        run_id=args.run_id,
        instrument=args.instrument,
        granularity=args.granularity,
        start_utc=_utc(args.start_utc),
        end_utc=_utc(args.end_utc),
        token=token,
        enabled=True,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        max_candles_per_chunk=args.max_candles_per_chunk,
    )
    return {
        "mode": "live-read-only",
        "network_permitted": True,
        "token_persisted": False,
        **result,
    }


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        result = execute(args)
    except Exception as exc:  # fail closed and avoid printing secrets
        print(json.dumps({"status": "ERROR", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
