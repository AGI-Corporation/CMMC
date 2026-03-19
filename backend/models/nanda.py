"""
NANDA Protocol Models - AgentFacts and Attestation
Networked AI Agents in a Decentralized Architecture
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, UTC

class TrustLevel(str, Enum):
    VERIFIED = "verified"
    TRUSTED = "trusted"
    SANDBOXED = "sandboxed"
    UNVERIFIED = "unverified"

class Protocol(str, Enum):
    MCP = "mcp"
    HTTPS = "https"
    A2A = "a2a"
    NLWEB = "nlweb"

class AgentFacts(BaseModel):
    """Metadata about an agent's capabilities and trust."""
    agent_id: str
    name: str
    version: str
    owner: str = "AGI Corporation"
    trust_level: TrustLevel = TrustLevel.UNVERIFIED
    protocols: List[Protocol] = [Protocol.MCP, Protocol.HTTPS]
    capabilities: List[str] = Field(..., description="CMMC Domains or ZT Pillars covered")
    attestation_key: Optional[str] = None
    last_verified: datetime = Field(default_factory=lambda: datetime.now(UTC))
    endpoint: str
    integration_score: float = 1.0  # 0.0 to 1.0

class AgentRegistryResponse(BaseModel):
    agents: List[AgentFacts]
    total: int
    system_status: str = "operational"
