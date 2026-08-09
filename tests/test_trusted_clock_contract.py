from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

calendar_guard = import_module("calendar_guard")
news_filter_real = import_module("news_filter_real")
trusted_time = import_module("trusted_time")
TrustedTimeUnavailable = trusted_time.TrustedTimeUnavailable
session_component = trusted_time.session_component
trusted_epoch = trusted_time.trusted_epoch
trusted_utc = trusted_time.trusted_utc

UTC = timezone.utc


def epoch(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())


def reference_session_component(value: int) -> tuple[float, str]:
    dt = datetime.fromtimestamp(value, UTC)
    hour = dt.hour + dt.minute / 60.0
    if 12.0 <= hour < 16.0:
        return 5.0, "session_overlap"
    if 7.0 <= hour < 12.0:
        return 2.0, "session_london"
    if 16.0 <= hour < 20.0:
        return 2.0, "session_ny"
    return 0.0, "session_edge"


def test_trusted_time_never_falls_back_to_wall_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BOTA_SERVER_EPOCH", raising=False)
    with pytest.raises(TrustedTimeUnavailable):
        trusted_epoch()
    with pytest.raises(TrustedTimeUnavailable):
        trusted_utc()

    monkeypatch.setenv("BOTA_SERVER_EPOCH", "not-an-epoch")
    with pytest.raises(TrustedTimeUnavailable):
        trusted_epoch()


def test_explicit_epoch_wins_for_replay_and_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "BOTA_SERVER_EPOCH", str(epoch("2026-08-10T19:00:00Z"))
    )
    explicit = epoch("2026-08-10T12:00:00Z")
    assert trusted_epoch(explicit) == explicit
    assert session_component(explicit) == (5.0, "session_overlap")


@pytest.mark.parametrize(
    ("stamp", "expected"),
    [
        ("2026-08-10T06:59:59Z", (0.0, "session_edge")),
        ("2026-08-10T07:00:00Z", (2.0, "session_london")),
        ("2026-08-10T11:59:59Z", (2.0, "session_london")),
        ("2026-08-10T12:00:00Z", (5.0, "session_overlap")),
        ("2026-08-10T15:59:59Z", (5.0, "session_overlap")),
        ("2026-08-10T16:00:00Z", (2.0, "session_ny")),
        ("2026-08-10T19:59:59Z", (2.0, "session_ny")),
        ("2026-08-10T20:00:00Z", (0.0, "session_edge")),
    ],
)
def test_session_boundaries_use_trusted_utc(
    stamp: str, expected: tuple[float, str]
) -> None:
    assert session_component(epoch(stamp)) == expected


