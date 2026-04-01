"""
CMMC Compliance Hackathon Platform - FastAPI + MCP Server
AGI Corporation 2026

This is the main FastAPI application with MCP integration.
The /mcp endpoint exposes all CMMC tools to AI agents via the
Model Context Protocol (MCP).
"""

import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from agents.data_agent import agent as data_agent
from agents.devsecops_agent import agent as devsecops
from agents.governance_agent import agent as governance_agent
from agents.icam_agent import agent as icam
from agents.infra_agent import agent as infra_agent
from agents.mistral_agent import agent as mistral
from agents.ops_agent import agent as ops_agent
from agents.orchestrator import agent as orchestrator
from agents.remediation_agent import agent as remediation_agent
from backend.db.database import init_db
from backend.middleware.security import SecurityHeadersMiddleware
from backend.routers import assessment, controls, evidence, reports

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


# ─── FastAPI Application ───────────────────────────────────────────────────────

app = FastAPI(
    title="CMMC Compliance Platform",
    description="""AI-powered CMMC 2.0 compliance automation platform.
    
    Exposes CMMC controls, evidence management, assessment scoring, and 
    SSP/POAM generation via both REST API and MCP protocol for AI agent access.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

cors_origins = json.loads(
    os.getenv("CORS_ORIGINS", '["http://localhost:3000", "http://localhost:5173"]')
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# ─── Routers ──────────────────────────────────────────────────────────────────

# Core Routers
app.include_router(controls.router, prefix="/api/controls", tags=["Controls"])
app.include_router(assessment.router, prefix="/api/assessment", tags=["Assessment"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["Evidence"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])

# Agent Routers
app.include_router(
    orchestrator.router, prefix="/api/orchestrator", tags=["Orchestrator"]
)
app.include_router(icam.router, prefix="/api/agents/icam", tags=["ICAM Agent"])
app.include_router(
    devsecops.router, prefix="/api/agents/devsecops", tags=["DevSecOps Agent"]
)
app.include_router(mistral.router, prefix="/api/agents/mistral", tags=["Mistral Agent"])
app.include_router(
    data_agent.router, prefix="/api/agents/data", tags=["Data Protection Agent"]
)
app.include_router(
    infra_agent.router, prefix="/api/agents/infra", tags=["Infrastructure Agent"]
)
app.include_router(
    governance_agent.router, prefix="/api/agents/governance", tags=["Governance Agent"]
)
app.include_router(
    ops_agent.router, prefix="/api/agents/ops", tags=["Operations Agent"]
)
app.include_router(
    remediation_agent.router,
    prefix="/api/agents/remediation",
    tags=["Remediation Agent"],
)


# ─── Health Check ─────────────────────────────────────────────────────────────


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "CMMC Compliance Platform",
        "version": "1.0.0",
        "status": "healthy",
        "mcp_endpoint": "/mcp",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


# ─── MCP Integration ──────────────────────────────────────────────────────────
# Exposes all FastAPI endpoints as MCP tools for AI agents
# Compatible with Claude Desktop, Goose Desktop, and any MCP client

mcp = FastApiMCP(
    app,
    name="CMMC Compliance MCP",
    description="MCP server for CMMC 2.0 compliance automation. Provides tools for control lookup, evidence collection, assessment scoring, SPRS calculation, and SSP/POAM generation.",
)

mcp.mount()

# ─── MCP endpoint is now available at /mcp ─────────────────────────────────────
# Add to claude_desktop_config.json:
# {
#   "mcpServers": {
#     "cmmc": { "url": "http://localhost:8000/mcp" }
#   }
# }
