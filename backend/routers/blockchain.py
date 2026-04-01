"""
Blockchain Audit Ledger Router
AGI Corporation 2026

Exposes the tamper-evident compliance audit chain via REST endpoints.
All assessment promotions, control updates, and key compliance events
are recorded in the chain.  Use /verify to confirm chain integrity.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.services import blockchain_service as bc

router = APIRouter()


@router.get("/chain", summary="List blockchain audit ledger entries")
async def get_chain(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Return audit ledger entries in chronological order.
    Each entry contains event_type, actor, payload, and cryptographic
    chain linkage fields (payload_hash, previous_hash, signature).
    """
    txs = await bc.get_chain(db, limit=limit, offset=offset)
    total = await bc.get_chain_length(db)
    return {
        "total_transactions": total,
        "limit": limit,
        "offset": offset,
        "transactions": [
            {
                "id": tx.id,
                "sequence": tx.sequence,
                "event_type": tx.event_type,
                "actor": tx.actor,
                "payload_hash": tx.payload_hash,
                "previous_hash": tx.previous_hash,
                "signature": tx.signature,
                "payload": tx.payload,
                "created_at": tx.created_at.isoformat(),
            }
            for tx in txs
        ],
    }


@router.get("/verify", summary="Verify blockchain audit chain integrity")
async def verify_chain(db: AsyncSession = Depends(get_db)):
    """
    Verify the tamper-evident integrity of the entire audit chain.

    Checks:
      - Sequence numbers are consecutive
      - Hash chain linkage (each record's previous_hash == prior record's payload_hash)
      - Payload hashes match stored data
      - HMAC signatures are valid

    Returns is_valid=True if no violations are found.
    """
    total = await bc.get_chain_length(db)
    is_valid, violations = await bc.verify_chain(db)
    return {
        "is_valid": is_valid,
        "total_transactions": total,
        "violations_found": len(violations),
        "violations": violations,
        "message": (
            "Chain integrity verified — no tampering detected."
            if is_valid
            else f"Chain integrity FAILED — {len(violations)} violation(s) detected."
        ),
    }


@router.get("/stats", summary="Blockchain ledger statistics")
async def chain_stats(db: AsyncSession = Depends(get_db)):
    """Return high-level ledger statistics."""
    total = await bc.get_chain_length(db)
    txs = await bc.get_chain(db, limit=total or 1)
    event_counts: dict = {}
    for tx in txs:
        event_counts[tx.event_type] = event_counts.get(tx.event_type, 0) + 1

    return {
        "total_transactions": total,
        "events_by_type": event_counts,
        "genesis_hash": bc.GENESIS_HASH,
    }
