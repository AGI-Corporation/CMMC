"""
Simulation Router - Visualizes agent interactions as a neural network.
AGI Corporation 2026
"""
from fastapi import APIRouter, Depends
from typing import List, Dict, Any
import random
from datetime import datetime, UTC

router = APIRouter()

# Mock simulation state
@router.get("/state", summary="Get current brain simulation state")
async def get_simulation_state():
    """
    Returns a graph-like structure of agents (neurons) and their connections.
    Includes 'firing' status based on recent activity.
    """
    agents = ["orchestrator", "icam", "devsecops", "mistral", "infra", "data", "nist", "hipaa", "fhir"]

    nodes = []
    for i, agent in enumerate(agents):
        nodes.append({
            "id": agent,
            "label": agent.upper(),
            "group": "agent",
            "level": 0 if agent == "orchestrator" else 1,
            "firing": random.random() > 0.7,
            "last_active": datetime.now(UTC).isoformat()
        })

    # Add some control clusters as nodes
    domains = ["AC", "IA", "SC", "SI", "AU"]
    for domain in domains:
        nodes.append({
            "id": f"domain_{domain}",
            "label": domain,
            "group": "domain",
            "level": 2,
            "firing": random.random() > 0.8
        })

    edges = []
    # Orchestrator connects to all agents
    for agent in agents[1:]:
        edges.append({"from": "orchestrator", "to": agent, "type": "coordinates"})

    # Agents connect to domains
    edges.append({"from": "icam", "to": "domain_AC", "type": "assesses"})
    edges.append({"from": "icam", "to": "domain_IA", "type": "assesses"})
    edges.append({"from": "devsecops", "to": "domain_SI", "type": "assesses"})
    edges.append({"from": "infra", "to": "domain_SC", "type": "assesses"})
    edges.append({"from": "mistral", "to": "domain_AU", "type": "analyzes"})

    return {
        "nodes": nodes,
        "edges": edges,
        "timestamp": datetime.now(UTC).isoformat(),
        "brain_load": random.randint(10, 85)
    }
