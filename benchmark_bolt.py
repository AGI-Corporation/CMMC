
import asyncio
import time
import os
import uuid
from datetime import datetime, UTC
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import (
    ControlRecord, AssessmentRecord, AsyncSessionLocal, init_db, Base, engine, get_latest_assessments
)

async def seed_benchmark_data(db: AsyncSession, num_controls=200, assessments_per_control=50):
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check if we already have data
    result = await db.execute(select(func.count(ControlRecord.id)))
    if result.scalar_one() >= num_controls:
        # Check assessment count too
        result = await db.execute(select(func.count(AssessmentRecord.id)))
        if result.scalar_one() >= num_controls * assessments_per_control:
            print("Data already seeded.")
            return

    print(f"Seeding {num_controls} controls and {num_controls * assessments_per_control} assessments...")

    for i in range(num_controls):
        ctrl_id = f"TEST.{i//20}.{i%20:03d}"
        # Check if control exists
        res = await db.execute(select(ControlRecord).where(ControlRecord.id == ctrl_id))
        if not res.scalar_one_or_none():
            ctrl = ControlRecord(
                id=ctrl_id,
                domain=f"DOMAIN_{i//20}",
                level="Level 2",
                title=f"Test Control {i}",
                description="A very long description " * 100, # Make it large
                score_value=i % 5 + 1
            )
            db.add(ctrl)

        for j in range(assessments_per_control):
            assessment = AssessmentRecord(
                id=str(uuid.uuid4()),
                control_id=ctrl_id,
                status="implemented" if (i + j) % 3 == 0 else "not_implemented",
                confidence=0.8,
                notes="Some notes " * 100, # Make it large
                assessment_date=datetime.now(UTC)
            )
            db.add(assessment)

    await db.commit()
    print("Seeding complete.")

async def run_benchmark():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./benchmark.db"
    async with AsyncSessionLocal() as db:
        await seed_benchmark_data(db)

        # Benchmark get_latest_assessments (Full)
        times = []
        for _ in range(5):
            start = time.perf_counter()
            results = await get_latest_assessments(db)
            end = time.perf_counter()
            times.append(end-start)
        print(f"get_latest_assessments (Full): {sum(times)/len(times):.4f}s (found {len(results)})")

        # Benchmark get_latest_assessments (Selective)
        times = []
        for _ in range(5):
            start = time.perf_counter()
            sub_q = select(
                AssessmentRecord.control_id,
                func.max(AssessmentRecord.assessment_date).label("max_date"),
            ).group_by(AssessmentRecord.control_id).subquery()

            query = select(AssessmentRecord.control_id, AssessmentRecord.status).join(
                sub_q,
                (AssessmentRecord.control_id == sub_q.c.control_id)
                & (AssessmentRecord.assessment_date == sub_q.c.max_date),
            )
            result = await db.execute(query)
            results = {a.control_id: a for a in result.all()}
            end = time.perf_counter()
            times.append(end-start)
        print(f"get_latest_assessments (Selective): {sum(times)/len(times):.4f}s (found {len(results)})")

        # Benchmark ControlRecord fetch (Full)
        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = await db.execute(select(ControlRecord))
            controls = result.scalars().all()
            end = time.perf_counter()
            times.append(end-start)
        print(f"ControlRecord fetch (Full): {sum(times)/len(times):.4f}s (found {len(controls)})")

        # Benchmark ControlRecord fetch (Selective)
        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = await db.execute(select(ControlRecord.id, ControlRecord.domain, ControlRecord.level, ControlRecord.score_value))
            controls = result.all()
            end = time.perf_counter()
            times.append(end-start)
        print(f"ControlRecord fetch (Selective): {sum(times)/len(times):.4f}s (found {len(controls)})")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
