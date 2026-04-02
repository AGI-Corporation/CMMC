"""
Blockchain Audit Service — CMMC Compliance Platform
AGI Corporation 2026

Provides a lightweight, tamper-evident append-only ledger for CMMC assessment
events using stdlib hashlib + hmac only (no external blockchain dependency).

Each transaction is signed with HMAC-SHA256 using the BLOCKCHAIN_SIGNING_KEY
environment variable. The chain integrity can be verified at any time via
verify_chain().

Environment variables:
    BLOCKCHAIN_SIGNING_KEY  — secret used to sign each transaction payload.
                              If not set, a runtime warning is emitted and an
                              insecure placeholder is used (dev/test only).
"""

import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

_SIGNING_KEY = os.getenv("BLOCKCHAIN_SIGNING_KEY", "")
if not _SIGNING_KEY:
    logger.warning(
        "BLOCKCHAIN_SIGNING_KEY is not set. "
        "Using insecure placeholder — do not use in production."
    )
    _SIGNING_KEY = "dev-insecure-key"


# ---------------------------------------------------------------------------
# DB model (imported into database.py Base)
# ---------------------------------------------------------------------------

# The actual SQLAlchemy model is defined in backend/db/database.py
# to keep the single-engine pattern. Here we expose the helper functions.


def _sign_payload(payload: str) -> str:
    """Return HMAC-SHA256 hex digest of payload using the signing key."""
    return hmac.new(
        _SIGNING_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def _hash_payload(payload: str) -> str:
    """Return SHA-256 hex digest of the JSON payload string."""
    return hashlib.sha256(payload.encode()).hexdigest()


async def record_event(
    db: AsyncSession,
    event_type: str,
    payload: Dict[str, Any],
    *,
    actor: str = "system",
) -> Dict[str, Any]:
    """
    Append a signed transaction to the blockchain ledger.

    Args:
        db:          Async SQLAlchemy session.
        event_type:  Human-readable category (e.g. 'assessment_submit', 'promote').
        payload:     Arbitrary dict of event data (will be JSON-serialised).
        actor:       Identity of the initiating actor.

    Returns:
        Dict summarising the new transaction (id, sequence, signature, timestamp).
    """
    from backend.db.database import BlockchainTransaction  # local import avoids circle

    # Determine the previous transaction's hash for chain linking
    result = await db.execute(
        select(BlockchainTransaction).order_by(
            BlockchainTransaction.sequence.desc()
        ).limit(1)
    )
    last_tx = result.scalar_one_or_none()
    previous_hash = last_tx.payload_hash if last_tx else "0" * 64
    next_sequence = (last_tx.sequence + 1) if last_tx else 1

    payload_with_meta = {
        **payload,
        "event_type": event_type,
        "actor": actor,
        "timestamp": datetime.now(UTC).isoformat(),
        "sequence": next_sequence,
    }
    payload_json = json.dumps(payload_with_meta, sort_keys=True)
    payload_hash = _hash_payload(payload_json)
    signature = _sign_payload(payload_json)

    tx = BlockchainTransaction(
        id=str(uuid.uuid4()),
        sequence=next_sequence,
        event_type=event_type,
        payload=payload_json,
        payload_hash=payload_hash,
        previous_hash=previous_hash,
        signature=signature,
        actor=actor,
        created_at=datetime.now(UTC),
    )
    db.add(tx)
    await db.flush()

    logger.info("blockchain: TX #%d event=%s actor=%s", next_sequence, event_type, actor)

    return {
        "id": tx.id,
        "sequence": tx.sequence,
        "event_type": event_type,
        "payload_hash": payload_hash,
        "signature": signature,
        "created_at": tx.created_at.isoformat(),
    }


async def verify_chain(db: AsyncSession) -> Dict[str, Any]:
    """
    Walk every transaction in sequence order and verify:
      1. Each payload_hash matches the stored payload.
      2. Each signature verifies against the stored payload.
      3. Each previous_hash matches the prior transaction's payload_hash.

    Returns a dict with 'valid' (bool) and 'broken_at_sequence' (int | None).
    """
    from backend.db.database import BlockchainTransaction

    result = await db.execute(
        select(BlockchainTransaction).order_by(BlockchainTransaction.sequence.asc())
    )
    txns: List[BlockchainTransaction] = result.scalars().all()

    prev_hash = "0" * 64
    for tx in txns:
        # Re-compute hash of stored payload
        computed_hash = _hash_payload(tx.payload)
        if computed_hash != tx.payload_hash:
            return {"valid": False, "broken_at_sequence": tx.sequence,
                    "reason": "payload_hash mismatch"}

        # Verify HMAC signature
        expected_sig = _sign_payload(tx.payload)
        if not hmac.compare_digest(expected_sig, tx.signature):
            return {"valid": False, "broken_at_sequence": tx.sequence,
                    "reason": "signature mismatch"}

        # Verify chain linkage
        if tx.previous_hash != prev_hash:
            return {"valid": False, "broken_at_sequence": tx.sequence,
                    "reason": "chain broken (previous_hash mismatch)"}

        prev_hash = tx.payload_hash

    return {"valid": True, "broken_at_sequence": None, "total_transactions": len(txns)}
