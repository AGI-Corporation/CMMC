import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.anyio
async def test_confidence_validation_too_high():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        update_data = {
            "implementation_status": "implemented",
            "confidence": 1.1
        }
        response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert response.status_code == 422

@pytest.mark.anyio
async def test_confidence_validation_too_low():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        update_data = {
            "implementation_status": "implemented",
            "confidence": -0.1
        }
        response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert response.status_code == 422

@pytest.mark.anyio
async def test_confidence_validation_valid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        update_data = {
            "implementation_status": "implemented",
            "confidence": 0.5
        }
        response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert response.status_code == 200
