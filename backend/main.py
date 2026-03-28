"""
CMMC Compliance Hackathon Platform - FastAPI + MCP Server
AGI Corporation 2026

This is the main FastAPI application with MCP integration.
The /mcp endpoint exposes all CMMC tools to AI agents via the
Model Context Protocol (MCP).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from contextlib import asynccontextmanager
import json
import os

from backend.routers import controls, assessment, evidence, reports
from backend.middleware.security import SecurityHeadersMiddleware
from agents.orchestrator import agent as orchestrator
from agents.icam_agent import agent as icam
from agents.devsecops_agent import agent as devsecops
from agents.mistral_agent import agent as mistral

from backend.db.database import init_db
from dotenv import load_dotenv

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

cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000", "http://localhost:5173"]'))

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
app.include_router(orchestrator.router, prefix="/api/orchestrator", tags=["Orchestrator"])
app.include_router(icam.router, prefix="/api/agents/icam", tags=["ICAM Agent"])
app.include_router(devsecops.router, prefix="/api/agents/devsecops", tags=["DevSecOps Agent"])
app.include_router(mistral.router, prefix="/api/agents/mistral", tags=["Mistral Agent"])


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

mcp.mount_http()

# ─── MCP endpoint is now available at /mcp ─────────────────────────────────────
# Add to claude_desktop_config.json:
# {
#   "mcpServers": {
#     "cmmc": { "url": "http://localhost:8000/mcp" }
#   }
# }
