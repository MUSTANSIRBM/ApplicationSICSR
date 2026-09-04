"""
api/incident.py -- POST /api/incident: the SECONDS-to-WEEKS bridge.

Step 5 of 7. One endpoint, one lifecycle beat:

  sensor incident in -> DecisionEngine (R1 wall -> model -> R2 leash)
  -> full decision JSON out
  -> and, when create_repair_defect=true, the repair becomes a Defect
     in the planner DB (LOCKED: ALWAYS created when the flag is true --
     the flag is a human decision, the endpoint obeys it, no severity
     gate).

This is api/ glue: FastAPI + pydantic + SQLModel live HERE and nowhere
near ml_sensor (purity wall, test-enforced at step 6).

Contract discipline:
  - Swagger (/docs) is the truth for what this exposes.
  - The defect write mirrors api/routes.py inject_defect line-for-line
    (corridor/department resolution, reported_at = latest weekly
    horizon start, 24h due window, NEW status) so both entry points
    write the SAME shape of Defect. Two write paths with different
    shapes = two truths in one DB.
  - Incident-created defects use source_ref "INC-####" so they are
    distinguishable from injected "INJ-####" in the timeline UI.
  - v2: department enum members are RESOLVED from the real enum at
    import time (normalized match on name/value), never hardcoded
    from memory. A miss fails loud with the actual members printed.
  - v3: sqlmodel's select, not sqlalchemy's -- Session.exec only
    unwraps entities from statements it recognizes (truth:
    DepartmentCode members are ENG / TRD / SNT).

Bridge defaults (owner-tunable at review, each flagged):
  DEFECT severity  = ceil(incident_severity / 2), clamped 1..5
  safety_flag      = incident_severity >= 8        <-- MY INFERENCE,
                     deserves explicit owner sign-off
  duration         = BASE_HOURS[type] * SEV_MULT[defect_severity],
                     min 15 min, rounded to 5 min
  due window       = 24h (same as inject default)
"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlmodel import Session, select    # sqlmodel's select, NOT
                                        # sqlalchemy's: Session.exec
                                        # only unwraps entities from
                                        # statements it recognizes --
                                        # the sqlalchemy one hands
                                        # back raw Rows (v3 bugfix)

from api.routes import PLAN_START, _latest_weekly
from ml_sensor.decide import DecisionEngine
from ml_sensor.scenarios import OBSTRUCTION_TYPES
from planner.db import get_session
from planner.models import (Corridor, Defect, Department,
                            DepartmentCode, TaskStatus)

router = APIRouter(prefix="/api", tags=["incident"])

# =====================================================================
# Department code resolution -- read truth, never guess (v2)
# =====================================================================

def _norm(s: str) -> str:
    return s.replace("_", "").replace("-", "").replace("&", "").upper()


def _resolve_dept_code(*candidates: str) -> DepartmentCode:
    """Find the DepartmentCode member matching any candidate, by
    normalized name OR value. Fails LOUD (listing the real members)
    rather than guessing. Truth (owner paste): ENG / TRD / SNT."""
    table: dict[str, DepartmentCode] = {}
    for m in DepartmentCode:
        table[_norm(m.name)] = m
        table[_norm(str(m.value))] = m
    for cand in candidates:
        m = table.get(_norm(cand))
        if m is not None:
            return m
    for cand in candidates:          # substring second chance
        k = _norm(cand)
        for key, m in table.items():
            if k and k in key:
                return m
    members = [f"{m.name}={m.value}" for m in DepartmentCode]
    raise RuntimeError(
        f"could not resolve a DepartmentCode member from candidates "
        f"{candidates}; actual members: {members} -- paste this error "
        f"and the mapping gets pinned to the exact member")

# Resolved ONCE at import. Loud failure at boot beats silent failure
# at request time; the step-6 tests lock these to ENG/TRD/SNT.
DEPT_ENGINEERING = _resolve_dept_code("ENGINEERING", "ENG")
DEPT_TRD = _resolve_dept_code("TRD")
DEPT_S_AND_T = _resolve_dept_code("SNT", "S_AND_T", "S_T", "S&T",
                                  "SIGNALS", "SIGNAL", "ST")

TYPE_TO_DEPARTMENT: dict[str, DepartmentCode] = {
    "signal_cable_theft": DEPT_S_AND_T,
    "equipment_failure_ahead": DEPT_TRD,
}
_DEFAULT_DEPT = DEPT_ENGINEERING


# =====================================================================
# The engine singleton + self-heal
# =====================================================================

_engine: DecisionEngine | None = None


def get_engine() -> DecisionEngine:
    global _engine
    if _engine is None:
        try:
            _engine = DecisionEngine()
        except FileNotFoundError:
            print("[incident] no decision model on disk -- training "
                  "in-process (seed 42)...")
            from ml_sensor.train import train
            train()
            _engine = DecisionEngine()
    return _engine


# =====================================================================
# Request schema -- strict boundary
# =====================================================================

WeatherIn = Literal["clear", "rain", "fog", "heavy_rain",
                    "snow", "flood", "dry"]     # dry -> clear (locked)
AheadIn = Literal["OCCUPIED", "CLEAR", "occupied", "clear"]
SensorIn = Literal["track_circuit", "axle_counter",
                   "vibration", "accelerometer"]


class IncidentIn(BaseModel):
    """The 14 raw fields the frontend sends (decision 12: computed
    values like braking distance are NEVER accepted as inputs -- they
    don't exist in this schema at all, which is the wall)."""
    train_speed_kmh: float = Field(ge=45, le=200)
    distance_to_obstacle_km: float = Field(ge=0, le=20)
    environmental_condition: WeatherIn
    weather_alert: bool = False
    signal_quality_percent: float = Field(ge=0, le=100)
    severity_score: int = Field(ge=1, le=10)
    obstruction_type: str
    alternative_route_available: bool = False
    communication_latency_ms: float = Field(ge=10, le=5000)
    axle_balance: Optional[float] = Field(default=None, ge=0.3, le=1.7)
    ahead_section_status: AheadIn = "CLEAR"
    known_train_schedule: bool = False
    distance_from_station_km: float = Field(ge=0, le=25)
    sensor_type: SensorIn

    # control flags (not features)
    create_repair_defect: bool = False
    corridor: Optional[str] = None

    @field_validator("environmental_condition")
    @classmethod
    def _norm_weather(cls, v: str) -> str:
        if v == "dry":            # locked: dry -> clear at the boundary
            return "clear"
        return v

    @field_validator("ahead_section_status")
    @classmethod
    def _norm_ahead(cls, v: str) -> str:
        return v.upper()

    @field_validator("obstruction_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in OBSTRUCTION_TYPES:
            raise ValueError(
                f"unknown obstruction_type: {v!r} -- must be one of "
                f"{sorted(OBSTRUCTION_TYPES)}")
        return v

    @model_validator(mode="after")
    def _bridge_needs_corridor(self) -> "IncidentIn":
        if self.create_repair_defect and not self.corridor:
            raise ValueError(
                "corridor is required when create_repair_defect=true")
        return self


# =====================================================================
# Bridge mapping: incident -> planner defect (Flag 6 defaults)
# =====================================================================

BASE_HOURS: dict[str, float] = {
    "landslide_debris": 8.0, "boulder": 6.0, "track_buckling": 8.0,
    "fallen_tree": 3.0, "stranded_vehicle": 5.0, "water_logging": 6.0,
    "cattle_crossing": 2.0, "broken_rail": 8.0, "signal_cable_theft": 4.0,
    "sensor_miscount": 2.0, "environmental_false_positive": 2.0,
    "unknown_obstruction": 5.0, "equipment_failure_ahead": 5.0,
}

SEV_MULT: dict[int, float] = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.25, 5: 1.5}

SAFETY_SEVERITY_THRESHOLD = 8     # <-- my inference; owner sign-off due
DUE_IN_HOURS = 24                 # same as inject default


def _defect_severity(incident_severity: int) -> int:
    return max(1, min(5, (incident_severity + 1) // 2))


def _duration_min(obstruction_type: str, defect_severity: int) -> int:
    hours = BASE_HOURS[obstruction_type] * SEV_MULT[defect_severity]
    minutes = int(round(hours * 60 / 5.0) * 5)
    return max(15, minutes)


# =====================================================================
# The endpoint
# =====================================================================

class RepairDefectOut(BaseModel):
    defect_id: int
    source_ref: str
    corridor: str
    department: str
    title: str
    defect_type: str
    severity: int
    safety_flag: bool
    base_duration_min: int
    due_by: str
    note: str


class IncidentOut(BaseModel):
    action: str
    confidence: Optional[float]
    source: str
    reasons: list[str]
    physics: dict
    probabilities: Optional[dict]
    decision_latency_ms: float
    within_100ms_budget: bool
    repair_defect: Optional[RepairDefectOut] = None


def _create_repair_defect(inc: IncidentIn, decision: dict,
                          session: Session) -> Defect:
    """Mirror of inject_defect's write path (same resolution, same
    clock, same defaults) so incident defects and injected defects are
    indistinguishable to the solver, scoring, and timeline. The REAL
    decision is baked into the description at construction --
    explainability is a data structure (locked decision 8)."""
    cor = session.exec(select(Corridor).where(
        Corridor.code == inc.corridor)).first()
    if not cor:
        raise HTTPException(404, f"unknown corridor: {inc.corridor}")

    dept_code = TYPE_TO_DEPARTMENT.get(inc.obstruction_type, _DEFAULT_DEPT)
    dept = session.exec(select(Department).where(
        Department.code == dept_code)).first()
    if not dept:
        raise HTTPException(500, f"department {dept_code} missing from "
                                 f"reference data -- re-run planner.seed")

    latest = _latest_weekly(session)
    now = latest.horizon_start if latest else PLAN_START

    sev = _defect_severity(inc.severity_score)
    duration = _duration_min(inc.obstruction_type, sev)
    n = len(session.exec(select(Defect).where(
        Defect.source_ref.startswith("INC-"))).all())

    return Defect(
        source_ref=f"INC-{n + 1:04d}",
        source_system=dept.source_system,
        department_id=dept.id, corridor_id=cor.id,
        title=inc.obstruction_type.replace("_", " ").title(),
        description=(f"Repair from sensor incident: "
                     f"{inc.obstruction_type} (severity "
                     f"{inc.severity_score}/10). Engine decided "
                     f"'{decision['action']}' (source="
                     f"{decision['source']}, confidence="
                     f"{decision['confidence']}). Weather: "
                     f"{inc.environmental_condition}."),
        defect_type=inc.obstruction_type.upper(),
        severity=sev,
        safety_flag=inc.severity_score >= SAFETY_SEVERITY_THRESHOLD,
        reported_at=now, due_by=now + timedelta(hours=DUE_IN_HOURS),
        base_duration_min=duration, status=TaskStatus.NEW,
    )


@router.post("/incident", response_model=IncidentOut)
def post_incident(inc: IncidentIn,
                  session: Session = Depends(get_session)):
    """The Detect -> Decide -> Repair lifecycle in one call.

    1. Decide (seconds): the engine answers under the R1/R2 leash.
    2. Bridge (flagged): if create_repair_defect=true, the repair
       becomes a planner Defect -- ALWAYS (locked owner decision).
       The defect creation is NOT influenced by the decision's action.
    """
    engine = get_engine()

    # --- 1) decide ---
    try:
        decision = engine.decide(inc.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # --- 2) bridge (only if flagged) ---
    repair: Optional[RepairDefectOut] = None
    if inc.create_repair_defect:
        d = _create_repair_defect(inc, decision, session)
        session.add(d)
        session.commit()
        session.refresh(d)
        dept_code = TYPE_TO_DEPARTMENT.get(inc.obstruction_type,
                                           _DEFAULT_DEPT)
        repair = RepairDefectOut(
            defect_id=d.id, source_ref=d.source_ref,
            corridor=str(inc.corridor),
            department=str(getattr(dept_code, "value", dept_code)),
            title=d.title, defect_type=d.defect_type,
            severity=d.severity, safety_flag=d.safety_flag,
            base_duration_min=d.base_duration_min,
            due_by=d.due_by.isoformat(),
            note=("ALWAYS created when flag=true (locked). Incident "
                  f"severity {inc.severity_score}/10 -> defect severity "
                  f"{d.severity}/5"
                  + (" (SAFETY TIER)" if d.safety_flag else "")
                  + f", repair est. {d.base_duration_min} min."),
        )

    return IncidentOut(
        action=decision["action"],
        confidence=decision["confidence"],
        source=decision["source"],
        reasons=decision["reasons"],
        physics=decision["physics"],
        probabilities=decision["probabilities"],
        decision_latency_ms=decision["decision_latency_ms"],
        within_100ms_budget=decision["within_100ms_budget"],
        repair_defect=repair,
    )
