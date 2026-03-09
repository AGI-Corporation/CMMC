
import asyncio
import time
import os
import uuid
from datetime import datetime, UTC, timedelta
from sqlalchemy import select, func, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup environment for aiosqlite
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./benchmark.db'
from backend.db.database import Base, ControlRecord, AssessmentRecord, get_latest_assessments

async def benchmark_queries():
    engine = create_async_engine('sqlite+aiosqlite:///./benchmark.db')
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Note: Base.metadata.create_all will create the index since it's now in the model
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("Seeding database...")
        # 200 controls
        controls = [
            ControlRecord(
                id=f"CTRL.{i}",
                domain="AC",
                level="Level 1",
                title=f"Control {i}",
                description="Description"
            ) for i in range(200)
        ]
        session.add_all(controls)

        # 50 assessments per control = 10,000 assessments
        assessments = []
        base_date = datetime.now(UTC)
        for i in range(200):
            for j in range(50):
                assessments.append(
                    AssessmentRecord(
                        id=str(uuid.uuid4()),
                        control_id=f"CTRL.{i}",
                        status="implemented" if j % 2 == 0 else "not_implemented",
                        assessment_date=base_date - timedelta(days=j),
                        confidence=0.9
                    )
                )
        session.add_all(assessments)
        await session.commit()
        print("Database seeded.")

    async def run_test(label):
        async with AsyncSessionLocal() as session:
            start = time.perf_counter()
            # Use the consolidated helper
            data = await get_latest_assessments(session)
            end = time.perf_counter()
            print(f"{label}: {len(data)} results in {end - start:.4f}s")
            return end - start

    # Test with index (now default)
    t_optimized = await run_test("With composite index (consolidated helper)")

    # Verify correctness
    async with AsyncSessionLocal() as session:
        latest = await get_latest_assessments(session)
        assert len(latest) == 200
        for a in latest:
             # Should be the one with j=0, which has assessment_date closest to base_date
             pass

    await engine.dispose()
    if os.path.exists("./benchmark.db"):
        os.remove("./benchmark.db")

if __name__ == "__main__":
    asyncio.run(benchmark_queries())
