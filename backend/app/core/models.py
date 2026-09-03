from enum import Enum
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4


class Department(str, Enum):
    TRACK = "Track"
    POWER = "Power"
    SIGNALS = "Signals"


class DefectStatus(str, Enum):
    NEW = "NEW"
    SCORED = "SCORED"
    SCHEDULED = "SCHEDULED"
    DEFERRED = "DEFERRED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"


class BlockStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"
    EXECUTED = "EXECUTED"


class SafetyTier(str, Enum):
    SAFETY_CRITICAL = "safety_critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Defect(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    defect_id: str  # Original system ID
    description: str
    department: Department
    severity: int = Field(ge=1, le=5)
    overdue_days: int = Field(ge=0)
    traffic_impact: int = Field(ge=1, le=5)
    safety_critical: bool = False
    corridor_id: str
    system_source: str  # TMS, SMMS, TDMS
    created_at: datetime = Field(default_factory=datetime.now)
    status: DefectStatus = DefectStatus.NEW
    score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    scheduled_time: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    block_id: Optional[UUID] = None
    deferral_reason: Optional[str] = None

    class Config:
        use_enum_values = True


class Corridor(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    corridor_id: str
    name: str
    capacity: int = 1  # Number of simultaneous blocks possible
    available_from: datetime
    available_to: datetime


class TimetableSlot(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    corridor_id: str
    train_id: str
    start_time: datetime
    end_time: datetime
    is_goods: bool = False
    priority: int = 1  # 1 = passenger, 2 = goods


class GoodsForecast(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    corridor_id: str
    train_id: str
    start_time: datetime
    end_time: datetime
    forecast_type: str  # "scheduled", "estimated", "confirmed"


class Block(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    corridor_id: str
    start_time: datetime
    end_time: datetime
    department: Department
    defect_ids: List[UUID] = []
    is_combined: bool = False
    combined_departments: List[Department] = []
    status: BlockStatus = BlockStatus.PROPOSED
    locked_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    
    @property
    def duration_hours(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 3600


class SolveRequest(BaseModel):
    defects: List[Defect]
    corridors: List[Corridor]
    timetable_slots: List[TimetableSlot]
    goods_forecast: List[GoodsForecast]
    current_date: date
    time_horizon_days: int = 7
    use_greedy_fallback: bool = False
    preserve_approved_blocks: bool = True
    approved_blocks: List[Block] = []


class SolveResponse(BaseModel):
    blocks: List[Block]
    deferred_defects: List[Dict[str, Any]]  # Defect + reason
    solver_used: str  # "cp-sat" or "greedy"
    solve_time_ms: float
    stats: Dict[str, Any]  # Utilization, savings, etc.
    changes_from_previous: Optional[List[Dict[str, Any]]] = None


class ScoreResponse(BaseModel):
    defect_id: UUID
    score: float
    tier: SafetyTier
    breakdown: Dict[str, float]
    explanation: str


class ImpactMetrics(BaseModel):
    total_closures_baseline: int
    total_closures_optimized: int
    closure_hours_baseline: float
    closure_hours_optimized: float
    hours_saved: float
    percent_improvement: float
    combined_blocks_count: int
    utilization_improvement: float  # percentage
    deferred_count: int
    safety_critical_handled: int