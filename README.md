# CMMC Compliance Framework

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

## FHIR Evidence Integration (BabelFHIR-TS)

Healthcare DIB contractors using FHIR® R4 can feed their clinical system
artifacts directly into the CMMC compliance engine as machine-readable evidence.

### How it works

```
FHIR EHR System
    │  AuditEvent / Device / Consent / Observation …
    ▼
POST /api/fhir/ingest           ← Python FastAPI backend
    │  ┌─────────────────────────────────────────┐
    │  │  Optional: BabelFHIR-TS validation      │
    │  │  sidecar  (fhir-service/, port 3100)    │
    │  │  @babelfhir-ts/client-r4  +  FHIRPath   │
    │  └─────────────────────────────────────────┘
    │
    ▼
EvidenceRecord rows  ──►  CMMC Assessment Dashboard
```

### FHIR → CMMC control mapping

| FHIR Resource Type | CMMC Controls | ZT Pillar |
|---|---|---|
| `AuditEvent` | AU.2.041, AU.2.042, AU.2.043, AU.3.045, AU.3.046, AU.3.048 | Visibility & Analytics |
| `Consent` | AC.2.006, AC.2.007, AC.3.018 | User |
| `Device` | CM.2.061, CM.2.062, CM.3.068 | Device |
| `DocumentReference` | AU.3.046, AU.3.048 | Visibility & Analytics |
| `Observation` | RA.2.141, RA.2.142 | Visibility & Analytics |
| `Patient` | AC.1.001, AC.1.002 | User |
| `Practitioner` | IA.1.076, IA.1.077, IA.3.083 | User |
| `PractitionerRole` | IA.1.076, IA.1.077, AC.2.007 | User |
| `Communication` | SC.1.175, SC.1.176, SC.3.177 | Network |
| `OperationOutcome` | SI.1.210, SI.1.211 | Application |

Full mapping reference: `GET /api/fhir/mappings`

### FHIR API endpoints

```
POST /api/fhir/ingest              Ingest any supported FHIR R4 resource
POST /api/fhir/audit-event         Shortcut for AuditEvent → AU domain
GET  /api/fhir/mappings            List all resource-type → control mappings
GET  /api/fhir/mappings/{type}     Lookup one resource type
```

### BabelFHIR-TS validation sidecar

The `fhir-service/` directory contains a Node.js TypeScript microservice that
uses [`@babelfhir-ts/client-r4`](https://www.npmjs.com/package/@babelfhir-ts/client-r4)
to validate FHIR resources before they are ingested as CMMC evidence.

```bash
cd fhir-service
npm install
npm run build
PORT=3100 npm start
```

Set `FHIR_VALIDATOR_URL=http://localhost:3100` in your backend `.env` to enable
validation. Set `FHIR_VALIDATOR_STRICT=false` to allow warnings without
blocking ingestion.

To add US Core profile-aware validation:

```bash
npx babelfhir-ts install hl7.fhir.us.core@8.0.0 --output fhir-service/src/generated
```

---



- [CMMC Official Site](https://dodcio.defense.gov/CMMC/)
- [NIST SP 800-171 Rev 2](https://csrc.nist.gov/pubs/sp/800/171/r2/upd1/final)
- [OSCAL Catalog Model](https://pages.nist.gov/OSCAL/learn/concepts/layer/control/catalog/)
- [ComplianceCow MCP](https://github.com/ComplianceCow/cow-mcp)
- [GitHub MCP Server](https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/set-up-the-github-mcp-server)
- [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp)

---

## License

MIT License - AGI Corporation 2026
