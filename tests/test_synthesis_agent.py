import pytest
import respx
import httpx
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db.database import AsyncSessionLocal, SynthesisRecord
from sqlalchemy import select

@pytest.mark.asyncio
@respx.mock
async def test_synthesis_registration_flow():
    """Test the full registration flow of the Synthesis Agent."""

    # 1. Mock Phase 1: Init
    respx.post("https://synthesis.devfolio.co/register/init").mock(
        return_value=httpx.Response(201, json={"pendingId": "test-pending-123", "message": "Success"})
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        init_data = {
            "name": "Sentient Agent",
            "description": "Multi-framework compliance agent",
            "agentHarness": "other",
            "agentHarnessOther": "Custom Sentient Orchestrator",
            "model": "mistral-large-latest",
            "humanInfo": {
                "name": "Jules",
                "email": "jules@agi.corp",
                "codingComfort": 10,
                "problemToSolve": "Compliance automation"
            }
        }

        response = await ac.post("/api/agents/synthesis/register/init", json=init_data)
        assert response.status_code == 200
        assert response.json()["pendingId"] == "test-pending-123"

        # 2. Mock Phase 2: OTP Confirm
        respx.post("https://synthesis.devfolio.co/register/verify/email/confirm").mock(
            return_value=httpx.Response(200, json={"verified": True, "method": "email"})
        )

        response = await ac.post("/api/agents/synthesis/register/verify/email/confirm?pending_id=test-pending-123&otp=123456")
        assert response.status_code == 200
        assert response.json()["verified"] is True

        # 3. Mock Phase 3: Complete
        respx.post("https://synthesis.devfolio.co/register/complete").mock(
            return_value=httpx.Response(201, json={
                "participantId": "part-456",
                "teamId": "team-789",
                "name": "Sentient Agent",
                "apiKey": "sk-synth-test-key",
                "registrationTxn": "https://basescan.org/tx/0x123"
            })
        )

        response = await ac.post("/api/agents/synthesis/register/complete?pending_id=test-pending-123")
        assert response.status_code == 200
        assert response.json()["apiKey"] == "sk-synth-test-key"

        # 4. Verify DB State
        async with AsyncSessionLocal() as session:
            query = select(SynthesisRecord).where(SynthesisRecord.pending_id == "test-pending-123")
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            assert record is not None
            assert record.status == "completed"
            assert record.api_key == "sk-synth-test-key"

@pytest.mark.asyncio
async def test_orchestrator_hackathon_task():
    """Test that Orchestrator handles HACKATHON trigger."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/orchestrator/task?trigger=hackathon&scope=Synthesis%20Registration")
        assert response.status_code == 200
        data = response.json()
        assert "synthesis" in data["assigned_agents"]
