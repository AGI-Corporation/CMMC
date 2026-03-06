
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.anyio
async def test_voice_advise():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        req = {
            "question": "What are the requirements for MFA in CMMC Level 2?",
            "context": "Focus on IA.3.083"
        }
        response = await ac.post("/api/agents/voice/advise", json=req)

    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "advice_text" in data
    assert "audio_url" in data
    assert "voice_id" in data
    assert data["question"] == req["question"]
    assert data["audio_url"].startswith("/api/assets/audio/")
