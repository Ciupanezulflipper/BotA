from __future__ import annotations

from argparse import Namespace

import pytest

from audit.historical_replay_20260601_20260710.src.live_acquisition_cli import (
    EXECUTION_PHRASE,
    TOKEN_ENV,
    build_preview,
    execute,
)


def args(**overrides):
    values = dict(
        output_root="/tmp/bota-audit",
        run_id="preview-001",
        instrument="EUR_USD",
        granularity="M15",
        start_utc="2026-06-01T00:00:00Z",
        end_utc="2026-07-11T00:00:00Z",
        base_url="https://api-fxpractice.oanda.com",
        timeout_seconds=30.0,
        max_candles_per_chunk=5000,
        execute=False,
        authorization_phrase="",
    )
    values.update(overrides)
    return Namespace(**values)


def test_preview_is_no_network_and_contains_no_token():
    preview = execute(args(), environ={TOKEN_ENV: "super-secret"})
    encoded = str(preview)
    assert preview["mode"] == "preview"
    assert preview["network_permitted"] is False
    assert preview["plan"]["request_count"] == 1
    assert "count=" not in preview["plan"]["requests"][0]["path_and_query"]
    assert "super-secret" not in encoded


def test_execute_requires_exact_authorization_phrase_before_token_use():
    with pytest.raises(PermissionError, match="authorization phrase"):
        execute(args(execute=True), environ={TOKEN_ENV: "secret"})


def test_execute_requires_ephemeral_token():
    with pytest.raises(PermissionError, match=TOKEN_ENV):
        execute(
            args(execute=True, authorization_phrase=EXECUTION_PHRASE),
            environ={},
        )


def test_preview_rejects_naive_timestamps():
    with pytest.raises(ValueError, match="timezone-aware"):
        build_preview(args(start_utc="2026-06-01T00:00:00"))
