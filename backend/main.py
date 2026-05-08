"""
CMMC Compliance Hackathon Platform - FastAPI + MCP Server
AGI Corporation 2026

This is the main FastAPI application with MCP integration.
The /mcp endpoint exposes all CMMC tools to AI agents via the
Model Context Protocol (MCP).
"""

import json
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP
from starlette.exceptions import HTTPException as StarletteHTTPException

from agents.devsecops_agent import agent as devsecops
from agents.icam_agent import agent as icam
from agents.mistral_agent import agent as mistral
from agents.orchestrator import agent as orchestrator
from backend.db.database import init_db
from backend.middleware.security import SecurityHeadersMiddleware
from backend.routers import assessment, controls, evidence, reports

load_dotenv()

# Configure central logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


# ─── Global Exception Handlers ────────────────────────────────────────────────


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Pass-through for standard HTTP exceptions (4xx) while logging them."""
    logger.info(f"HTTP {exc.status_code} error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle 422 validation errors with detailed feedback."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions (500) to mask internal details."""
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
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
