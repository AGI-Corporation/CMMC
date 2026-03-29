import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.db.database import Base, engine, init_db
from backend.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Use a separate test database
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_api.db"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield
    # Cleanup
    if os.path.exists("./test_api.db"):
        os.remove("./test_api.db")


@pytest.mark.anyio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_list_controls():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/controls/")
    assert response.status_code == 200
    data = response.json()
    assert "controls" in data
    assert data["total"] > 0
    # Check for AC.1.001 which should be seeded
    control_ids = [c["control"]["id"] for c in data["controls"]]
    assert "AC.1.001" in control_ids


@pytest.mark.anyio
async def test_update_and_score():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Check SPRS score initial
        response = await ac.get("/api/assessment/sprs")
        data = response.json()
        initial_score = data["sprs_score"]

        # 2. Update to implemented
        update_data = {
            "implementation_status": "implemented",
            "notes": "Test fix",
            "responsible_party": "Tester",
        }
        patch_response = await ac.patch("/api/controls/AC.1.001", json=update_data)
        assert patch_response.status_code == 200

        # 3. Check SPRS score again
        response = await ac.get("/api/assessment/sprs")
        data = response.json()
        # AC.1.001 has deduction 3.
        assert data["sprs_score"] == initial_score + 3


@pytest.mark.anyio
async def test_reports():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Check dashboard
        resp = await ac.get("/api/reports/dashboard")
        assert resp.status_code == 200

        # 2. Check SSP
        resp = await ac.get("/api/reports/ssp")
        assert resp.status_code == 200
        assert "# System Security Plan" in resp.text

        # 3. Check POAM
        resp = await ac.get("/api/reports/poam")
        assert resp.status_code == 200
        assert "Control ID,Domain" in resp.text


@pytest.mark.anyio
async def test_update_with_advanced_fields():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        update_data = {
            "implementation_status": "implemented",
            "notes": "Advanced update",
            "responsible_party": "Tester",
            "confidence": 0.95,
            "poam_required": False,
            "evidence_ids": ["ev-123"],
        }
        patch_response = await ac.patch("/api/controls/AC.1.002", json=update_data)
        assert patch_response.status_code == 200
        data = patch_response.json()
        assert data["confidence"] == 0.95
        assert data["poam_required"] == False

        # Verify detail endpoint reflects these
        detail_response = await ac.get("/api/controls/AC.1.002")
        data = detail_response.json()
        assert data["confidence"] == 0.95
        assert data["evidence_count"] == 1
        assert data["poam_required"] == False
