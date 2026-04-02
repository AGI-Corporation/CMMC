"""
Database initialization and session management.
AGI Corporation CMMC Platform 2026
"""

import json
import os
from datetime import UTC, datetime

from sqlalchemy import (JSON, Column, DateTime, Float, Index, Integer, String,
                        Text, func, select)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cmmc.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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
    status = Column(
        String, default="not_implemented"
    )  # implemented/partial/planned/not_implemented
    score_value = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


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
    assessment_date = Column(DateTime, default=lambda: datetime.now(UTC))
    next_review = Column(DateTime)
    poam_required = Column(String, default="false")

    __table_args__ = (Index("idx_control_date", "control_id", "assessment_date"),)


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


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)  # ISSO, ISSM, System Owner, Control Owner, Assessor, etc.
    department = Column(String)
    phone = Column(String)
    active = Column(Integer, default=1)  # 1=active, 0=inactive
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class ControlAssignment(Base):
    __tablename__ = "control_assignments"
    id = Column(String, primary_key=True, index=True)
    member_id = Column(String, index=True, nullable=False)  # FK → team_members.id
    control_id = Column(String, index=True, nullable=False)  # FK → controls.id
    role = Column(String, default="owner")  # owner / reviewer / approver
    due_date = Column(DateTime)
    completion_date = Column(DateTime)
    priority = Column(String, default="medium")  # critical / high / medium / low
    status = Column(String, default="open")  # open / in_progress / completed / overdue
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("idx_assignment_member", "member_id"),
        Index("idx_assignment_control", "control_id"),
    )


class BlockchainTransaction(Base):
    """Tamper-evident audit ledger for CMMC assessment events."""

    __tablename__ = "blockchain_transactions"
    id = Column(String, primary_key=True, index=True)
    sequence = Column(Integer, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(Text, nullable=False)        # JSON string
    payload_hash = Column(String, nullable=False)  # SHA-256 of payload
    previous_hash = Column(String, nullable=False)  # SHA-256 of prior TX
    signature = Column(String, nullable=False)    # HMAC-SHA256
    actor = Column(String, default="system")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed controls if empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ControlRecord))
        if not result.scalars().first():
            schema_path = os.getenv(
                "OSCAL_CATALOG_PATH", "./schema/cmmc_oscal_catalog.json"
            )
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
                            score_value=c.get("weight", 1),
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


async def get_latest_assessments(db: AsyncSession, control_ids: list[str] = None):
    """
    Shared helper to fetch the latest AssessmentRecord for each control.
    Optionally filtered by a list of control_ids for better performance.
    """
    sub_q = select(
        AssessmentRecord.control_id,
        func.max(AssessmentRecord.assessment_date).label("max_date"),
    ).group_by(AssessmentRecord.control_id)

    if control_ids:
        sub_q = sub_q.where(AssessmentRecord.control_id.in_(control_ids))

    sub_q = sub_q.subquery()

    query = select(AssessmentRecord).join(
        sub_q,
        (AssessmentRecord.control_id == sub_q.c.control_id)
        & (AssessmentRecord.assessment_date == sub_q.c.max_date),
    )

    result = await db.execute(query)
    return {a.control_id: a for a in result.scalars().all()}
