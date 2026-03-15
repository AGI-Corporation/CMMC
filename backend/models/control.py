"""
Pydantic models for CMMC Controls
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime, UTC


class CMMCLevel(str, Enum):
    LEVEL_1 = "Level 1"
    LEVEL_2 = "Level 2"
    LEVEL_3 = "Level 3"


class ControlDomain(str, Enum):
    AC = "AC"  # Access Control
    AU = "AU"  # Audit and Accountability
    CM = "CM"  # Configuration Management
    IA = "IA"  # Identification and Authentication
    IR = "IR"  # Incident Response
    MA = "MA"  # Maintenance
    MP = "MP"  # Media Protection
    PS = "PS"  # Personnel Security
    PE = "PE"  # Physical Protection
    RA = "RA"  # Risk Assessment
    CA = "CA"  # Security Assessment
    SA = "SA"  # Situational Awareness
    SC = "SC"  # System and Communications Protection
    SI = "SI"  # System and Information Integrity


class ImplementationStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    NOT_APPLICABLE = "not_applicable"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    PLANNED = "planned"


class Control(BaseModel):
    """CMMC Control - aligned with OSCAL catalog model."""
    id: str = Field(..., description="Control ID (e.g., AC.1.001)")
    title: str = Field(..., description="Control title")
    description: str = Field(..., description="Control description / requirement")
    domain: ControlDomain = Field(..., description="Control domain / family")
    level: CMMCLevel = Field(..., description="Minimum CMMC level requiring this control")
    nist_mapping: Optional[str] = Field(None, description="Mapped NIST SP 800-171 control ID")
    discussion: Optional[str] = Field(None, description="CMMC discussion / implementation guidance")
    assessment_objectives: Optional[List[str]] = Field(default_factory=list, description="Assessment objectives")
    weight: int = Field(default=1, description="SPRS point weight (deducted if not implemented)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        json_schema_extra = {
            "example": {
                "id": "AC.1.001",
                "title": "Limit system access to authorized users",
                "description": "Limit information system access to authorized users, processes acting on behalf of authorized users, and devices (including other information systems).",
                "domain": "AC",
                "level": "Level 1",
                "nist_mapping": "3.1.1",
                "weight": 5
            }
        }


class ControlResponse(BaseModel):
    """API response wrapper for a single control."""
    control: Control
    implementation_status: Optional[ImplementationStatus] = None
    evidence_count: int = 0
    notes: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    poam_required: bool = False


class ControlListResponse(BaseModel):
    """API response for list of controls."""
    controls: List[ControlResponse]
    total: int
    level_filter: Optional[CMMCLevel] = None
    domain_filter: Optional[ControlDomain] = None


class ControlUpdate(BaseModel):
    """Request body for updating control implementation status."""
    implementation_status: ImplementationStatus
    notes: Optional[str] = None
    responsible_party: Optional[str] = None
    target_completion_date: Optional[datetime] = None
    evidence_ids: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[float] = Field(0.0, ge=0.0, le=1.0)
    poam_required: Optional[bool] = False
