#!/usr/bin/env python3
"""Fail-closed R5 proof that production Telegram/Supabase side effects are sandboxed."""
from __future__ import annotations

import http.client
import json
import os
import re
import socket
import sys
import urllib.request
from pathlib import Path

R5_SENTINEL = "R5_SHADOW_NO_NETWORK"
SENSITIVE_KEYS = (
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_TOKEN", "BOT_TOKEN",
    "TELEGRAM_CHAT_ID", "CHAT_ID", "TG_CHAT_ID",
    "SUPABASE_SERVICE_KEY", "BOTA_HEALTH_INGEST_SECRET",
)
EXPECTED_ENV = {
    **{key: R5_SENTINEL for key in SENSITIVE_KEYS},
    "TELEGRAM_ENABLED": "1",
    "DRY_RUN_MODE": "false",
    "HEARTBEAT_DRY_RUN": "1",
    "DAILY_SUMMARY_GATE_DRY_RUN": "1",
    "DAILY_SUMMARY_SEND": "0",
    "RUNTIME_HEALTH_PUSH_DRY_RUN": "1",
}
CONFIG_PATHS = (
    ".env", ".env.runtime", "config/tele.env", "config/strategy.env",
    "config/bota_health_ingest.env",
)
ENV_LINE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _scan_release_configs(root: Path) -> list[str]:
    found: list[str] = []
    sensitive = set(SENSITIVE_KEYS)
    for relative in CONFIG_PATHS:
        path = root / relative
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError):
            found.append(f"{relative}:UNREADABLE")
            continue
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = ENV_LINE.fullmatch(line)
            if match is None:
                continue
            key, value = match.groups()
            if key in sensitive and _unquote(value).strip() not in {"", R5_SENTINEL}:
                found.append(f"{relative}:{key}")
    return sorted(set(found))


def _module_path() -> Path | None:
    module = sys.modules.get("sitecustomize")
    raw = getattr(module, "__file__", None) if module is not None else None
    if not raw:
        return None
    try:
        return Path(raw).resolve()
    except OSError:
        return None


def _ledger_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _probes(ledger: Path) -> dict[str, bool]:
    checks = {"urllib_telegram_synthetic": False,
              "http_client_supabase_synthetic": False,
              "dns_fail_closed": False,
              "suppression_ledger_grew": False}
    before = _ledger_size(ledger)
    request = urllib.request.Request(
        "https://api.telegram.org/botR5_SENTINEL/sendMessage",
        data=b"chat_id=R5_SENTINEL&text=preflight",
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=1) as response:
            payload = json.loads(response.read().decode("utf-8"))
            checks["urllib_telegram_synthetic"] = (
                response.getcode() == 200 and payload.get("ok") is True
                and payload.get("result", {}).get("message_id") == -1
            )
    except Exception:
        pass

    connection = http.client.HTTPSConnection("r5-preflight.supabase.co", timeout=1)
    try:
        connection.request("GET", "/rest/v1/signals")
        response = connection.getresponse()
        checks["http_client_supabase_synthetic"] = (
            response.status == 200 and response.read() == b"[]"
        )
    except Exception:
        pass
    finally:
        connection.close()

    try:
        socket.getaddrinfo("api.telegram.org", 443)
    except socket.gaierror:
        checks["dns_fail_closed"] = True
    except Exception:
        pass
    checks["suppression_ledger_grew"] = _ledger_size(ledger) > before
    return checks


def evaluate() -> dict[str, object]:
    required = os.environ.get("BOTA_REQUIRE_R5_SHADOW") == "1"
    active = os.environ.get("BOTA_R5_SHADOW") == "1"
    if not required and not active:
        return {"schema_version": "1.0", "healthy": True, "r5_shadow": False,
                "side_effects_enabled": True, "checks": {"r5_required": False}}

    root = Path(os.environ.get("BOTA_CODE_ROOT") or os.environ.get("BOTA_ROOT")
                or Path(__file__).resolve().parents[1]).resolve()
    mutable = Path(os.environ.get("BOTA_MUTABLE_ROOT", "/var/lib/bota")).expanduser()
    ledger = mutable / "state" / "r5_side_effects.jsonl"
    expected_module = (root / "r5_bootstrap" / "sitecustomize.py").resolve()
    actual_module = _module_path()
    checks: dict[str, object] = {
        "r5_required": required,
        "r5_active": active,
        "bootstrap_active": os.environ.get("BOTA_R5_BOOTSTRAP_ACTIVE") == "1",
        "bootstrap_module_exact": actual_module == expected_module,
        "production_secret_present": os.environ.get("BOTA_R5_PRODUCTION_SECRET_PRESENT") == "1",
        "forced_environment_exact": all(os.environ.get(k) == v for k, v in EXPECTED_ENV.items()),
        "release_config_secret_locations": _scan_release_configs(root),
    }
    if required and not active:
        checks["failure"] = "r5_shadow_required_but_inactive"
    elif not checks["bootstrap_active"] or not checks["bootstrap_module_exact"]:
        checks["failure"] = "r5_bootstrap_not_proven"
    elif checks["production_secret_present"]:
        checks["failure"] = "production_secret_detected_in_process_environment"
    elif checks["release_config_secret_locations"]:
        checks["failure"] = "production_secret_detected_in_release_config"
    elif not checks["forced_environment_exact"]:
        checks["failure"] = "r5_forced_environment_mismatch"
    else:
        checks.update(_probes(ledger))
        if not all(checks.get(key) is True for key in (
            "urllib_telegram_synthetic", "http_client_supabase_synthetic",
            "dns_fail_closed", "suppression_ledger_grew",
        )):
            checks["failure"] = "r5_transport_suppression_probe_failed"

    healthy = "failure" not in checks
    return {"schema_version": "1.0", "healthy": healthy, "r5_shadow": active,
            "side_effects_enabled": False, "checks": checks}


def main() -> int:
    result = evaluate()
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
