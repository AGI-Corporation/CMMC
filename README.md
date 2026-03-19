# Sentient Compliance Platform

> AI-powered Multi-Framework Compliance Automation platform. Leverages Model Context Protocol (MCP), NANDA agent discovery, and Sentient OML-inspired cryptographic provenance to automate compliance for CMMC 2.0, NIST 800-171, HIPAA, and FHIR.

---

## Overview

This platform is a comprehensive compliance management system designed for high-stakes industries (Defense, Healthcare). It automates the lifecycle of compliance—from evidence collection to AI-driven assessment and report generation—across multiple frameworks:

- **CMMC 2.0**: Level 1 (FCI) & Level 2 (CUI) compliance for DIB contractors.
- **NIST SP 800-171**: Security requirements for protecting Controlled Unclassified Information.
- **HIPAA Security**: Security and privacy rules for healthcare data (PHI).
- **FHIR Privacy**: Specialized controls for healthcare data interoperability, SMART on FHIR, and BabelFHIR-TS type safety.

---

## Core Capabilities

### 🧠 Sentient Core (OAGD Protocol)
The platform features a real-time neural simulation of the agent fleet's cognitive state. Using the **Open Agent Graph Discovery (OAGD)** protocol, the UI visualizes:
- **Neuron Activity**: Real-time monitoring of agent tasking and cognitive load.
- **Active Pathways**: Visualizing how agents collaborate to solve complex compliance mappings.
- **Neural Integrity**: Continuous OML validation of the agent fleet's internal state.

### 🤖 Intelligent Agent Fleet (NANDA Registry)
A decentralized, verified registry of specialist AI agents:
- **Orchestrator**: Manages cross-agent assessment cycles and RAG evaluation.
- **NIST/HIPAA/FHIR Specialists**: Domain-expert agents for framework-specific auditing.
- **ICAM / DevSecOps / Infrastructure Agents**: Technical auditors for specific Zero Trust pillars.
- **Mistral Intelligence**: Provides executive gap analysis and remediation planning.

### ⚖️ RAG Evaluation (Mistral-as-a-Judge)
The platform incorporates the latest Mistral RAG evaluation protocol to ensure AI-generated compliance summaries are:
- **Contextually Relevant**: Ensuring the right controls are applied to the right systems.
- **Grounded**: Verifying that assessment findings are backed by stored evidence.
- **High Fidelity**: Providing Answer Relevance scores for audit-ready documentation.

### 🤝 Collaborative Auditing (Human + AI)
The "Evidence Review" workflow enables a hybrid assessment model:
- **AI Feedback**: Mistral provides constructive, 360-degree feedback on evidence quality.
- **Status Tracking**: Seamless transition from agent-discovered findings to human-verified implementation status.
- **Audit History**: Every review decision is cryptographically anchored to the OML integrity feed.

### 🛡️ Provenance & Integrity (Sentient OML)
Every AI assessment finding and report is cryptographically fingerprinted using Sentient OML-inspired protocols. The "Integrity Feed" provides a verifiable trail of:
- Which agent performed the assessment.
- When the assessment occurred.
- The exact state of evidence used for the finding.
- A SHA-256 fingerprint for forensic auditability.

---

## Repository Structure

```
.
|-- agents/                  # Specialist AI Agent implementations
|   |-- orchestrator/        # RAG Evaluation & Fleet management
|   |-- mistral_agent/       # Mistral-as-a-Judge & Gap Analysis
|   `-- [nist/hipaa/fhir]/   # Framework specialist agents
|-- backend/
|   |-- db/                  # Async SQLite/SQLAlchemy persistent storage
|   |-- models/              # Pydantic models for Controls, Evidence, Assessments
|   `-- routers/             # REST API, NANDA registry, & OAGD simulation endpoints
|-- frontend/
|   |-- src/
|   |   |-- components/      # React components (Dashboard, Advisor, Explorer)
|   |   |-- pages/           # Sidebar-driven navigation pages
|   |   `-- types/           # Multi-framework TypeScript types
|-- schema/                  # Machine-readable OSCAL and custom catalogs
`-- tests/                   # Integration tests for Agents, Backend, & Multi-Framework
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **AI Orchestration** | FastAPI-MCP + NANDA Protocol |
| **LLM Backends** | Mistral Large 2 / Codestral / OpenAI / Ollama |
| **Backend** | FastAPI + Asynchronous SQLAlchemy + aiosqlite |
| **Frontend** | React 19 + Vite + TypeScript + Tailwind CSS |
| **Provenance** | Sentient OML-inspired SHA-256 Fingerprinting |
| **UI Icons** | Lucide React |

---

## Quick Start

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI + MCP server
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## License

MIT License - AGI Corporation 2026
