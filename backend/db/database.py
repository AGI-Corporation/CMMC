"""
Database initialization and session management.
AGI Corporation CMMC Platform 2026
"""
import os
import json
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, select, func, Index
from datetime import datetime, UTC

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cmmc.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


class ControlRecord(Base):
    __tablename__ = "controls"
    id = Column(String, primary_key=True, index=True)  # e.g. AC.1.001
    domain = Column(String, index=True)
    level = Column(String)
    title = Column(String)
    description = Column(Text)
    zt_pillar = Column(String)  # User/Device/Network/App/Data/Visibility/Automation
    nist_mapping = Column(String)  # e.g. 3.1.1
    status = Column(String, default="not_implemented")  # implemented/partial/planned/not_implemented
    score_value = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class EvidenceRecord(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, index=True)
    control_id = Column(String, index=True)
    zt_pillar = Column(String)
    zt_capability_id = Column(String)
    evidence_type = Column(String)  # log/scan/policy/diagram/screenshot
    title = Column(String)
    description = Column(Text)
    source_system = Column(String)
    uri = Column(String)
    reviewer = Column(String)
    review_cycle_days = Column(Integer, default=365)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class AssessmentRecord(Base):
    __tablename__ = "assessments"
    id = Column(String, primary_key=True, index=True)
    system_name = Column(String)
    control_id = Column(String, index=True)
    status = Column(String)  # implemented/partial/planned/not_implemented/na
    confidence = Column(Float, default=0.0)  # 0.0 - 1.0 ZT confidence score
    notes = Column(Text)
    evidence_ids = Column(JSON, default=list)
    assessor = Column(String)
    assessment_date = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    next_review = Column(DateTime)
    poam_required = Column(String, default="false")

    # Optimization: Composite index for "latest per control" queries
    __table_args__ = (
        Index("idx_control_date", "control_id", "assessment_date"),
    )


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True, index=True)
    agent_type = Column(String)  # orchestrator/icam/data/infra/devsecops/governance/ops
    trigger = Column(String)  # code_push/incident/schedule/manual
    scope = Column(String)
    controls_evaluated = Column(JSON, default=list)
    findings = Column(JSON, default=dict)
    status = Column(String, default="running")  # running/completed/failed
    mistral_model = Column(String)  # mistral model used for this run
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime)


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed controls if empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ControlRecord))
        if not result.scalars().first():
            schema_path = os.getenv("OSCAL_CATALOG_PATH", "./schema/cmmc_oscal_catalog.json")
            if os.path.exists(schema_path):
                with open(schema_path) as f:
                    data = json.load(f)
                    controls = data.get("controls", [])
                    for c in controls:
                        db_ctrl = ControlRecord(
                            id=c["id"],
                            domain=c["domain"],
                            level=c["level"],
                            title=c["title"],
                            description=c["description"],
                            nist_mapping=c.get("nist_mapping"),
                            score_value=c.get("weight", 1)
                        )
                        session.add(db_ctrl)
                await session.commit()


async def get_db():
    """Dependency: yield an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_latest_assessments(db: AsyncSession, control_ids: Optional[List[str]] = None) -> Dict[str, AssessmentRecord]:
    """
    Performance-optimized helper to fetch the most recent assessment for each control.
    Bolt ⚡: Uses the idx_control_date index and optional ID filtering to minimize DB load.
    """
    if control_ids is not None and not control_ids:
        return {}

    # Subquery for latest assessment date per control_id
    sub_q = (
        select(
            AssessmentRecord.control_id,
            func.max(AssessmentRecord.assessment_date).label("max_date")
        )
    )
    if control_ids:
        sub_q = sub_q.where(AssessmentRecord.control_id.in_(control_ids))

    sub_q = sub_q.group_by(AssessmentRecord.control_id).subquery()

    # Join with the original table to get full records
    query = (
        select(AssessmentRecord)
        .join(
            sub_q,
            (AssessmentRecord.control_id == sub_q.c.control_id) &
            (AssessmentRecord.assessment_date == sub_q.c.max_date)
        )
    )

    result = await db.execute(query)
    # Convert to dict for fast ID-based lookup in callers
    return {a.control_id: a for a in result.scalars().all()}
