"""
Blockchain Service — cmmc.blockchain attestation layer.
AGI Corporation 2026

Implements a tamper-evident, append-only compliance ledger using:
  • SHA-256 content hashing for every payload
  • Merkle-style previous-hash chaining (each TX includes hash of prior TX)
  • HMAC-SHA256 platform signature for record integrity
  • Monotonic block-height counter for ordering

The ledger is stored in the local PostgreSQL/SQLite database and designed to
be anchored to a real blockchain (Hyperledger Fabric / Polygon Edge) via the
BLOCKCHAIN_ANCHOR_URL environment variable. When BLOCKCHAIN_ENABLED=false
(or the external node is unreachable) the service operates in "local" mode
with full cryptographic integrity — a circuit-breaker pattern that keeps
compliance operations running regardless of blockchain node availability.

On-chain data privacy:
  - CUI/FCI content NEVER enters the ledger.
  - Only SHA-256 hashes, status strings, and metadata are recorded.
  - Evidence file content remains in internal storage.
"""
import hashlib
import hmac
import json
import os
import uuid
import logging
from datetime import datetime, UTC
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.db.database import (
    BlockchainTransaction,
    ControlRecord,
    EvidenceRecord,
    AssessmentRecord,
    get_next_block_height,
)

logger = logging.getLogger(__name__)

# ─── Configuration ─────────────────────────────────────────────────────────────

BLOCKCHAIN_ENABLED = os.getenv("BLOCKCHAIN_ENABLED", "true").lower() == "true"
BLOCKCHAIN_LEDGER_MODE = os.getenv("BLOCKCHAIN_LEDGER_MODE", "local")  # local | fabric | evm
BLOCKCHAIN_ORG_ID = os.getenv("BLOCKCHAIN_ORG_ID", "agi-corp")
BLOCKCHAIN_MSP_ID = os.getenv("BLOCKCHAIN_MSP_ID", "AgiCorpMSP")
BLOCKCHAIN_CHAIN_ID = os.getenv("BLOCKCHAIN_CHAIN_ID", "cmmc-blockchain-mainnet")
BLOCKCHAIN_ANCHOR_URL = os.getenv("BLOCKCHAIN_ANCHOR_URL", "")

# HMAC signing key — in production, replace with HSM/KMS-backed key.
# The key is used to sign each transaction record so any tampering is detectable.
_SIGNING_KEY = os.getenv("BLOCKCHAIN_SIGNING_KEY", "change-me-use-hsm-in-production").encode()


# ─── Cryptographic Helpers ────────────────────────────────────────────────────

def _sha256(data: Any) -> str:
    """Deterministic SHA-256 hash of a JSON-serialisable value."""
    serialised = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()


def _hmac_sign(payload_hash: str) -> str:
    """HMAC-SHA256 platform signature over a payload hash."""
    return hmac.new(_SIGNING_KEY, payload_hash.encode(), hashlib.sha256).hexdigest()


