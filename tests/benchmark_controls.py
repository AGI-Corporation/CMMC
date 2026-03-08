import asyncio
import time
import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func, text
import os
import sys

# Add current directory to path so we can import backend
sys.path.append(os.getcwd())

# Ensure we use a clean test database
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_benchmark.db"

from backend.db.database import AsyncSessionLocal, ControlRecord, AssessmentRecord, init_db

async def seed_data(num_controls=500, assessments_per_control=20):
    async with AsyncSessionLocal() as session:
        # Clear existing data
        await session.execute(text("DELETE FROM assessments"))
        await session.execute(text("DELETE FROM controls"))
        await session.commit()

        print(f"Seeding {num_controls} controls...")
        for i in range(num_controls):
            c = ControlRecord(
                id=f"TEST.{i}",
                domain="AC",
                level="Level 1",
                title=f"Test Control {i}",
                description=f"Description for test control {i}",
                nist_mapping="3.1.1",
                score_value=1
            )
            session.add(c)

        await session.commit()

        print(f"Seeding {num_controls * assessments_per_control} assessments...")
        for i in range(num_controls):
            for j in range(assessments_per_control):
                a = AssessmentRecord(
                    id=str(uuid.uuid4()),
                    control_id=f"TEST.{i}",
                    status="implemented" if j == assessments_per_control - 1 else "not_implemented",
                    assessment_date=datetime.now(UTC) - timedelta(days=assessments_per_control - j),
                    confidence=0.9,
                    notes=f"Assessment {j} for control {i}",
                    poam_required="false"
                )
                session.add(a)
            if i % 100 == 0:
                await session.commit()
        await session.commit()

async def benchmark_list_controls_original():
    async with AsyncSessionLocal() as session:
        start_time = time.perf_counter()

        # Original logic from backend/routers/controls.py
        query = select(ControlRecord)

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

        ctrl_result = await session.execute(query)
        controls_data = ctrl_result.scalars().all()

        ass_result = await session.execute(assessments_q)
        assessments_map = {a.control_id: a for a in ass_result.scalars().all()}

        responses = []
        for c in controls_data:
            assessment = assessments_map.get(c.id)
            impl_status = assessment.status if assessment else "not_started"

            responses.append({
                "id": c.id,
                "status": impl_status,
                "evidence_count": len(assessment.evidence_ids) if assessment and isinstance(assessment.evidence_ids, list) else 0,
            })

        end_time = time.perf_counter()
        return end_time - start_time

async def benchmark_list_controls_optimized():
    async with AsyncSessionLocal() as session:
        start_time = time.perf_counter()

        # Optimized logic from backend/routers/controls.py
        sub_q = (
            select(
                AssessmentRecord.control_id,
                func.max(AssessmentRecord.assessment_date).label("max_date")
            )
            .group_by(AssessmentRecord.control_id)
            .subquery()
        )

        query = (
            select(ControlRecord, AssessmentRecord)
            .outerjoin(
                sub_q,
                ControlRecord.id == sub_q.c.control_id
            )
            .outerjoin(
                AssessmentRecord,
                (AssessmentRecord.control_id == sub_q.c.control_id) &
                (AssessmentRecord.assessment_date == sub_q.c.max_date)
            )
        )

        result = await session.execute(query)
        rows = result.all()

        responses = []
        for c, assessment in rows:
            impl_status = assessment.status if assessment else "not_started"

            responses.append({
                "id": c.id,
                "status": impl_status,
                "evidence_count": len(assessment.evidence_ids) if assessment and isinstance(assessment.evidence_ids, list) else 0,
            })

        end_time = time.perf_counter()
        return end_time - start_time

async def main():
    await init_db()
    await seed_data()

    print("Running original benchmark...")
    times = []
    for _ in range(5):
        duration = await benchmark_list_controls_original()
        times.append(duration)
        print(f"Iteration: {duration:.4f}s")

    avg_original = sum(times)/len(times)
    print(f"Average time (Original): {avg_original:.4f}s")

    print("\nRunning optimized benchmark...")
    times = []
    for _ in range(5):
        duration = await benchmark_list_controls_optimized()
        times.append(duration)
        print(f"Iteration: {duration:.4f}s")

    avg_optimized = sum(times)/len(times)
    print(f"Average time (Optimized): {avg_optimized:.4f}s")

    print(f"\nImprovement: {((avg_original - avg_optimized) / avg_original) * 100:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
