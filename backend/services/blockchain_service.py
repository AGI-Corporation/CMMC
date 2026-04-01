"""
Blockchain Audit Ledger Service
AGI Corporation 2026

Provides a tamper-evident audit trail for compliance events using a simple
SHA-256 Merkle-chained ledger backed by the `blockchain_transactions` table.

Each transaction stores:
  - SHA-256 hash of the JSON payload
  - Hash of the previous transaction ("genesis" for the first)
  - HMAC-SHA256 signature keyed by BLOCKCHAIN_SIGNING_KEY env var
  - Full payload for auditability

The chain can be verified at any time by recomputing hashes and signatures.
No external dependencies — uses stdlib hashlib and hmac only.

Compliance mapping:
  AU.2.041 - Audit logging
  AU.2.042 - Audit event review
  AU.3.045 - Protect audit logs from unauthorized access (via HMAC signing)
  CA.2.157 - Security assessment documentation
"""

import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import BlockchainTransaction

# ─── Configuration ─────────────────────────────────────────────────────────────
import logging as _logging

_SIGNING_KEY_ENV = os.getenv("BLOCKCHAIN_SIGNING_KEY", "")
if not _SIGNING_KEY_ENV:
    _logging.getLogger(__name__).warning(
        "BLOCKCHAIN_SIGNING_KEY is not set. Using a weak default key. "
        "Set this environment variable to a strong secret in production."
    )
    _SIGNING_KEY_ENV = "default-dev-signing-key"

SIGNING_KEY = _SIGNING_KEY_ENV.encode()

GENESIS_HASH = "0" * 64  # Sentinel previous_hash for the first transaction


# ─── Core helpers ─────────────────────────────────────────────────────────────


def _sha256(data: str) -> str:
    """Compute SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode()).hexdigest()


def _hmac_sign(payload_hash: str, previous_hash: str) -> str:
    """Sign the concatenation of payload_hash + previous_hash using HMAC-SHA256."""
    message = (payload_hash + previous_hash).encode()
    return hmac.new(SIGNING_KEY, message, hashlib.sha256).hexdigest()


def _payload_hash(payload: Dict[str, Any]) -> str:
    """Deterministically hash a JSON payload (sorted keys)."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return _sha256(serialized)


# ─── Public API ───────────────────────────────────────────────────────────────


async def record_event(
    db: AsyncSession,
    event_type: str,
    actor: str,
    payload: Dict[str, Any],
) -> BlockchainTransaction:
    """
    Append a new authenticated transaction to the ledger.

    Parameters
    ----------
    db:         SQLAlchemy async session
    event_type: Short descriptor of the event (e.g. "assessment_promoted")
    actor:      Who triggered the event (agent name, "manual", etc.)
    payload:    Arbitrary JSON-serializable event data

    Returns the persisted BlockchainTransaction.
    """
    # Find the latest transaction to chain from
    latest_query = (
        select(BlockchainTransaction)
        .order_by(BlockchainTransaction.sequence.desc())
        .limit(1)
    )
    result = await db.execute(latest_query)
    latest = result.scalar_one_or_none()

    if latest is None:
        seq = 1
        previous_hash = GENESIS_HASH
    else:
        seq = latest.sequence + 1
        previous_hash = latest.payload_hash

    p_hash = _payload_hash(payload)
    sig = _hmac_sign(p_hash, previous_hash)

    tx = BlockchainTransaction(
        id=str(uuid.uuid4()),
        sequence=seq,
        event_type=event_type,
        actor=actor,
        payload_hash=p_hash,
        previous_hash=previous_hash,
        signature=sig,
        payload=payload,
        created_at=datetime.now(UTC),
    )
    db.add(tx)
    # Caller is responsible for committing
    return tx


async def get_chain(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
) -> List[BlockchainTransaction]:
    """Return ledger entries in chronological order with pagination."""
    query = (
        select(BlockchainTransaction)
        .order_by(BlockchainTransaction.sequence.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_chain_length(db: AsyncSession) -> int:
    """Return total number of transactions in the chain."""
    result = await db.execute(
        select(func.count(BlockchainTransaction.id))
    )
    return result.scalar_one() or 0


async def verify_chain(db: AsyncSession) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Verify the integrity of the entire chain.

    Checks:
      1. Sequence numbers are consecutive starting at 1.
      2. Each transaction's previous_hash equals the prior transaction's payload_hash.
      3. Each transaction's payload_hash matches the stored payload.
      4. Each HMAC signature is valid.

    Returns (is_valid, list_of_violations).
    """
    query = select(BlockchainTransaction).order_by(
        BlockchainTransaction.sequence.asc()
    )
    result = await db.execute(query)
    transactions = list(result.scalars().all())

    violations: List[Dict[str, Any]] = []
    expected_previous = GENESIS_HASH

    for i, tx in enumerate(transactions):
        # 1. Sequence check
        expected_seq = i + 1
        if tx.sequence != expected_seq:
            violations.append(
                {
                    "tx_id": tx.id,
                    "sequence": tx.sequence,
                    "issue": f"Sequence gap: expected {expected_seq}, got {tx.sequence}.",
                }
            )

        # 2. Chain linkage
        if tx.previous_hash != expected_previous:
            violations.append(
                {
                    "tx_id": tx.id,
                    "sequence": tx.sequence,
                    "issue": "Chain broken: previous_hash mismatch.",
                }
            )

        # 3. Payload integrity
        recomputed_hash = _payload_hash(tx.payload)
        if recomputed_hash != tx.payload_hash:
            violations.append(
                {
                    "tx_id": tx.id,
                    "sequence": tx.sequence,
                    "issue": "Payload tampered: hash does not match stored payload.",
                }
            )

        # 4. Signature validity
        expected_sig = _hmac_sign(tx.payload_hash, tx.previous_hash)
        if not hmac.compare_digest(tx.signature, expected_sig):
            violations.append(
                {
                    "tx_id": tx.id,
                    "sequence": tx.sequence,
                    "issue": "Signature invalid: HMAC verification failed.",
                }
            )

        # Advance chain pointer
        expected_previous = tx.payload_hash

    return (len(violations) == 0, violations)
