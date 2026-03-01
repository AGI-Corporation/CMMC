"""
Pydantic models for Evidence artifacts.
AGI Corporation 2026
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class EvidenceType(str, Enum):
    LOG = "log"
    SCAN = "scan"
    POLICY = "policy"
    DIAGRAM = "diagram"
    SCREENSHOT = "screenshot"
    REPORT = "report"
    INTERVIEW = "interview"
    CONFIGURATION = "configuration"


class EvidenceBase(BaseModel):
    control_id: str = Field(..., example="AC.1.001")
    zt_pillar: str = Field(..., example="User")
    zt_capability_id: Optional[str] = Field(None, example="ZT-1.1")
    evidence_type: EvidenceType
    title: str
    description: str
    source_system: str = Field(..., example="Okta / GitHub Actions")
    uri: Optional[str] = None
    reviewer: Optional[str] = None
    review_cycle_days: int = 365
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceResponse(EvidenceBase):
    id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvidenceListResponse(BaseModel):
    total: int
    evidence: List[EvidenceResponse]


class EvidenceSchema(BaseModel):
    """Canonical evidence schema for agent interoperability."""
    id: str
    type: EvidenceType
    source_system: str
    zt_capability_id: Optional[str] = None
    controls: List[str]  # list of control IDs covered
    summary: str
    uri: Optional[str] = None
    timestamp: datetime
    owner_agent: str  # which agent produced this evidence
    retention_days: int = 1095  # 3-year default
