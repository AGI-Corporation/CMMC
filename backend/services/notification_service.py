"""
Notification / Webhook Service
AGI Corporation 2026

Dispatches outbound notifications for key compliance events:
  - POAM flagged during assessment submit (control not_implemented / partial)
  - High-severity agent findings
  - Blockchain integrity alert

Configuration (env vars):
  WEBHOOK_URL       - HTTPS URL to POST compliance events to (optional).
                      When unset, events are logged locally only.
  WEBHOOK_SECRET    - Shared secret for HMAC-SHA256 request signing (optional).
  NOTIFY_ENABLED    - Set to "false" to suppress all outbound calls (default: "true").

Payload schema (all event types):
  {
    "event_type":   str,   # "poam_flagged" | "agent_finding" | "blockchain_alert"
    "severity":     str,   # "critical" | "high" | "medium" | "low" | "info"
    "control_id":   str | null,
    "agent":        str | null,
    "message":      str,
    "timestamp":    str,   # ISO-8601 UTC
    "metadata":     dict,  # event-specific payload
  }

Compliance mapping:
  IR.2.092 - Establish operational incident-handling capability
  IR.2.093 - Track, document, and report incidents
  CA.2.158 - Develop and implement plans of action and milestones
  AU.2.042 - Review and update logged events
"""

import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL", "")
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
NOTIFY_ENABLED: bool = os.getenv("NOTIFY_ENABLED", "true").lower() == "true"

# Warn at import time if a webhook URL is configured without a signing secret,
# so that misconfigurations are visible in startup logs rather than silently
# sending unsigned payloads in production.
if WEBHOOK_URL and not WEBHOOK_SECRET:
    logger.warning(
        "WEBHOOK_URL is set but WEBHOOK_SECRET is empty. "
        "Outbound compliance event payloads will be sent without a valid HMAC signature. "
        "Set WEBHOOK_SECRET to enable request signing (X-CMMC-Signature header)."
    )

# In-memory event log (bounded ring-buffer, used when no webhook URL is set)
_MAX_LOG_ENTRIES = 500
_event_log: list = []


def _sign_payload(body: bytes) -> str:
    """Compute HMAC-SHA256 hex signature of the raw payload bytes.
    Returns an empty-keyed HMAC when no WEBHOOK_SECRET is configured;
    the receiver should treat an absent or zero-key signature as unverified.
    """
    key = WEBHOOK_SECRET.encode() if WEBHOOK_SECRET else b""
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def _local_log(event: Dict[str, Any]) -> None:
    """Store event in the in-process ring buffer."""
    global _event_log
    _event_log.append(event)
    if len(_event_log) > _MAX_LOG_ENTRIES:
        _event_log = _event_log[-_MAX_LOG_ENTRIES:]


def _dispatch(event: Dict[str, Any]) -> bool:
    """
    Send ``event`` to the configured webhook, or record it locally.
    Returns True if the notification was successfully delivered (or logged locally).
    """
    if not NOTIFY_ENABLED:
        return True

    _local_log(event)

    if not WEBHOOK_URL:
        logger.info(
            "compliance_event type=%s severity=%s control=%s msg=%s",
            event.get("event_type"),
            event.get("severity"),
            event.get("control_id"),
            event.get("message"),
        )
        return True

    body = json.dumps(event, default=str).encode()
    signature = _sign_payload(body)

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-CMMC-Signature": f"sha256={signature}",
            "X-CMMC-Event": event.get("event_type", "unknown"),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status < 300:
                return True
            logger.warning(
                "Webhook returned HTTP %s for event %s",
                resp.status,
                event.get("event_type"),
            )
            return False
    except urllib.error.URLError as exc:
        logger.warning(
            "Webhook delivery failed for event %s: %s",
            event.get("event_type"),
            exc,
        )
        return False


# ── Public API ─────────────────────────────────────────────────────────────────


def notify_poam_flagged(
    control_id: str,
    status: str,
    confidence: float,
    assessor: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    """
    Fire a 'poam_flagged' notification when an assessment submit marks a control
    as requiring a Plan of Action & Milestones.

    Maps to CA.2.158 (POA&M) and IR.2.092 (incident notification).
    """
    severity = "critical" if confidence < 0.2 else "high" if confidence < 0.5 else "medium"
    event = {
        "event_type": "poam_flagged",
        "severity": severity,
        "control_id": control_id,
        "agent": assessor or "assessment",
        "message": (
            f"Control {control_id} flagged for POA&M: status={status}, "
            f"confidence={confidence:.2f}"
        ),
        "timestamp": datetime.now(UTC).isoformat(),
        "metadata": {
            "status": status,
            "confidence": confidence,
            "assessor": assessor,
            "notes": notes,
        },
    }
    return _dispatch(event)


def notify_agent_finding(
    agent: str,
    control_id: Optional[str],
    severity: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Fire an 'agent_finding' notification for high-severity agent assessment results.

    Maps to IR.2.093 (track and report incidents) and AU.2.042 (review logged events).
    """
    event = {
        "event_type": "agent_finding",
        "severity": severity,
        "control_id": control_id,
        "agent": agent,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
        "metadata": metadata or {},
    }
    return _dispatch(event)


def notify_blockchain_alert(
    message: str,
    chain_length: int,
    last_hash: Optional[str] = None,
) -> bool:
    """
    Fire a 'blockchain_alert' notification when chain integrity verification fails.

    Maps to AU.3.045 (protect audit logs).
    """
    event = {
        "event_type": "blockchain_alert",
        "severity": "critical",
        "control_id": None,
        "agent": "blockchain",
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
        "metadata": {
            "chain_length": chain_length,
            "last_hash": last_hash,
        },
    }
    return _dispatch(event)


def get_event_log(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> list:
    """
    Return recent notification events from the in-process log.
    Optionally filter by event_type and/or severity.
    """
    events = list(reversed(_event_log))  # newest first
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    if severity:
        events = [e for e in events if e.get("severity") == severity]
    return events[:limit]
