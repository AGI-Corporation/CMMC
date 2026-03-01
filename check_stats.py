import asyncio
from backend.db.database import get_db
from sqlalchemy import select
from backend.models.control import ControlRecord

async def check():
    async with get_db() as db:
        res = await db.execute(select(ControlRecord).where(ControlRecord.framework == "HIPAA"))
        controls = res.scalars().all()
        by_level = {}
        for c in controls:
            lvl = c.level or "N/A"
            if lvl not in by_level:
                by_level[lvl] = {"total": 0}
            by_level[lvl]["total"] += 1
        print(f"HIPAA levels: {by_level}")

asyncio.run(check())
