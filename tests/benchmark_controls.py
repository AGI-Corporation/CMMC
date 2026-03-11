import asyncio
import os
import time
import uuid
from datetime import datetime, UTC, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup environment before importing database
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./benchmark.db"

from backend.db.database import Base, ControlRecord, AssessmentRecord

engine = create_async_engine("sqlite+aiosqlite:///./benchmark.db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def setup_data(num_controls=500, assessments_per_control=20):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print(f"Seeding {num_controls} controls...")
        for i in range(num_controls):
            ctrl = ControlRecord(
                id=f"CTRL.{i}",
                domain="AC",
                level="Level 2",
                title=f"Control {i}",
                description=f"Description for control {i}",
                score_value=1
            )
            session.add(ctrl)

        print(f"Seeding {num_controls * assessments_per_control} assessments...")
        for i in range(num_controls):
            for j in range(assessments_per_control):
                ass = AssessmentRecord(
                    id=str(uuid.uuid4()),
                    control_id=f"CTRL.{i}",
                    status="implemented" if j == assessments_per_control - 1 else "not_implemented",
                    assessment_date=datetime.now(UTC) - timedelta(days=assessments_per_control - j),
                    evidence_ids=["ev1", "ev2"]
                )
                session.add(ass)
            if i % 100 == 0:
                await session.flush()

        await session.commit()
        print("Seeding complete.")

async def benchmark_query():
    async with AsyncSessionLocal() as session:
        start_time = time.perf_counter()

        # This mimics the logic in list_controls
        sub_q = (
            select(
                AssessmentRecord.control_id,
                func.max(AssessmentRecord.assessment_date).label("max_date")
            )
            .group_by(AssessmentRecord.control_id)
            .subquery()
        )

        assessments_q = (
            select(AssessmentRecord)
            .join(
                sub_q,
                (AssessmentRecord.control_id == sub_q.c.control_id) &
                (AssessmentRecord.assessment_date == sub_q.c.max_date)
            )
        )

        result = await session.execute(assessments_q)
        assessments = result.scalars().all()

        end_time = time.perf_counter()
        print(f"Query took {end_time - start_time:.4f} seconds to fetch {len(assessments)} latest assessments.")
        return end_time - start_time

async def main():
    await setup_data()
    total_time = 0
    runs = 5
    for i in range(runs):
        total_time += await benchmark_query()
    print(f"Average query time: {total_time / runs:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
