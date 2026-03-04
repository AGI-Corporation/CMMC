
import asyncio
import time
import os
import uuid
import statistics
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

# Set up environment for benchmark
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./benchmark.db"

from backend.main import app
from backend.db.database import Base, ControlRecord, AssessmentRecord, init_db

async def seed_benchmark_data():
    engine = create_async_engine("sqlite+aiosqlite:///./benchmark.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # 1. Seed 110 controls (Standard CMMC Level 2)
        controls = []
        for i in range(110):
            cid = f"AC.2.{i+1:03d}"
            ctrl = ControlRecord(
                id=cid,
                domain="AC",
                level="Level 2",
                title=f"Benchmark Control {i+1}",
                description=f"Description for control {i+1}",
                score_value=1 if i % 5 != 0 else 5
            )
            controls.append(ctrl)
            session.add(ctrl)

        # 2. Seed 10 assessments per control (1100 total)
        # We want to simulate history, so the latest one is what matters
        for ctrl in controls:
            for j in range(10):
                assessment = AssessmentRecord(
                    id=str(uuid.uuid4()),
                    control_id=ctrl.id,
                    status="implemented" if j == 9 else "not_implemented",
                    assessment_date=datetime.now(UTC) - timedelta(days=10-j),
                    confidence=0.9,
                    notes=f"Assessment history {j}",
                    evidence_ids=["ev-1", "ev-2"]
                )
                session.add(assessment)

        await session.commit()
    await engine.dispose()

async def run_benchmark():
    print("Seeding benchmark data...")
    await seed_benchmark_data()

    print("Running benchmark on /api/controls/ ...")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. No filter
        print("\nTest 1: No filter")
        latencies = []
        await ac.get("/api/controls/") # Warmup
        for _ in range(50):
            start_time = time.perf_counter()
            response = await ac.get("/api/controls/")
            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)
        print(f"Avg: {statistics.mean(latencies):.2f} ms, P95: {statistics.quantiles(latencies, n=20)[18]:.2f} ms")

        # 2. Status filter (should be faster with SQL filtering)
        print("\nTest 2: Status filter (implemented)")
        latencies = []
        await ac.get("/api/controls/?status=implemented") # Warmup
        for _ in range(50):
            start_time = time.perf_counter()
            response = await ac.get("/api/controls/?status=implemented")
            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)
        print(f"Avg: {statistics.mean(latencies):.2f} ms, P95: {statistics.quantiles(latencies, n=20)[18]:.2f} ms")

    avg_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18] # 19th 5-percentile is p95

    print(f"\nResults (50 requests):")
    print(f"Average Latency: {avg_latency:.2f} ms")
    print(f"Median Latency:  {median_latency:.2f} ms")
    print(f"P95 Latency:     {p95_latency:.2f} ms")

    # Clean up
    if os.path.exists("./benchmark.db"):
        os.remove("./benchmark.db")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
