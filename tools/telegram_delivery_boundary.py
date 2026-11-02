#!/usr/bin/env python3
"""Canonical watcher adapter for crash-consistent Telegram text delivery.

The underlying delivery module durably records Telegram intent/outcome and emits
cycle evidence. Legacy cooldown/hash markers are *not* committed here because
Supabase publication is part of the outer GREEN delivery transaction. The
watcher core commits those markers only after Supabase succeeds. Therefore a
crash/failure after Telegram confirmation but before Supabase completion can be
reconciled on the next cycle without blindly resending the Telegram text.

Public presentation is transformed only at the final Telegram network boundary.
The durable decision identity, filters, thresholds, cooldown semantics and
Supabase transaction remain unchanged.
"""
from __future__ import annotations

import telegram_delivery as delivery
from telegram_public_presentation import format_public_signal


_ORIGINAL_SEND_REQUEST = delivery.send_request


def _public_send_request(message: str):
    """Send modern channel copy while preserving legacy decision identity.

    Presentation must never become a new trading gate. If formatting itself
    fails, fall back to the already-validated canonical text rather than losing
    an otherwise valid signal.
    """
    try:
        public_message = format_public_signal(message)
    except Exception:
        public_message = message
    return _ORIGINAL_SEND_REQUEST(public_message)


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
    delivery.send_request = _public_send_request
    delivery.finalize_confirmed_delivery = _finalize_after_telegram_only
    return delivery.main()


if __name__ == "__main__":
    raise SystemExit(main())
