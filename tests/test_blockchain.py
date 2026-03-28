"""
Tests for the cmmc.blockchain attestation layer.
AGI Corporation 2026

Covers:
  - Control attestation (submit, history, verify)
  - SPRS score anchoring and history
  - Evidence registration and integrity verification
  - Formal C3PAO assessment submission
  - Audit trail pagination
  - Ledger integrity (hash chain verification)
  - Blockchain status and identity endpoints
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import init_db, engine, Base

os.environ.setdefault("BLOCKCHAIN_SIGNING_KEY", "test-signing-key-not-for-production")
os.environ.setdefault("BLOCKCHAIN_ORG_ID", "test-org")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_blockchain.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    if os.path.exists("./test_blockchain.db"):
        os.remove("./test_blockchain.db")


# ─── Status & Identity ────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_blockchain_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/blockchain/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert "block_height" in str(data)  # latest_block_height key present
    assert data["ledger_mode"] in ("local", "fabric", "evm")
    # org_id comes from BLOCKCHAIN_ORG_ID env var (default: "agi-corp")
    assert "org_id" in data


@pytest.mark.anyio
async def test_blockchain_identity():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/blockchain/identity")
    assert resp.status_code == 200
    data = resp.json()
    assert "org_id" in data
    assert "msp_id" in data
    assert "public_key_fingerprint" in data
    assert len(data["public_key_fingerprint"]) == 16


# ─── Control Attestation ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_submit_attestation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "status": "implemented",
            "confidence": 0.95,
            "evidence_hashes": ["abc123def456"],
            "assessor_id": "test-c3pao",
            "notes": "MFA confirmed via Okta"
        }
        resp = await ac.post("/api/blockchain/attest/AC.1.001", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "AC.1.001"
    assert data["status"] == "implemented"
    assert data["confidence"] == 0.95
    assert data["block_height"] >= 1
    assert len(data["payload_hash"]) == 64  # SHA-256 hex digest


@pytest.mark.anyio
async def test_submit_attestation_unknown_control():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/blockchain/attest/XX.9.999", json={"status": "implemented", "confidence": 0.5})
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_attestation_history():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Submit a second attestation so we have history
        await ac.post("/api/blockchain/attest/AC.1.001", json={
            "status": "partially_implemented",
            "confidence": 0.6,
        })
        resp = await ac.get("/api/blockchain/attest/AC.1.001/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "AC.1.001"
    assert data["total_records"] >= 2
    # Ordered by block_height ascending
    heights = [a["block_height"] for a in data["attestations"]]
    assert heights == sorted(heights)


@pytest.mark.anyio
async def test_attestation_verify_consistent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Update DB to match chain
        await ac.patch("/api/controls/AC.1.001", json={
            "implementation_status": "implemented",
            "notes": "Blockchain test",
            "confidence": 0.95
        })
        # Attest with matching status
        await ac.post("/api/blockchain/attest/AC.1.001", json={
            "status": "implemented",
            "confidence": 0.95,
        })
        resp = await ac.get("/api/blockchain/attest/AC.1.001/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "AC.1.001"
    assert data["chain_status"] == "implemented"
    assert data["discrepancy"] is False


# ─── SPRS Score Anchoring ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_anchor_sprs_score():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "sprs_score": 92,
            "total_controls": 110,
            "implemented": 85,
            "attestation_ids": ["tx-001", "tx-002"],
            "notes": "Q1 2026 assessment"
        }
        resp = await ac.post("/api/blockchain/sprs/anchor", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sprs_score"] == 92
    assert data["total_controls"] == 110
    assert data["implemented"] == 85
    assert data["block_height"] >= 1
    assert len(data["payload_hash"]) == 64


@pytest.mark.anyio
async def test_sprs_history():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Anchor a second score
        await ac.post("/api/blockchain/sprs/anchor", json={
            "sprs_score": 98,
            "total_controls": 110,
            "implemented": 100,
        })
        resp = await ac.get("/api/blockchain/sprs/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_anchors"] >= 2
    assert len(data["anchors"]) >= 2


# ─── Evidence ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_register_evidence():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create an evidence record first
        ev_payload = {
            "control_id": "AC.1.001",
            "zt_pillar": "User",
            "evidence_type": "log",
            "title": "Okta MFA Log",
            "description": "MFA enforcement log from Okta",
            "source_system": "Okta"
        }
        ev_resp = await ac.post("/api/evidence/", json=ev_payload)
        assert ev_resp.status_code == 200
        evidence_id = ev_resp.json()["id"]

        # Register it on chain
        resp = await ac.post(f"/api/blockchain/evidence/{evidence_id}/register")
    assert resp.status_code == 200
    data = resp.json()
    assert data["evidence_id"] == evidence_id
    assert len(data["sha256_hash"]) == 64
    assert data["block_height"] >= 1


@pytest.mark.anyio
async def test_verify_evidence_registered():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create + register
        ev_payload = {
            "control_id": "IA.1.076",
            "zt_pillar": "User",
            "evidence_type": "scan",
            "title": "Identity Scan",
            "description": "Identity verification scan",
            "source_system": "ScanTool"
        }
        ev_resp = await ac.post("/api/evidence/", json=ev_payload)
        evidence_id = ev_resp.json()["id"]
        await ac.post(f"/api/blockchain/evidence/{evidence_id}/register")

        resp = await ac.get(f"/api/blockchain/evidence/{evidence_id}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["registered"] is True
    assert data["revoked"] is False
    assert data["tx_id"] is not None


@pytest.mark.anyio
async def test_verify_evidence_not_registered():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create but do NOT register
        ev_payload = {
            "control_id": "SI.1.210",
            "zt_pillar": "Device",
            "evidence_type": "policy",
            "title": "Unregistered Policy",
            "description": "Not on chain",
            "source_system": "Internal"
        }
        ev_resp = await ac.post("/api/evidence/", json=ev_payload)
        evidence_id = ev_resp.json()["id"]

        resp = await ac.get(f"/api/blockchain/evidence/{evidence_id}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["registered"] is False


# ─── Formal Assessment ────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_submit_formal_assessment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "level": "Level 2",
            "outcome": "conditional",
            "sprs_score": 92,
            "control_count": 110,
            "assessor_org_id": "c3pao-alpha",
            "findings_hash": "a" * 64,
        }
        resp = await ac.post("/api/blockchain/assessment/submit", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["level"] == "Level 2"
    assert data["outcome"] == "conditional"
    assert data["sprs_score"] == 92
    assert len(data["payload_hash"]) == 64


# ─── Audit Trail ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_audit_trail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/blockchain/audit-trail?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_transactions" in data
    assert data["total_transactions"] >= 1
    assert isinstance(data["transactions"], list)
    # Newest first (descending block_height)
    heights = [t["block_height"] for t in data["transactions"]]
    assert heights == sorted(heights, reverse=True)


@pytest.mark.anyio
async def test_audit_trail_type_filter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/blockchain/audit-trail?tx_type=attestation")
    assert resp.status_code == 200
    data = resp.json()
    for tx in data["transactions"]:
        assert tx["tx_type"] == "attestation"


# ─── Ledger Integrity ────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_ledger_integrity():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/blockchain/integrity")
    assert resp.status_code == 200
    data = resp.json()
    assert "chain_valid" in data
    assert data["chain_valid"] is True
    assert data["issues_found"] == 0
    assert data["blocks_checked"] >= 1