def test_seeded_clock_fault_matrix_is_host_timezone_invariant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Monte-Carlo-like fault injection over 2,000 trusted UTC instants."""
    rng = random.Random(20260809)
    zones = [
        "UTC",
        "America/Lima",
        "Europe/London",
        "Europe/Bucharest",
        "Asia/Tokyo",
        "Pacific/Honolulu",
    ]
    start = epoch("2026-08-10T00:00:00Z")
    span = 14 * 24 * 60 * 60

    for _ in range(2_000):
        value = start + rng.randrange(span)
        monkeypatch.setenv("TZ", rng.choice(zones))
        monkeypatch.setenv("BOTA_SERVER_EPOCH", str(value))
        assert session_component() == reference_session_component(value)
        assert int(trusted_utc().timestamp()) == value


def run_market_gate(
    tmp_path: Path, stamp: str
) -> tuple[subprocess.CompletedProcess[str], str, int]:
    reason_file = tmp_path / "reason.txt"
    epoch_file = tmp_path / "epoch.txt"

    # If market_open accidentally re-enters its HTTP clock probe despite an
    # inherited epoch, this sitecustomize makes every urlopen fail. The gate
    # must still classify the supplied epoch correctly.
    (tmp_path / "sitecustomize.py").write_text(
        "import urllib.request\n"
        "def _boom(*args, **kwargs):\n"
        "    raise RuntimeError('network probe forbidden in inherited-clock test')\n"
        "urllib.request.urlopen = _boom\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "BOTA_SERVER_EPOCH": str(epoch(stamp)),
            "BOTA_SERVER_EPOCH_FILE": str(epoch_file),
            "MARKET_OPEN_REASON_FILE": str(reason_file),
            "PYTHONPATH": str(tmp_path),
        }
    )
    proc = subprocess.run(
        ["bash", str(TOOLS / "market_open.sh")],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    reason = reason_file.read_text(encoding="utf-8").strip()
    recorded_epoch = int(epoch_file.read_text(encoding="utf-8").strip())
    return proc, reason, recorded_epoch


@pytest.mark.parametrize(
    ("stamp", "stdout", "returncode", "reason"),
    [
        ("2026-08-08T12:00:00Z", "Closed", 1, "MARKET_CLOSED_SATURDAY"),
        ("2026-08-09T12:00:00Z", "Closed", 1, "MARKET_CLOSED_SUNDAY"),
        ("2026-08-14T19:59:59Z", "Open", 0, "MARKET_OPEN"),
        (
            "2026-08-14T20:00:00Z",
            "Closed",
            1,
            "MARKET_CLOSED_FRIDAY_POST_2000",
        ),
        (
            "2026-08-10T06:59:59Z",
            "Closed",
            1,
            "MARKET_CLOSED_ASIAN_PRE_0700",
        ),
        ("2026-08-10T07:00:00Z", "Open", 0, "MARKET_OPEN"),
        ("2026-08-10T19:59:59Z", "Open", 0, "MARKET_OPEN"),
        (
            "2026-08-10T20:00:00Z",
            "Closed",
            1,
            "MARKET_CLOSED_POST_NY",
        ),
    ],
)
def test_market_gate_reuses_inherited_epoch_without_network(
    tmp_path: Path,
    stamp: str,
    stdout: str,
    returncode: int,
    reason: str,
) -> None:
    proc, actual_reason, recorded_epoch = run_market_gate(tmp_path, stamp)
    assert proc.stdout.strip() == stdout
    assert proc.returncode == returncode
    assert actual_reason == reason
    assert recorded_epoch == epoch(stamp)


def event(minutes_from_now: int, *, importance: str = "high") -> dict:
    now = epoch("2026-08-10T12:00:00Z")
    return {
        "title": "Test Event",
        "currency": "USD",
        "importance": importance,
        "timestamp": now + minutes_from_now * 60,
    }


@pytest.mark.parametrize(
    ("minutes", "importance", "blocked"),
    [
        (30, "high", True),
        (31, "high", False),
        (0, "high", True),
        (-60, "high", True),
        (-61, "high", False),
        (15, "medium", True),
        (16, "medium", False),
        (-30, "medium", True),
        (-31, "medium", False),
    ],
)
def test_calendar_before_after_windows_have_correct_sign(
    minutes: int, importance: str, blocked: bool
) -> None:
    now = float(epoch("2026-08-10T12:00:00Z"))
    result = calendar_guard.check_events(
        [event(minutes, importance=importance)], {"USD"}, now
    )
    assert result["block"] is blocked
    if blocked and minutes > 0:
        assert result["reason"].endswith("min before")
    if blocked and minutes < 0:
        assert result["reason"].endswith("min after")


def test_calendar_cli_fails_closed_without_trusted_epoch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BOTA_SERVER_EPOCH", raising=False)
    result = calendar_guard.clock_unavailable_result(
        "EURUSD", "BOTA_SERVER_EPOCH_unavailable"
    )
    assert result["block"] is True
    assert result["reason"].startswith("CLOCK_UNAVAILABLE:")


def test_news_gate_requires_trusted_time_when_calendar_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEWS_BLOCK_ENABLED", "true")
    monkeypatch.setenv("FINNHUB_API_KEY", "dummy")
    monkeypatch.delenv("BOTA_SERVER_EPOCH", raising=False)
    ok, note = news_filter_real.news_risk_gate("EURUSD")
    assert ok is False
    assert note == "clock_unavailable"


def test_news_gate_keeps_provider_absence_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEWS_BLOCK_ENABLED", "true")
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("BOTA_SERVER_EPOCH", raising=False)
    ok, note = news_filter_real.news_risk_gate("EURUSD")
    assert ok is True
    assert note == "no_calendar_api"


def test_scoring_engine_session_score_tracks_trusted_epoch(
    tmp_path: Path,
) -> None:
    """Run the real scorer at 11:59 and 12:00 with identical indicators."""
    root = tmp_path / "BotA"
    tools = root / "tools"
    cache = root / "cache"
    config = root / "config"
    tools.mkdir(parents=True)
    cache.mkdir()
    config.mkdir()

    for name in ("scoring_engine.sh", "market_open.sh", "trusted_time.py"):
        shutil.copy2(TOOLS / name, tools / name)
    (tools / "scoring_engine.sh").chmod(0o755)
    (tools / "market_open.sh").chmod(0o755)

    indicators = {
        "ema9": 1.1010,
        "ema21": 1.1000,
        "rsi": 60.0,
        "atr": 0.0010,
        "price": 1.1005,
        "open": 1.1002,
        "high": 1.1012,
        "low": 1.0998,
        "close": 1.1006,
        "prev_close": 1.1001,
        "macd_hist": 0.00010,
        "adx": 25.0,
        "bb_upper": 0.0,
        "bb_middle": 0.0,
        "bb_lower": 0.0,
        "bb_squeeze": False,
        "candles": [{"volume": 100.0} for _ in range(21)],
    }
    (cache / "indicators_EURUSD_M15.json").write_text(
        json.dumps(indicators), encoding="utf-8"
    )

    def score_at(stamp: str) -> dict:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(tmp_path),
                "BOTA_ROOT": str(root),
                "BOTA_SERVER_EPOCH": str(epoch(stamp)),
            }
        )
        proc = subprocess.run(
            ["bash", str(tools / "scoring_engine.sh"), "EURUSD", "M15"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    london = score_at("2026-08-10T11:59:00Z")
    overlap = score_at("2026-08-10T12:00:00Z")

    assert london["direction"] == overlap["direction"] == "BUY"
    assert "session=session_london" in london["reasons"]
    assert "session=session_overlap" in overlap["reasons"]
    assert overlap["score"] - london["score"] == pytest.approx(3.0)


def test_clock_sensitive_sources_do_not_call_wall_clock_now() -> None:
    scorer = (TOOLS / "scoring_engine.sh").read_text(encoding="utf-8")
    calendar_source = (TOOLS / "calendar_guard.py").read_text(encoding="utf-8")
    news_source = (TOOLS / "news_filter_real.py").read_text(encoding="utf-8")

    assert "datetime.now(" not in scorer
    assert "datetime.datetime.now(" not in calendar_source
    assert "datetime.now(UTC)" not in news_source
    assert "session_comp, session_tag = session_component()" in scorer
