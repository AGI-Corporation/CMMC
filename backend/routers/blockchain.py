"""
Blockchain Router — cmmc.blockchain attestation API.
AGI Corporation 2026

Exposes all blockchain compliance operations as REST endpoints (and MCP tools):

  POST   /api/blockchain/attest/{control_id}           Submit control attestation
  GET    /api/blockchain/attest/{control_id}/history    Full attestation audit trail
  GET    /api/blockchain/attest/{control_id}/verify     Verify attestation vs DB state
  POST   /api/blockchain/sprs/anchor                   Anchor SPRS score on-chain
  GET    /api/blockchain/sprs/history                  SPRS score history
  POST   /api/blockchain/evidence/{evidence_id}/register  Register evidence hash
  GET    /api/blockchain/evidence/{evidence_id}/verify    Verify evidence integrity
  POST   /api/blockchain/assessment/submit             Submit formal C3PAO assessment
  GET    /api/blockchain/audit-trail                   Full org audit trail
  GET    /api/blockchain/integrity                     Verify ledger hash-chain integrity
  GET    /api/blockchain/status                        Node / ledger health
  GET    /api/blockchain/identity                      Current org MSP identity
"""
import hashlib
import os
from datetime import datetime, UTC
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.database import (
    get_db,
    ControlRecord,
    AssessmentRecord,
    EvidenceRecord,
    BlockchainTransaction,
    get_latest_assessments,
)
from backend.models.blockchain import (
    AttestationRequest,
    AttestationResponse,
    AttestationHistoryResponse,
    AttestationVerifyResponse,
    SPRSAnchorRequest,
    SPRSAnchorResponse,
    SPRSHistoryResponse,
    EvidenceRegisterResponse,
    EvidenceVerifyResponse,
    FormalAssessmentRequest,
    FormalAssessmentResponse,
    BlockchainTxResponse,
    AuditTrailResponse,
    BlockchainStatusResponse,
    BlockchainIdentityResponse,
    TxType,
    TxStatus,
)
from backend.services import blockchain_service as svc

router = APIRouter()

_ORG_ID = os.getenv("BLOCKCHAIN_ORG_ID", "agi-corp")
_MSP_ID = os.getenv("BLOCKCHAIN_MSP_ID", "AgiCorpMSP")
_CHAIN_ID = os.getenv("BLOCKCHAIN_CHAIN_ID", "cmmc-blockchain-mainnet")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _tx_to_response(tx: BlockchainTransaction) -> BlockchainTxResponse:
    return BlockchainTxResponse(
        id=tx.id,
        tx_type=TxType(tx.tx_type),
        org_id=tx.org_id,
        control_id=tx.control_id,
        evidence_id=tx.evidence_id,
        payload_hash=tx.payload_hash,
        previous_tx_hash=tx.previous_tx_hash,
        block_height=tx.block_height,
        status=TxStatus(tx.status),
        payload=tx.payload,
        created_at=tx.created_at,
        confirmed_at=tx.confirmed_at,
    )


def _tx_to_attestation(tx: BlockchainTransaction) -> AttestationResponse:
    p = tx.payload
    return AttestationResponse(
        attestation_id=p.get("attestation_id", tx.id),
        control_id=p.get("control_id", ""),
        tx_id=tx.id,
        block_height=tx.block_height,
        payload_hash=tx.payload_hash,
        status=p.get("status", ""),
        confidence=p.get("confidence", 0.0),
        evidence_hashes=p.get("evidence_hashes", []),
        org_id=tx.org_id,
        assessor_id=p.get("assessor_id"),
        timestamp=tx.created_at,
        previous_tx_hash=tx.previous_tx_hash,
    )


# ─── Control Attestation ───────────────────────────────────────────────────────

