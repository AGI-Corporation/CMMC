# CMMC Compliance Framework — cmmc.blockchain

> AI-powered CMMC 2.0 compliance automation platform with blockchain-anchored attestations. Built by AGI Corporation on the `cmmc.blockchain` domain. Leverages Model Context Protocol (MCP), NIST OSCAL schemas, FastAPI, and a SHA-256 Merkle ledger for tamper-evident compliance records.

---

## Overview

This platform addresses the **Cybersecurity Maturity Model Certification (CMMC) 2.0** framework, which entered Phase 1 implementation on November 10, 2025. It targets Defense Industrial Base (DIB) contractors needing to comply with:

- **Level 1**: 17 controls (FAR 52.204-21) - Basic FCI protection
- **Level 2**: 110 controls (NIST SP 800-171 Rev 2) - CUI protection
- **Level 3**: 110+ controls (NIST SP 800-172) - Advanced CUI

### What makes this `cmmc.blockchain`?

Every compliance event is cryptographically anchored in a tamper-evident ledger:
- **SHA-256 hashing** — every payload is content-hashed before storage
- **Merkle-style chaining** — each transaction includes the hash of the previous record
- **HMAC-SHA256 signatures** — platform signatures protect against record tampering
- **Monotonic block heights** — total ordering of all compliance events
- **Off-chain privacy** — CUI/FCI content never enters the ledger; only hashes and metadata

The ledger operates in **local mode** (DB-backed, full cryptographic integrity) by default and is designed to anchor to **Hyperledger Fabric** or **Polygon Edge** via `BLOCKCHAIN_ANCHOR_URL`.

---

## Architecture

```
cmmc.blockchain (Unstoppable Domains .blockchain TLD)
     IPFS-hosted React Frontend (Vite + React 19 + Tailwind)
                    |
     FastAPI Backend + Blockchain Service Layer
       /api/blockchain/* — Attestation, SPRS, Evidence, Assessment
       /api/controls, /api/assessment, /api/evidence, /api/reports
       /mcp — MCP protocol endpoint (Claude Desktop, Goose)
                    |
      ┌─────────────┴──────────────────────┐
      │                                    │
SQLite/PostgreSQL                   Blockchain Ledger
(off-chain: CUI content,            (on-chain: SHA-256 hashes,
 full text, assessments)             SPRS anchors, attestation
                                     chains, evidence registry)
```

---

## Repository Structure

```
CMMC/
├── README.md
├── requirements.txt
├── .env.example
├── schema/
│   └── cmmc_oscal_catalog.json       # OSCAL CMMC Level 1 & 2 controls
├── backend/
│   ├── main.py                       # FastAPI + fastapi-mcp server
│   ├── db/
│   │   └── database.py               # SQLAlchemy models + BlockchainTransaction table
│   ├── models/
│   │   ├── control.py                # Control Pydantic models
│   │   ├── evidence.py               # Evidence Pydantic models
│   │   └── blockchain.py             # Blockchain attestation models ⬅ NEW
│   ├── services/
│   │   └── blockchain_service.py     # SHA-256 Merkle ledger service ⬅ NEW
│   └── routers/
│       ├── controls.py
│       ├── assessment.py
│       ├── evidence.py
│       ├── reports.py
│       └── blockchain.py             # /api/blockchain/* endpoints ⬅ NEW
├── agents/
│   ├── orchestrator/agent.py
│   ├── icam_agent/agent.py
│   ├── devsecops_agent/agent.py
│   └── mistral_agent/agent.py
├── frontend/                         # React 19 + TypeScript + Tailwind ⬅ NEW
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/Layout.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx         # Compliance posture + charts
│   │   │   ├── ControlsGrid.tsx      # All CMMC controls with filters
│   │   │   ├── BlockchainExplorer.tsx # Audit trail viewer
│   │   │   ├── AttestationWizard.tsx # Guided on-chain attestation
│   │   │   ├── Reports.tsx           # SSP/POAM download
│   │   │   └── PublicVerify.tsx      # Public certification page
│   │   ├── lib/api.ts                # API client
│   │   └── types/api.ts              # TypeScript types
│   └── vite.config.ts
└── tests/
    ├── test_backend.py
    ├── test_agents.py
    └── test_blockchain.py            # 15 blockchain tests ⬅ NEW
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP Host | Claude Desktop / Goose Desktop |
| MCP Server | `fastapi-mcp` (Python) |
| Backend | FastAPI + Uvicorn |
| Blockchain | SHA-256 Merkle ledger (local) → Hyperledger Fabric / Polygon Edge (production) |
| Schema | NIST OSCAL JSON (machine-readable) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS |
| Charts | Recharts (RadarChart, BarChart, LineChart) |
| AI | Mistral AI / OpenAI GPT-4 / Claude / Ollama (local) |
| Domain | Unstoppable Domains `.blockchain` TLD |
| Crypto | Python `hashlib` (SHA-256), `hmac` (HMAC-SHA256) — stdlib, no new deps |

---

## Quick Start

### Backend

```bash
git clone https://github.com/AGI-Corporation/CMMC.git
cd CMMC

