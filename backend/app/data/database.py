# app/data/database.py
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional, Generator
from datetime import datetime
from uuid import UUID, uuid4
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DATABASE_URL, echo=True)


class DefectDB(SQLModel, table=True):
    __tablename__ = "defects"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    defect_id: str = Field(index=True)
    description: str
    department: str
    severity: int
    overdue_days: int
    traffic_impact: int
    safety_critical: bool = False
    corridor_id: str = Field(index=True)
    system_source: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "NEW"
    score: float = None
    scheduled_time: datetime = None
    scheduled_end: datetime = None
    block_id: UUID = None
    deferral_reason: str = None


class CorridorDB(SQLModel, table=True):
    __tablename__ = "corridors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    corridor_id: str = Field(index=True, unique=True)
    name: str
    capacity: int = 1
    available_from: datetime
    available_to: datetime


class TimetableSlotDB(SQLModel, table=True):
    __tablename__ = "timetable_slots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    corridor_id: str = Field(index=True)
    train_id: str = Field(index=True)
    start_time: datetime
    end_time: datetime
    is_goods: bool = False
    priority: int = 1


class GoodsForecastDB(SQLModel, table=True):
    __tablename__ = "goods_forecast"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    corridor_id: str = Field(index=True)
    train_id: str = Field(index=True)
    start_time: datetime
    end_time: datetime
    forecast_type: str = "scheduled"


class BlockDB(SQLModel, table=True):
    __tablename__ = "blocks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    corridor_id: str = Field(index=True)
    start_time: datetime
    end_time: datetime
    department: str
    defect_ids: str  # Comma-separated UUIDs
    is_combined: bool = False
    combined_departments: str  # Comma-separated department names
    status: str = "PROPOSED"
    locked_at: datetime = None
    executed_at: datetime = None


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a database session."""
    return Session(engine)


def get_db() -> Generator[Session, None, None]:
    """Get a database session as a context manager."""
    with Session(engine) as session:
        yield session