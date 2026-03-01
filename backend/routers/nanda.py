"""
NANDA Agent Registry Router
Provides verified agent discovery and attestation facts.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from backend.models.nanda import AgentFacts, TrustLevel, Protocol, AgentRegistryResponse

router = APIRouter()

# In-memory registry (seeded on init)
_registry: Dict[str, AgentFacts] = {}

def seed_registry():
    agents = [
        AgentFacts(
            agent_id="icam-01",
            name="ICAM Agent",
            version="1.0.2",
            trust_level=TrustLevel.VERIFIED,
            protocols=[Protocol.HTTPS, Protocol.MCP],
            capabilities=["Access Control", "Identification & Authentication", "User Pillar"],
            endpoint="/api/agents/icam"
        ),
        AgentFacts(
            agent_id="devsecops-01",
            name="DevSecOps Agent",
            version="1.1.0",
            trust_level=TrustLevel.VERIFIED,
            protocols=[Protocol.HTTPS, Protocol.MCP],
            capabilities=["Configuration Management", "System & Information Integrity", "Application Pillar"],
            endpoint="/api/agents/devsecops"
        ),
        AgentFacts(
            agent_id="infra-01",
            name="Infrastructure Agent",
            version="0.9.5",
            trust_level=TrustLevel.TRUSTED,
            protocols=[Protocol.HTTPS],
            capabilities=["System & Communications Protection", "Network Pillar"],
            endpoint="/api/agents/infra"
        ),
        AgentFacts(
            agent_id="data-01",
            name="Data Protection Agent",
            version="0.9.0",
            trust_level=TrustLevel.TRUSTED,
            protocols=[Protocol.HTTPS],
            capabilities=["Media Protection", "Data Pillar"],
            endpoint="/api/agents/data"
        ),
        AgentFacts(
            agent_id="mistral-01",
            name="Mistral Intelligence Agent",
            version="2.0.0",
            trust_level=TrustLevel.VERIFIED,
            protocols=[Protocol.HTTPS, Protocol.MCP],
            capabilities=["Compliance Analysis", "Remediation Planning", "All ZT Pillars"],
            endpoint="/api/agents/mistral"
        )
    ]
    for a in agents:
        _registry[a.agent_id] = a

seed_registry()

@router.get("/", response_model=AgentRegistryResponse, summary="Discover agents via NANDA Index")
async def list_agents():
    """List all registered agents and their verified facts."""
    agents = list(_registry.values())
    return AgentRegistryResponse(agents=agents, total=len(agents))

@router.get("/{agent_id}", response_model=AgentFacts, summary="Get verified facts for a specific agent")
async def get_agent_facts(agent_id: str):
    """Retrieve attestation facts for a specific agent ID."""
    if agent_id in _registry:
        return _registry[agent_id]
    raise HTTPException(status_code=404, detail="Agent not found in NANDA Index")
