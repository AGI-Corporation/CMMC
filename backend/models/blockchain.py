"""
Pydantic models for the cmmc.blockchain attestation layer.
AGI Corporation 2026

All on-chain records use SHA-256 content hashing with Merkle-style chaining
so the ledger is tamper-evident even in the local (DB-backed) deployment.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ─── Enumerations ─────────────────────────────────────────────────────────────

class TxType(str, Enum):
    ATTESTATION = "attestation"
    SPRS_ANCHOR = "sprs_anchor"
    EVIDENCE = "evidence"
    ASSESSMENT = "assessment"


class TxStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


# ─── Control Attestation ───────────────────────────────────────────────────────

class AttestationRequest(BaseModel):
    """Body for submitting a control attestation on-chain."""
    status: str = Field(..., description="implemented | partial | planned | not_implemented")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="ZT confidence score 0-1")
    evidence_hashes: List[str] = Field(default_factory=list, description="SHA-256 hashes of supporting evidence")
    assessor_id: Optional[str] = Field(None, description="C3PAO or agent that performed the assessment")
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "implemented",
                "confidence": 0.92,
                "evidence_hashes": ["abc123def456..."],
                "assessor_id": "c3pao-org-001",
                "notes": "MFA enforced via Okta, reviewed 2026-03-28"
            }
        }


class AttestationResponse(BaseModel):
    """Result of a successful on-chain attestation."""
    attestation_id: str
    control_id: str
    tx_id: str
    block_height: int
    payload_hash: str
    status: str
    confidence: float
    evidence_hashes: List[str]
    org_id: str
    assessor_id: Optional[str]
    timestamp: datetime
    previous_tx_hash: Optional[str]

    class Config:
        from_attributes = True


class AttestationHistoryResponse(BaseModel):
    """Full audit trail for a control's attestations."""
    control_id: str
    org_id: str
    total_records: int
    attestations: List[AttestationResponse]


class AttestationVerifyResponse(BaseModel):
    """Result of verifying a control's on-chain attestation against the DB."""
    control_id: str
    verified: bool
    db_status: Optional[str]
    chain_status: Optional[str]
    db_confidence: Optional[float]
    chain_confidence: Optional[float]
    discrepancy: bool
    last_tx_id: Optional[str]
    last_block_height: Optional[int]
    message: str


# ─── SPRS Anchoring ───────────────────────────────────────────────────────────

class SPRSAnchorRequest(BaseModel):
    """Body for anchoring the current SPRS score on-chain."""
    sprs_score: int = Field(..., ge=-203, le=110)
    total_controls: int
    implemented: int
    attestation_ids: List[str] = Field(default_factory=list, description="IDs of attestation TXs included")
    notes: Optional[str] = None


class SPRSAnchorResponse(BaseModel):
    """Result of a successful SPRS score anchor."""
    anchor_id: str
    tx_id: str
    block_height: int
    payload_hash: str
    sprs_score: int
    total_controls: int
    implemented: int
    org_id: str
    timestamp: datetime


class SPRSHistoryResponse(BaseModel):
    """SPRS score history from the blockchain ledger."""
    org_id: str
    total_anchors: int
    anchors: List[SPRSAnchorResponse]


# ─── Evidence Registration ─────────────────────────────────────────────────────

class EvidenceRegisterResponse(BaseModel):
    """Result of registering an evidence artifact on-chain."""
    evidence_id: str
    tx_id: str
    block_height: int
    payload_hash: str
    sha256_hash: str
    org_id: str
    timestamp: datetime


class EvidenceVerifyResponse(BaseModel):
    """Result of verifying evidence integrity against the chain."""
    evidence_id: str
    registered: bool
    hash_match: Optional[bool]
    stored_hash: Optional[str]
    computed_hash: Optional[str]
    revoked: bool
    tx_id: Optional[str]
    message: str


# ─── Assessment Records ────────────────────────────────────────────────────────

class FormalAssessmentRequest(BaseModel):
    """Body for submitting a formal C3PAO assessment on-chain."""
    agent_run_id: Optional[str] = Field(None, description="AgentRunRecord ID to promote")
    level: str = Field(..., description="Level 1 | Level 2 | Level 3")
    outcome: str = Field(..., description="conditional | final | failed")
    sprs_score: int = Field(..., ge=-203, le=110)
    control_count: int
    findings_hash: Optional[str] = Field(None, description="SHA-256 of findings report")
    report_ipfs_cid: Optional[str] = None
    valid_until: Optional[datetime] = None
    assessor_org_id: Optional[str] = None


class FormalAssessmentResponse(BaseModel):
    """Result of a formal C3PAO assessment submission."""
    assessment_chain_id: str
    tx_id: str
    block_height: int
    payload_hash: str
    org_id: str
    level: str
    outcome: str
    sprs_score: int
    issued_at: datetime
    valid_until: Optional[datetime]
    assessor_org_id: Optional[str]


# ─── Generic Transaction / Audit ──────────────────────────────────────────────

class BlockchainTxResponse(BaseModel):
    """Generic blockchain transaction record."""
    id: str
    tx_type: TxType
    org_id: str
    control_id: Optional[str]
    evidence_id: Optional[str]
    payload_hash: str
    previous_tx_hash: Optional[str]
    block_height: int
    status: TxStatus
    payload: Dict[str, Any]
    created_at: datetime
    confirmed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    """Full org audit trail from the blockchain ledger."""
    org_id: str
    total_transactions: int
    transactions: List[BlockchainTxResponse]


class BlockchainStatusResponse(BaseModel):
    """Status of the blockchain node / ledger."""
    connected: bool
    ledger_mode: str          # "local" | "fabric" | "evm"
    latest_block_height: int
    total_transactions: int
    org_id: str
    chain_id: str


class BlockchainIdentityResponse(BaseModel):
    """Current org identity / signing info."""
    org_id: str
    msp_id: str
    public_key_fingerprint: str
    ledger_mode: str
    chain_id: str
