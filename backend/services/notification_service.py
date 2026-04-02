"""
Notification Service — CMMC Compliance Platform
AGI Corporation 2026

Stdlib-only webhook dispatcher and in-process event log.

The service maintains a rolling in-memory event log (last 500 events) that
can be retrieved by GET /api/assessment/notifications. Optionally dispatches
events to an external webhook (WEBHOOK_URL env var) signed with HMAC-SHA256
using WEBHOOK_SECRET.

Environment variables:
    WEBHOOK_URL     — Target URL for outbound webhook POSTs (optional).
    WEBHOOK_SECRET  — HMAC-SHA256 signing secret for webhook payloads.
                      A warning is emitted at startup if WEBHOOK_URL is set
                      without WEBHOOK_SECRET.
"""

import hashlib
import hmac
import json
import logging
import os
import urllib.request
import urllib.error
from collections import deque
from datetime import UTC, datetime
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")
_WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET")

if _WEBHOOK_URL and not _WEBHOOK_SECRET:
    logger.warning(
        "WEBHOOK_URL is set but WEBHOOK_SECRET is missing. "
        "Outbound webhooks will be sent WITHOUT HMAC signatures."
    )

# ---------------------------------------------------------------------------
# In-process event log (last 500 events)
# ---------------------------------------------------------------------------

_EVENT_LOG: Deque[Dict[str, Any]] = deque(maxlen=500)


def _append_event(event: Dict[str, Any]) -> None:
    _EVENT_LOG.append(event)


def get_event_log(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Return recent events from the in-process log, newest first.

    Args:
        event_type: Filter to events of this type (e.g. 'poam_flagged').
        severity:   Filter to this severity level ('info', 'warning', 'critical').
        limit:      Maximum number of events to return (default 100, max 500).
    """
    events = list(_EVENT_LOG)
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    if severity:
        events = [e for e in events if e.get("severity") == severity]
    # Return newest first, capped at limit
    return list(reversed(events[-limit:]))


# ---------------------------------------------------------------------------
# Webhook dispatcher (fire-and-forget; best-effort)
# ---------------------------------------------------------------------------

def _sign_webhook(payload_bytes: bytes) -> Optional[str]:
    if not _WEBHOOK_SECRET:
        return None
    return hmac.new(
        _WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def _dispatch_webhook(event: Dict[str, Any]) -> None:
    """Send event to WEBHOOK_URL (best-effort, no retry)."""
    if not _WEBHOOK_URL:
        return
    try:
        body = json.dumps(event).encode()
        headers = {"Content-Type": "application/json"}
        sig = _sign_webhook(body)
        if sig:
            headers["X-CMMC-Signature"] = f"sha256={sig}"
        req = urllib.request.Request(_WEBHOOK_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5):
            pass
        logger.debug("webhook dispatched event_type=%s", event.get("event_type"))
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("webhook dispatch failed: %s", exc)


def _notify(event_type: str, severity: str, data: Dict[str, Any]) -> None:
    """Core notification routine: log + optionally webhook."""
    event = {
        "event_type": event_type,
        "severity": severity,
        "timestamp": datetime.now(UTC).isoformat(),
        **data,
    }
    _append_event(event)
    _dispatch_webhook(event)


# ---------------------------------------------------------------------------
# Public notification helpers
# ---------------------------------------------------------------------------

def notify_poam_flagged(
    control_id: str,
    status: str,
    assessor: str = "system",
    notes: str = "",
) -> None:
    """
    Notify that a control has been auto-flagged as requiring a POA&M.

    Called from POST /api/assessment/submit when `poam_required` is auto-set.
    """
    _notify(
        event_type="poam_flagged",
        severity="warning",
        data={
            "control_id": control_id,
            "status": status,
            "assessor": assessor,
            "notes": notes,
        },
    )


def notify_agent_run_completed(
    run_id: str,
    agent_type: str,
    status: str,
    controls_evaluated: List[str],
) -> None:
    """Notify that an agent run has completed."""
    _notify(
        event_type="agent_run_completed",
        severity="info",
        data={
            "run_id": run_id,
            "agent_type": agent_type,
            "status": status,
            "controls_evaluated": controls_evaluated,
            "count": len(controls_evaluated),
        },
    )


def notify_blockchain_recorded(
    transaction_id: str,
    sequence: int,
    event_type: str,
) -> None:
    """Notify that an event was appended to the blockchain ledger."""
    _notify(
        event_type="blockchain_recorded",
        severity="info",
        data={
            "transaction_id": transaction_id,
            "sequence": sequence,
            "blockchain_event_type": event_type,
        },
    )


def notify_assessment_promoted(
    run_id: str,
    agent_type: str,
    assessments_created: int,
) -> None:
    """Notify that agent run findings were promoted to official assessment records."""
    _notify(
        event_type="assessment_promoted",
        severity="info",
        data={
            "run_id": run_id,
            "agent_type": agent_type,
            "assessments_created": assessments_created,
        },
    )