pip install -r requirements.txt
cp .env.example .env

# Run the FastAPI + MCP + blockchain server
uvicorn backend.main:app --reload
# API: http://localhost:8000/docs
# MCP: http://localhost:8000/mcp
# Blockchain: http://localhost:8000/api/blockchain/status
```

### Frontend (cmmc.blockchain UI)

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### MCP Integration (Claude Desktop)

```json
{
  "mcpServers": {
    "cmmc": { "url": "http://localhost:8000/mcp" }
  }
}
```

---

## Blockchain API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/blockchain/attest/{control_id}` | Submit on-chain attestation |
| `GET` | `/api/blockchain/attest/{control_id}/history` | Full attestation audit trail |
| `GET` | `/api/blockchain/attest/{control_id}/verify` | Verify attestation vs DB state |
| `POST` | `/api/blockchain/sprs/anchor` | Anchor SPRS score on-chain |
| `GET` | `/api/blockchain/sprs/history` | SPRS score history from chain |
| `POST` | `/api/blockchain/evidence/{id}/register` | Register evidence hash on-chain |
| `GET` | `/api/blockchain/evidence/{id}/verify` | Verify evidence integrity |
| `POST` | `/api/blockchain/assessment/submit` | Submit formal C3PAO assessment |
| `GET` | `/api/blockchain/audit-trail` | Paginated full audit trail |
| `GET` | `/api/blockchain/integrity` | Verify ledger hash-chain integrity |
| `GET` | `/api/blockchain/status` | Ledger node health |
| `GET` | `/api/blockchain/identity` | Org MSP identity / signing info |

### Blockchain Configuration (`.env`)

```bash
BLOCKCHAIN_ENABLED=true
BLOCKCHAIN_LEDGER_MODE=local        # local | fabric | evm
BLOCKCHAIN_ORG_ID=agi-corp
BLOCKCHAIN_MSP_ID=AgiCorpMSP
BLOCKCHAIN_CHAIN_ID=cmmc-blockchain-mainnet
BLOCKCHAIN_SIGNING_KEY=<use-hsm-in-production>
BLOCKCHAIN_ANCHOR_URL=              # External node URL (optional)
BLOCKCHAIN_DOMAIN=cmmc.blockchain
```

---

## CMMC Control Domains (14 Families)

| Domain | Code | L1 | L2 |
|---|---|---|---|
| Access Control | AC | 2 | 22 |
| Audit & Accountability | AU | 0 | 9 |
| Configuration Management | CM | 0 | 9 |
| Identification & Authentication | IA | 1 | 11 |
| Incident Response | IR | 0 | 3 |
| Maintenance | MA | 0 | 6 |
| Media Protection | MP | 1 | 9 |
| Personnel Security | PS | 0 | 2 |
| Physical Protection | PE | 4 | 6 |
| Risk Assessment | RA | 0 | 5 |
| Security Assessment | CA | 0 | 4 |
| Situational Awareness | SA | 0 | 1 |
| System & Comms Protection | SC | 2 | 16 |
| System & Info Integrity | SI | 5 | 7 |
| **Total** | | **17** | **110** |

