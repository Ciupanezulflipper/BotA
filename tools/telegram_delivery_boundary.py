#!/usr/bin/env python3
"""Canonical watcher adapter for crash-consistent Telegram text delivery.

The underlying delivery module durably records Telegram intent/outcome and emits
cycle evidence.  Legacy cooldown/hash markers are *not* committed here because
Supabase publication is part of the outer GREEN delivery transaction.  The
watcher core commits those markers only after Supabase succeeds.  Therefore a
crash/failure after Telegram confirmation but before Supabase completion can be
reconciled on the next cycle without blindly resending the Telegram text.
"""
from __future__ import annotations

import telegram_delivery as delivery


def _finalize_after_telegram_only(
    identity: dict[str, str],
    provenance: dict[str, object],
    cycle_status: str,
    detail: dict[str, object],
) -> bool:
    """Persist only current-cycle Telegram evidence; defer legacy commit markers."""
    del provenance  # provenance is already durable in telegram_delivery state.
    return delivery.emit_cycle_result(identity, cycle_status, detail)


def main() -> int:
    delivery.finalize_confirmed_delivery = _finalize_after_telegram_only
    return delivery.main()


if __name__ == "__main__":
    raise SystemExit(main())