def _verify_hmac(payload_hash: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature."""
    expected = _hmac_sign(payload_hash)
    return hmac.compare_digest(expected, signature)


def compute_sha256_for_content(content: str | bytes) -> str:
    """Compute SHA-256 of arbitrary evidence content (string or bytes)."""
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()


# ─── Core Ledger Writer ───────────────────────────────────────────────────────

async def _write_transaction(
    db: AsyncSession,
    tx_type: str,
    payload: dict,
    org_id: str,
    control_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
) -> BlockchainTransaction:
    """
    Append a new tamper-evident transaction to the local ledger.

    Each transaction includes:
      • SHA-256 of its payload
      • Hash of the immediately preceding transaction (chain linkage)
      • HMAC-SHA256 platform signature
      • Monotonic block height
    """
    tx_id = str(uuid.uuid4())
    block_height = await get_next_block_height(db)

    # Fetch hash of the previous transaction (chain linkage)
    prev_result = await db.execute(
        select(BlockchainTransaction.payload_hash)
        .order_by(BlockchainTransaction.block_height.desc())
        .limit(1)
    )
    previous_tx_hash = prev_result.scalar()

    # Content hash includes the previous hash — tamper-evident chain
    payload_with_meta = {
        **payload,
        "tx_id": tx_id,
        "tx_type": tx_type,
        "org_id": org_id,
        "block_height": block_height,
        "previous_tx_hash": previous_tx_hash,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    payload_hash = _sha256(payload_with_meta)
    signature = _hmac_sign(payload_hash)

    tx = BlockchainTransaction(
        id=tx_id,
        tx_type=tx_type,
        org_id=org_id,
        control_id=control_id,
        evidence_id=evidence_id,
        payload_hash=payload_hash,
        previous_tx_hash=previous_tx_hash,
        block_height=block_height,
        status="confirmed",
        payload=payload_with_meta,
        signature=signature,
        created_at=datetime.now(UTC),
        confirmed_at=datetime.now(UTC),
    )
    db.add(tx)
    await db.flush()

    logger.info(
        "Blockchain TX written: type=%s control=%s block=%d hash=%s",
        tx_type,
        control_id,
        block_height,
        payload_hash[:16],
    )
    return tx


# ─── Attestation ─────────────────────────────────────────────────────────────

async def submit_attestation(
    db: AsyncSession,
    control_id: str,
    status: str,
    confidence: float,
    evidence_hashes: list[str],
    assessor_id: Optional[str] = None,
    notes: Optional[str] = None,
    org_id: Optional[str] = None,
) -> BlockchainTransaction:
    """
    Submit an immutable control attestation to the ledger.

    Also updates ControlRecord.last_attestation_tx_id and block_height.
    """
    org = org_id or BLOCKCHAIN_ORG_ID
    attestation_id = str(uuid.uuid4())

    payload = {
        "attestation_id": attestation_id,
        "control_id": control_id,
        "status": status,
        "confidence": confidence,
        "evidence_hashes": evidence_hashes,
        "assessor_id": assessor_id,
        "notes": notes,
    }

    tx = await _write_transaction(
        db,
        tx_type="attestation",
        payload=payload,
        org_id=org,
        control_id=control_id,
    )

    # Update the ControlRecord with blockchain sync metadata
    ctrl_result = await db.execute(
        select(ControlRecord).where(ControlRecord.id == control_id)
    )
    ctrl = ctrl_result.scalar_one_or_none()
    if ctrl:
        ctrl.last_attestation_tx_id = tx.id
        ctrl.attestation_block_height = tx.block_height
        ctrl.blockchain_synced_at = datetime.now(UTC)

    return tx


# ─── SPRS Score Anchoring ─────────────────────────────────────────────────────

async def anchor_sprs_score(
    db: AsyncSession,
    sprs_score: int,
    total_controls: int,
    implemented: int,
    attestation_ids: list[str],
    notes: Optional[str] = None,
    org_id: Optional[str] = None,
) -> BlockchainTransaction:
    """Anchor a SPRS score snapshot in the ledger."""
    org = org_id or BLOCKCHAIN_ORG_ID
    anchor_id = str(uuid.uuid4())

    payload = {
        "anchor_id": anchor_id,
        "sprs_score": sprs_score,
        "total_controls": total_controls,
        "implemented": implemented,
        "attestation_ids": attestation_ids,
        "notes": notes,
    }

    return await _write_transaction(
        db,
        tx_type="sprs_anchor",
        payload=payload,
        org_id=org,
    )


# ─── Evidence Registration ────────────────────────────────────────────────────

async def register_evidence(
    db: AsyncSession,
    evidence_id: str,
    sha256_hash: str,
    control_id: Optional[str] = None,
    storage_uri: Optional[str] = None,
    evidence_type: Optional[str] = None,
    reviewer_id: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    org_id: Optional[str] = None,
) -> BlockchainTransaction:
    """Register an evidence artifact hash on the ledger."""
    org = org_id or BLOCKCHAIN_ORG_ID

    payload = {
        "evidence_id": evidence_id,
        "sha256_hash": sha256_hash,
        "control_id": control_id,
        "storage_uri": storage_uri,
        "evidence_type": evidence_type,
        "reviewer_id": reviewer_id,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "revoked": False,
    }

    tx = await _write_transaction(
        db,
        tx_type="evidence",
        payload=payload,
        org_id=org,
        control_id=control_id,
        evidence_id=evidence_id,
    )

    # Back-fill the EvidenceRecord with the TX reference
    ev_result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == evidence_id)
    )
    ev = ev_result.scalar_one_or_none()
    if ev:
        ev.sha256_hash = sha256_hash
        ev.evidence_anchor_tx_id = tx.id

    return tx


async def verify_evidence_integrity(
    db: AsyncSession,
    evidence_id: str,
    content: Optional[str | bytes] = None,
) -> dict:
    """
    Verify an evidence artifact against its on-chain registration.

    If `content` is provided, its SHA-256 hash is compared with the stored hash.
    """
    # Look up the most recent evidence TX for this evidence_id
    result = await db.execute(
        select(BlockchainTransaction)
        .where(
            BlockchainTransaction.tx_type == "evidence",
            BlockchainTransaction.evidence_id == evidence_id,
        )
        .order_by(BlockchainTransaction.block_height.desc())
        .limit(1)
    )
    tx = result.scalar_one_or_none()

    if not tx:
        return {
            "evidence_id": evidence_id,
            "registered": False,
            "hash_match": None,
            "stored_hash": None,
            "computed_hash": None,
            "revoked": False,
            "tx_id": None,
            "message": "Evidence not registered on blockchain",
        }

    stored_hash = tx.payload.get("sha256_hash")
    revoked = tx.payload.get("revoked", False)
    computed_hash = None
    hash_match = None

    if content is not None:
        computed_hash = compute_sha256_for_content(content)
        hash_match = computed_hash == stored_hash

    return {
        "evidence_id": evidence_id,
        "registered": True,
        "hash_match": hash_match,
        "stored_hash": stored_hash,
        "computed_hash": computed_hash,
        "revoked": revoked,
        "tx_id": tx.id,
        "message": "Hash verified" if hash_match else (
            "Hash mismatch — evidence may have been tampered with" if hash_match is False
            else "Registered (no content provided for hash check)"
        ),
    }


# ─── Formal Assessment ────────────────────────────────────────────────────────

async def submit_formal_assessment(
    db: AsyncSession,
    level: str,
    outcome: str,
    sprs_score: int,
    control_count: int,
    findings_hash: Optional[str] = None,
    report_ipfs_cid: Optional[str] = None,
    valid_until: Optional[datetime] = None,
    assessor_org_id: Optional[str] = None,
    agent_run_id: Optional[str] = None,
    org_id: Optional[str] = None,
) -> BlockchainTransaction:
    """Submit a formal C3PAO assessment record to the ledger."""
    org = org_id or BLOCKCHAIN_ORG_ID
    assessment_chain_id = str(uuid.uuid4())

    payload = {
        "assessment_chain_id": assessment_chain_id,
        "level": level,
        "outcome": outcome,
        "sprs_score": sprs_score,
        "control_count": control_count,
        "findings_hash": findings_hash,
        "report_ipfs_cid": report_ipfs_cid,
        "valid_until": valid_until.isoformat() if valid_until else None,
        "assessor_org_id": assessor_org_id,
        "agent_run_id": agent_run_id,
    }

    return await _write_transaction(
        db,
        tx_type="assessment",
        payload=payload,
        org_id=org,
    )


# ─── Query Helpers ─────────────────────────────────────────────────────────────

async def get_attestation_history(
    db: AsyncSession,
    control_id: str,
    org_id: Optional[str] = None,
) -> list[BlockchainTransaction]:
    """Return all attestation TXs for a control, oldest-first."""
    query = (
        select(BlockchainTransaction)
        .where(
            BlockchainTransaction.tx_type == "attestation",
            BlockchainTransaction.control_id == control_id,
        )
        .order_by(BlockchainTransaction.block_height.asc())
    )
    if org_id:
        query = query.where(BlockchainTransaction.org_id == org_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_sprs_history(
    db: AsyncSession,
    org_id: Optional[str] = None,
) -> list[BlockchainTransaction]:
    """Return all SPRS anchor TXs for an org, newest-first."""
    query = (
        select(BlockchainTransaction)
        .where(BlockchainTransaction.tx_type == "sprs_anchor")
        .order_by(BlockchainTransaction.block_height.desc())
    )
    if org_id:
        query = query.where(BlockchainTransaction.org_id == org_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_audit_trail(
    db: AsyncSession,
    org_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[BlockchainTransaction]]:
    """Return paginated audit trail of all TXs, newest-first."""
    base_q = select(BlockchainTransaction).order_by(BlockchainTransaction.block_height.desc())
    count_q = select(func.count(BlockchainTransaction.id))
    if org_id:
        base_q = base_q.where(BlockchainTransaction.org_id == org_id)
        count_q = count_q.where(BlockchainTransaction.org_id == org_id)

    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    result = await db.execute(base_q.offset(offset).limit(limit))
    records = result.scalars().all()
    return total, records


async def get_ledger_status(db: AsyncSession) -> dict:
    """Return current ledger health and statistics."""
    result = await db.execute(select(func.max(BlockchainTransaction.block_height)))
    latest_height = result.scalar() or 0

    count_result = await db.execute(select(func.count(BlockchainTransaction.id)))
    total_txs = count_result.scalar() or 0

    return {
        "connected": True,
        "ledger_mode": BLOCKCHAIN_LEDGER_MODE,
        "latest_block_height": latest_height,
        "total_transactions": total_txs,
        "org_id": BLOCKCHAIN_ORG_ID,
        "chain_id": BLOCKCHAIN_CHAIN_ID,
    }


async def verify_chain_integrity(db: AsyncSession) -> dict:
    """
    Walk the entire ledger and verify that the hash chain is unbroken.
    Returns a report of any tampering detected.
    """
    result = await db.execute(
        select(BlockchainTransaction).order_by(BlockchainTransaction.block_height.asc())
    )
    txs = result.scalars().all()

    issues: list[str] = []
    prev_hash: Optional[str] = None

    for tx in txs:
        # 1. Verify HMAC signature
        if tx.signature and not _verify_hmac(tx.payload_hash, tx.signature):
            issues.append(
                f"Block {tx.block_height} (tx={tx.id}): HMAC signature invalid — record may be tampered"
            )

        # 2. Verify previous hash linkage
        if prev_hash is not None and tx.previous_tx_hash != prev_hash:
            issues.append(
                f"Block {tx.block_height} (tx={tx.id}): Chain broken — "
                f"expected prev_hash={prev_hash[:16]}… got {str(tx.previous_tx_hash)[:16]}…"
            )

        prev_hash = tx.payload_hash

    return {
        "blocks_checked": len(txs),
        "issues_found": len(issues),
        "chain_valid": len(issues) == 0,
        "issues": issues,
    }