@router.post(
    "/attest/{control_id}",
    response_model=AttestationResponse,
    summary="Submit On-Chain Control Attestation",
    description=(
        "Immutably record the compliance status of a CMMC control on the blockchain ledger. "
        "Each attestation is cryptographically chained to the previous one, forming a tamper-evident "
        "audit trail. The payload hash and HMAC signature are stored alongside the control status."
    ),
)
async def submit_attestation(
    control_id: str,
    body: AttestationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit an on-chain attestation for a specific CMMC control."""
    ctrl_result = await db.execute(select(ControlRecord).where(ControlRecord.id == control_id))
    if not ctrl_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    tx = await svc.submit_attestation(
        db=db,
        control_id=control_id,
        status=body.status,
        confidence=body.confidence,
        evidence_hashes=body.evidence_hashes,
        assessor_id=body.assessor_id,
        notes=body.notes,
        org_id=_ORG_ID,
    )
    return _tx_to_attestation(tx)


@router.get(
    "/attest/{control_id}/history",
    response_model=AttestationHistoryResponse,
    summary="Get Control Attestation History",
    description=(
        "Retrieve the full on-chain attestation history for a CMMC control, ordered by block height. "
        "Each record includes its payload hash and link to the previous transaction, enabling "
        "independent verification of the chain of custody."
    ),
)
async def get_attestation_history(
    control_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the full blockchain attestation audit trail for a control."""
    ctrl_result = await db.execute(select(ControlRecord).where(ControlRecord.id == control_id))
    if not ctrl_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    txs = await svc.get_attestation_history(db, control_id=control_id)
    return AttestationHistoryResponse(
        control_id=control_id,
        org_id=_ORG_ID,
        total_records=len(txs),
        attestations=[_tx_to_attestation(t) for t in txs],
    )


@router.get(
    "/attest/{control_id}/verify",
    response_model=AttestationVerifyResponse,
    summary="Verify Control Attestation vs DB State",
    description=(
        "Cross-check the most recent on-chain attestation for a control against its current "
        "database state. Returns a discrepancy flag if the blockchain record and the DB diverge, "
        "which may indicate an integrity issue."
    ),
)
async def verify_attestation(
    control_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Compare the latest on-chain attestation with the current DB assessment for a control."""
    # Fetch latest on-chain attestation
    txs = await svc.get_attestation_history(db, control_id=control_id)
    if not txs:
        return AttestationVerifyResponse(
            control_id=control_id,
            verified=False,
            db_status=None,
            chain_status=None,
            db_confidence=None,
            chain_confidence=None,
            discrepancy=False,
            last_tx_id=None,
            last_block_height=None,
            message="No on-chain attestation found for this control",
        )

    latest_tx = txs[-1]
    chain_status = latest_tx.payload.get("status")
    chain_confidence = latest_tx.payload.get("confidence")

    # Fetch latest DB assessment
    assessments = await get_latest_assessments(db, control_ids=[control_id])
    assessment = assessments.get(control_id)
    db_status = assessment.status if assessment else None
    db_confidence = assessment.confidence if assessment else None

    discrepancy = (db_status != chain_status) if (db_status and chain_status) else False

    if discrepancy:
        msg = f"DISCREPANCY: DB status='{db_status}' differs from chain status='{chain_status}'"
    elif db_status is None:
        msg = "No DB assessment found; chain attestation is the only record"
    else:
        msg = "Verified — DB and chain are consistent"

    return AttestationVerifyResponse(
        control_id=control_id,
        verified=not discrepancy,
        db_status=db_status,
        chain_status=chain_status,
        db_confidence=db_confidence,
        chain_confidence=chain_confidence,
        discrepancy=discrepancy,
        last_tx_id=latest_tx.id,
        last_block_height=latest_tx.block_height,
        message=msg,
    )


# ─── SPRS Score Anchoring ─────────────────────────────────────────────────────

@router.post(
    "/sprs/anchor",
    response_model=SPRSAnchorResponse,
    summary="Anchor SPRS Score On-Chain",
    description=(
        "Record an immutable SPRS score snapshot on the blockchain ledger. "
        "Use this after calculating the SPRS score to create a time-stamped, tamper-evident "
        "record for DoD submission evidence."
    ),
)
async def anchor_sprs_score(
    body: SPRSAnchorRequest,
    db: AsyncSession = Depends(get_db),
):
    """Anchor the current SPRS compliance score on the blockchain ledger."""
    tx = await svc.anchor_sprs_score(
        db=db,
        sprs_score=body.sprs_score,
        total_controls=body.total_controls,
        implemented=body.implemented,
        attestation_ids=body.attestation_ids,
        notes=body.notes,
        org_id=_ORG_ID,
    )
    p = tx.payload
    return SPRSAnchorResponse(
        anchor_id=p.get("anchor_id", tx.id),
        tx_id=tx.id,
        block_height=tx.block_height,
        payload_hash=tx.payload_hash,
        sprs_score=p["sprs_score"],
        total_controls=p["total_controls"],
        implemented=p["implemented"],
        org_id=tx.org_id,
        timestamp=tx.created_at,
    )


@router.get(
    "/sprs/history",
    response_model=SPRSHistoryResponse,
    summary="Get SPRS Score History",
    description="Retrieve the full blockchain history of SPRS score anchors, newest first.",
)
async def get_sprs_history(db: AsyncSession = Depends(get_db)):
    """Return all SPRS score anchors from the blockchain ledger."""
    txs = await svc.get_sprs_history(db, org_id=_ORG_ID)
    anchors = []
    for tx in txs:
        p = tx.payload
        anchors.append(
            SPRSAnchorResponse(
                anchor_id=p.get("anchor_id", tx.id),
                tx_id=tx.id,
                block_height=tx.block_height,
                payload_hash=tx.payload_hash,
                sprs_score=p.get("sprs_score", 0),
                total_controls=p.get("total_controls", 0),
                implemented=p.get("implemented", 0),
                org_id=tx.org_id,
                timestamp=tx.created_at,
            )
        )
    return SPRSHistoryResponse(org_id=_ORG_ID, total_anchors=len(anchors), anchors=anchors)


# ─── Evidence Registration ────────────────────────────────────────────────────

@router.post(
    "/evidence/{evidence_id}/register",
    response_model=EvidenceRegisterResponse,
    summary="Register Evidence Hash On-Chain",
    description=(
        "Register the SHA-256 hash of an evidence artifact on the blockchain ledger. "
        "This creates an immutable timestamp proving the evidence existed and was unmodified "
        "at registration time. CUI content is never stored on-chain — only the hash."
    ),
)
async def register_evidence(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Register an existing evidence artifact's hash on the blockchain ledger."""
    ev_result = await db.execute(select(EvidenceRecord).where(EvidenceRecord.id == evidence_id))
    ev = ev_result.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found")

    # Compute hash from evidence metadata if no file content is available
    content_for_hash = f"{ev.id}|{ev.title}|{ev.description}|{ev.source_system}|{ev.uri or ''}|{ev.created_at}"
    sha256 = svc.compute_sha256_for_content(content_for_hash)

    tx = await svc.register_evidence(
        db=db,
        evidence_id=evidence_id,
        sha256_hash=sha256,
        control_id=ev.control_id,
        storage_uri=ev.uri,
        evidence_type=ev.evidence_type,
        reviewer_id=ev.reviewer,
        org_id=_ORG_ID,
    )
    return EvidenceRegisterResponse(
        evidence_id=evidence_id,
        tx_id=tx.id,
        block_height=tx.block_height,
        payload_hash=tx.payload_hash,
        sha256_hash=sha256,
        org_id=tx.org_id,
        timestamp=tx.created_at,
    )


@router.get(
    "/evidence/{evidence_id}/verify",
    response_model=EvidenceVerifyResponse,
    summary="Verify Evidence Integrity",
    description=(
        "Verify that an evidence artifact has not been tampered with since its blockchain registration. "
        "Compares the stored on-chain hash against the current evidence record. "
        "Pass `content` as a query parameter to verify arbitrary content against the registered hash."
    ),
)
async def verify_evidence(
    evidence_id: str,
    content: Optional[str] = Query(None, description="Optional content string to hash and compare"),
    db: AsyncSession = Depends(get_db),
):
    """Verify evidence integrity against the blockchain registration."""
    result = await svc.verify_evidence_integrity(db, evidence_id=evidence_id, content=content)
    return EvidenceVerifyResponse(**result)


# ─── Formal Assessment ────────────────────────────────────────────────────────

@router.post(
    "/assessment/submit",
    response_model=FormalAssessmentResponse,
    summary="Submit Formal C3PAO Assessment On-Chain",
    description=(
        "Submit a formal CMMC assessment record to the blockchain ledger. "
        "This represents the official C3PAO assessment outcome and creates an immutable "
        "certification record with validity window. Only use this endpoint after a full "
        "formal assessment has been completed."
    ),
)
async def submit_formal_assessment(
    body: FormalAssessmentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a formal C3PAO CMMC assessment record to the blockchain."""
    tx = await svc.submit_formal_assessment(
        db=db,
        level=body.level,
        outcome=body.outcome,
        sprs_score=body.sprs_score,
        control_count=body.control_count,
        findings_hash=body.findings_hash,
        report_ipfs_cid=body.report_ipfs_cid,
        valid_until=body.valid_until,
        assessor_org_id=body.assessor_org_id,
        agent_run_id=body.agent_run_id,
        org_id=_ORG_ID,
    )
    p = tx.payload
    return FormalAssessmentResponse(
        assessment_chain_id=p.get("assessment_chain_id", tx.id),
        tx_id=tx.id,
        block_height=tx.block_height,
        payload_hash=tx.payload_hash,
        org_id=tx.org_id,
        level=p["level"],
        outcome=p["outcome"],
        sprs_score=p["sprs_score"],
        issued_at=tx.created_at,
        valid_until=body.valid_until,
        assessor_org_id=body.assessor_org_id,
    )


# ─── Audit Trail ──────────────────────────────────────────────────────────────

@router.get(
    "/audit-trail",
    response_model=AuditTrailResponse,
    summary="Get Full Blockchain Audit Trail",
    description=(
        "Retrieve a paginated list of all compliance transactions in the blockchain ledger, "
        "newest first. Each record includes the payload hash and previous-hash linkage "
        "for independent chain verification."
    ),
)
async def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tx_type: Optional[str] = Query(None, description="Filter by tx_type: attestation | sprs_anchor | evidence | assessment"),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated audit trail of all blockchain transactions."""
    total, txs = await svc.get_audit_trail(db, org_id=_ORG_ID, limit=limit, offset=offset)

    records = [_tx_to_response(t) for t in txs]
    if tx_type:
        records = [r for r in records if r.tx_type.value == tx_type]

    return AuditTrailResponse(
        org_id=_ORG_ID,
        total_transactions=total,
        transactions=records,
    )


@router.get(
    "/integrity",
    summary="Verify Ledger Chain Integrity",
    description=(
        "Walk the entire blockchain ledger and verify that the hash chain is unbroken "
        "and all HMAC signatures are valid. Returns a detailed report of any issues found."
    ),
)
async def verify_ledger_integrity(db: AsyncSession = Depends(get_db)):
    """Run a full cryptographic integrity check on the blockchain ledger."""
    return await svc.verify_chain_integrity(db)


# ─── Status & Identity ────────────────────────────────────────────────────────

@router.get(
    "/status",
    response_model=BlockchainStatusResponse,
    summary="Blockchain Ledger Status",
    description="Get the current status of the blockchain ledger including node connectivity, block height, and transaction count.",
)
async def get_blockchain_status(db: AsyncSession = Depends(get_db)):
    """Return current blockchain ledger health and statistics."""
    status = await svc.get_ledger_status(db)
    return BlockchainStatusResponse(**status)


@router.get(
    "/identity",
    response_model=BlockchainIdentityResponse,
    summary="Current Org Blockchain Identity",
    description="Return the current organisation's blockchain identity including MSP ID and signing key fingerprint.",
)
async def get_blockchain_identity():
    """Return the current org's blockchain identity information."""
    signing_key = os.getenv("BLOCKCHAIN_SIGNING_KEY", "change-me-use-hsm-in-production")
    import hashlib
    key_fingerprint = hashlib.sha256(signing_key.encode()).hexdigest()[:16]

    return BlockchainIdentityResponse(
        org_id=_ORG_ID,
        msp_id=_MSP_ID,
        public_key_fingerprint=key_fingerprint,
        ledger_mode=os.getenv("BLOCKCHAIN_LEDGER_MODE", "local"),
        chain_id=_CHAIN_ID,
    )
