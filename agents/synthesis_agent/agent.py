from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
import httpx
import os
import json
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import get_db, SynthesisRecord
from sqlalchemy import select, update

router = APIRouter()

BASE_URL = "https://synthesis.devfolio.co"

class SynthesisAgent:
    def __init__(self):
        self.agent_id = "synthesis-01"
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    async def register_init(self, db: AsyncSession, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Initiate registration."""
        response = await self.client.post("/register/init", json=agent_data)
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        data = response.json()
        pending_id = data["pendingId"]

        # Save to local DB
        new_reg = SynthesisRecord(
            pending_id=pending_id,
            status="pending",
            created_at=datetime.now(UTC)
        )
        db.add(new_reg)
        await db.commit()

        return data

    async def verify_email_send(self, pending_id: str) -> Dict[str, Any]:
        """Phase 2a: Send Email OTP."""
        response = await self.client.post("/register/verify/email/send", json={"pendingId": pending_id})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        return response.json()

    async def verify_email_confirm(self, db: AsyncSession, pending_id: str, otp: str) -> Dict[str, Any]:
        """Phase 2b: Confirm Email OTP."""
        response = await self.client.post("/register/verify/email/confirm", json={"pendingId": pending_id, "otp": otp})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        data = response.json()
        if data.get("verified"):
            await db.execute(
                update(SynthesisRecord)
                .where(SynthesisRecord.pending_id == pending_id)
                .values(status="verified")
            )
            await db.commit()
        return data

    async def register_complete(self, db: AsyncSession, pending_id: str) -> Dict[str, Any]:
        """Phase 3: Complete registration and get API key."""
        response = await self.client.post("/register/complete", json={"pendingId": pending_id})
        if response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        data = response.json()

        # Update local DB with credentials
        await db.execute(
            update(SynthesisRecord)
            .where(SynthesisRecord.pending_id == pending_id)
            .values(
                api_key=data["apiKey"],
                participant_id=data["participantId"],
                team_id=data["teamId"],
                registration_txn=data.get("registrationTxn"),
                status="completed"
            )
        )
        await db.commit()

        return data

    async def get_auth_header(self, db: AsyncSession, pending_id: str) -> Dict[str, str]:
        """Retrieve the API key for authenticated requests."""
        query = select(SynthesisRecord).where(SynthesisRecord.pending_id == pending_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        if not record or not record.api_key:
            raise HTTPException(status_code=401, detail="Agent not registered or API key missing.")
        return {"Authorization": f"Bearer {record.api_key}"}

    async def get_team(self, db: AsyncSession, pending_id: str, team_uuid: str) -> Dict[str, Any]:
        """Get team details."""
        headers = await self.get_auth_header(db, pending_id)
        response = await self.client.get(f"/teams/{team_uuid}", headers=headers)
        return response.json()

_synthesis = SynthesisAgent()

@router.post("/register/init")
async def init_reg(agent_data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    return await _synthesis.register_init(db, agent_data)

@router.post("/register/verify/email/send")
async def send_otp(pending_id: str):
    return await _synthesis.verify_email_send(pending_id)

@router.post("/register/verify/email/confirm")
async def confirm_otp(pending_id: str, otp: str, db: AsyncSession = Depends(get_db)):
    return await _synthesis.verify_email_confirm(db, pending_id, otp)

@router.post("/register/complete")
async def complete_reg(pending_id: str, db: AsyncSession = Depends(get_db)):
    return await _synthesis.register_complete(db, pending_id)