---

## MCP Tools Available

- `list_controls` — List all CMMC controls by domain/level
- `get_control_detail` — Get full details of a specific control
- `submit_assessment` — Submit assessment status for a control
- `upload_evidence` — Associate evidence artifacts with controls
- `calculate_sprs_score` — Calculate SPRS score (DoD supplier risk score)
- `generate_ssp` — Generate System Security Plan in Markdown
- `generate_poam` — Generate POAM CSV for unimplemented controls
- `get_compliance_dashboard` — Get overall compliance posture summary

Plus all 12 blockchain endpoints are automatically exposed as MCP tools via `fastapi-mcp`.

---

## Key Resources

- [CMMC Official Site](https://dodcio.defense.gov/CMMC/)
- [NIST SP 800-171 Rev 2](https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final)
- [OSCAL Catalog Model](https://pages.nist.gov/OSCAL/learn/concepts/layer/control/catalog/)
- [Unstoppable Domains .blockchain](https://unstoppabledomains.com)
- [Hyperledger Fabric](https://www.hyperledger.org/projects/fabric)
- [ComplianceCow MCP](https://github.com/ComplianceCow/cow-mcp)
- [GitHub MCP Server](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/set-up-the-github-mcp-server)
- [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp)

---

## License

MIT License — AGI Corporation 2026


> AI-powered CMMC 2.0 compliance automation platform built for the AGI Corporation hackathon. Leverages Model Context Protocol (MCP), OSCAL machine-readable schemas, and FastAPI to automate evidence collection, control assessments, and SSP/POAM generation.

---

## Overview

This platform addresses the **Cybersecurity Maturity Model Certification (CMMC) 2.0** framework, which entered Phase 1 implementation on November 10, 2025. It targets Defense Industrial Base (DIB) contractors needing to comply with:

- **Level 1**: 17 controls (FAR 52.204-21) - Basic FCI protection
- **Level 2**: 110 controls (NIST SP 800-171 Rev 2) - CUI protection
- **Level 3**: 110+ controls (NIST SP 800-172) - Advanced CUI

---

## Architecture

```
MCP HOST (Claude / Goose Desktop)
        |
        | MCP Protocol
        v
FastAPI-MCP Backend (/mcp endpoint)
  - CMMC Controls API (OSCAL JSON schema)
  - Evidence Collection Endpoints
  - Assessment Scoring Engine
  - POAM / SSP Generator
        |
   _____|______________________
  |            |               |
GitHub MCP  ComplianceCow   NIST OSCAL
(code/PRs)  (GRC workflows) (controls catalog)
```

---

## Repository Structure

```
CMMC/
|-- README.md
|-- requirements.txt
|-- .env.example
|-- schema/
|   |-- cmmc_oscal_catalog.json      # OSCAL CMMC Level 1 & 2 controls
|   |-- cmmc_controls_l1.json        # Level 1 (17 controls)
|   |-- cmmc_controls_l2.json        # Level 2 (110 controls)
|   `-- evidence_schema.json         # Evidence collection schema
|-- backend/
|   |-- main.py                      # FastAPI + fastapi-mcp server
|   |-- routers/
|   |   |-- controls.py              # Controls CRUD endpoints
|   |   |-- assessment.py            # Assessment scoring
|   |   |-- evidence.py              # Evidence management
|   |   `-- reports.py               # SSP/POAM generation
|   |-- models/
|   |   |-- control.py               # Pydantic models
|   |   |-- assessment.py
|   |   `-- evidence.py
|   `-- db/
|       `-- database.py              # SQLite/PostgreSQL setup
|-- mcp/
|   |-- mcp.json                     # MCP server configuration
|   |-- cmmc_mcp_server.py           # Custom CMMC MCP server
|   `-- tools/
|       |-- control_lookup.py        # Look up CMMC controls
|       |-- evidence_collector.py    # Collect & map evidence
|       |-- score_calculator.py      # SPRS score calculation
|       `-- report_generator.py      # SSP/POAM generation
|-- frontend/
|   |-- package.json
|   `-- src/
|       |-- App.tsx
|       |-- components/
|       |   |-- Dashboard.tsx        # Compliance score dashboard
|       |   |-- ControlsGrid.tsx     # 14-domain controls grid
|       |   |-- EvidenceUpload.tsx   # Evidence management
|       |   |-- AssessmentWizard.tsx # Step-by-step assessment
|       |   `-- ReportExport.tsx     # SSP/POAM export
|       `-- types/
|           `-- cmmc.ts              # TypeScript types
`-- docs/
    |-- SSP_template.md              # System Security Plan template
    |-- POAM_template.md             # Plan of Action & Milestones
    `-- deployment.md                # Deployment guide
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP Host | Claude Desktop / Goose Desktop |
| MCP Server | `fastapi-mcp` (Python) |
| Backend | FastAPI + Uvicorn |
| Schema | NIST OSCAL JSON (machine-readable) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | React 19 + TypeScript + Tailwind CSS |
| AI | OpenAI GPT-4 / Claude / Ollama (local) |
| GRC Automation | ComplianceCow MCP |
| Repo Automation | GitHub MCP Server |

---

## Quick Start

### Backend

```bash
# Clone the repo
git clone https://github.com/AGI-Corporation/CMMC.git
cd CMMC

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run the FastAPI + MCP server
uvicorn backend.main:app --reload
# MCP endpoint available at: http://localhost:8000/mcp
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### MCP Integration (Claude Desktop)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cmmc": {
      "url": "http://localhost:8000/mcp"
    },
    "github": {
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}
```

---

## CMMC Control Domains (14 Families)

| Domain | Code | L1 Controls | L2 Controls |
|---|---|---|---|
| Access Control | AC | 2 | 22 |
| Audit & Accountability | AU | 0 | 9 |
| Configuration Management | CM | 0 | 9 |
| Identification & Authentication | IA | 1 | 11 |
| Incident Response | IR | 0 | 3 |
| Maintenance | MA | 0 | 6 |
| Media Protection | MP | 1 | 9 |
| Personnel Security | PS | 0 | 2 |
| Physical Protection | PE | 4 | 6 |
| Risk Assessment | RA | 0 | 5 |
| Security Assessment | CA | 0 | 4 |
| Situational Awareness | SA | 0 | 1 |
| System & Comms Protection | SC | 2 | 16 |
| System & Info Integrity | SI | 5 | 7 |
| **Total** | | **17** | **110** |

---

## MCP Tools Available

Once the server is running, the following MCP tools are available to AI agents:

- `list_controls` - List all CMMC controls by domain/level
- `get_control_detail` - Get full details of a specific control
- `submit_assessment` - Submit assessment status for a control
- `upload_evidence` - Associate evidence artifacts with controls
- `calculate_sprs_score` - Calculate SPRS score (DoD supplier risk score)
- `generate_ssp` - Generate System Security Plan in Markdown
- `generate_poam` - Generate POAM CSV for unimplemented controls
- `get_compliance_dashboard` - Get overall compliance posture summary

---

## Key Resources

- [CMMC Official Site](https://dodcio.defense.gov/CMMC/)
- [NIST SP 800-171 Rev 2](https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final)
- [OSCAL Catalog Model](https://pages.nist.gov/OSCAL/learn/concepts/layer/control/catalog/)
- [ComplianceCow MCP](https://github.com/ComplianceCow/cow-mcp)
- [GitHub MCP Server](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/set-up-the-github-mcp-server)
- [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp)

---

## License

MIT License - AGI Corporation 2026
