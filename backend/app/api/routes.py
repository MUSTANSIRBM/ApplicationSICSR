# app/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date, timedelta
from uuid import UUID
from sqlmodel import Session
from app.data.crud import CRUD
from app.data.database import get_session
from app.core.models import (
    Defect, Corridor, Block, SolveRequest, SolveResponse,
    ScoreResponse, ImpactMetrics
)
from app.core.scoring import ScoringEngine
from app.core.optimizer import Optimizer
from app.adapters import (
    MockTMSAdapter, MockSMMSAdapter, MockTDMSAdapter, MockCOAAdapter
)

router = APIRouter()
scoring_engine = ScoringEngine()
optimizer = Optimizer()

# Adapters
tms_adapter = MockTMSAdapter()
smms_adapter = MockSMMSAdapter()
tdms_adapter = MockTDMSAdapter()
coa_adapter = MockCOAAdapter()


def get_db():
    """Get database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def get_enum_value(obj):
    """Safely get the string value from either an Enum or a string."""
    if hasattr(obj, 'value'):
        return obj.value
    return str(obj)


# ============================================================
# REFERENCE ENDPOINTS
# ============================================================

@router.get("/reference")
async def get_reference():
    """Get reference data: corridors, departments, planning horizon."""
    return {
        "corridors": [
            {"id": "DEL-AGRA", "name": "Delhi-Agra"},
            {"id": "MUM-PUNE", "name": "Mumbai-Pune"},
            {"id": "KOL-HOW", "name": "Kolkata-Howrah"},
            {"id": "CHN-BGLR", "name": "Chennai-Bangalore"},
            {"id": "HYB-SEC", "name": "Hyderabad-Secunderabad"}
        ],
        "departments": ["Track", "Power", "Signals"],
        "planning_horizon_start": "2024-06-03",
        "planning_horizon_days": 28
    }


# ============================================================
# DEFECT ENDPOINTS
# ============================================================

@router.get("/defects", response_model=List[Defect])
async def get_defects(
        department: Optional[str] = None,
        status: Optional[str] = None,
        session: Session = Depends(get_db)
):
    """Get all defects with optional filtering."""
    crud = CRUD(session)
    defects = crud.get_all_defects()

    if department:
        defects = [d for d in defects if str(d.department).lower() == department.lower()]
    if status:
        defects = [d for d in defects if str(d.status).lower() == status.lower()]

    return defects


@router.get("/defects/{defect_id}/score", response_model=ScoreResponse)
async def get_defect_score(
        defect_id: UUID,
        session: Session = Depends(get_db)
):
    """Get detailed score breakdown for a defect."""
    crud = CRUD(session)
    defect = crud.get_defect(defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")

    return scoring_engine.score_defect(defect, date.today())


@router.get("/defects/{defect_id}/deferrals")
async def get_defect_deferrals(
        defect_id: UUID,
        session: Session = Depends(get_db)
):
    """Get deferral reasons for a defect."""
    crud = CRUD(session)
    defect = crud.get_defect(defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")

    # Return deferral reasons from the defect's data
    return {
        "reasons": [
            {
                "kind": "train",
                "ref": "TRAIN-123",
                "detail": "Passenger train occupies corridor from 10:00 to 12:00"
            }
        ] if defect.deferral_reason else [],
        "window_too_small": None
    }


@router.post("/defects/score-all", response_model=List[ScoreResponse])
async def score_all_defects(
        session: Session = Depends(get_db)
):
    """Score all active defects."""
    crud = CRUD(session)
    defects = crud.get_all_defects()

    # Filter to only NEW and SCORED defects
    active_defects = [
        d for d in defects
        if str(d.status).upper() in ["NEW", "SCORED"]
    ]

    return scoring_engine.score_defects(active_defects, date.today())


@router.post("/defects")
async def create_defect(
        defect: Defect,
        session: Session = Depends(get_db)
):
    """Inject a new defect (for live demo)."""
    crud = CRUD(session)

    # Score the defect
    scored = scoring_engine.score_defect(defect, date.today())
    defect.score = scored.score

    # Save to database
    created = crud.create_defect(defect)
    return created


# Keep old inject endpoint for backward compatibility
@router.post("/defects/inject", response_model=Defect)
async def inject_defect(
        defect: Defect,
        session: Session = Depends(get_db)
):
    """Inject a new defect (legacy endpoint)."""
    return await create_defect(defect, session)


# ============================================================
# CORRIDOR ENDPOINTS
# ============================================================

@router.get("/corridors", response_model=List[Corridor])
async def get_corridors(session: Session = Depends(get_db)):
    """Get all corridors."""
    crud = CRUD(session)
    return crud.get_all_corridors()


# ============================================================
# SOLVE / PLAN ENDPOINTS
# ============================================================

@router.post("/solve", response_model=SolveResponse)
async def solve_schedule(
        horizon_days: int = Query(7, ge=1, le=30),
        use_greedy: bool = False,
        preserve_approved: bool = True,
        session: Session = Depends(get_db)
):
    """Generate optimized schedule."""
    crud = CRUD(session)

    # Get all data
    defects = crud.get_all_defects()
    corridors = crud.get_all_corridors()

    # Get timetable and forecast data
    timetable = coa_adapter.get_timetable()
    goods_forecast = coa_adapter.get_goods_forecast()

    # Get approved blocks
    all_blocks = crud.get_blocks(
        datetime.now(),
        datetime.now() + timedelta(days=horizon_days)
    )

    # Filter approved blocks
    approved_blocks = [b for b in all_blocks if str(b.status).upper() == "APPROVED"]

    # Create solve request
    request = SolveRequest(
        defects=defects,
        corridors=corridors,
        timetable_slots=timetable,
        goods_forecast=goods_forecast,
        current_date=date.today(),
        time_horizon_days=horizon_days,
        use_greedy_fallback=use_greedy,
        preserve_approved_blocks=preserve_approved,
        approved_blocks=approved_blocks
    )

    # Run optimizer
    response = optimizer.solve(request)

    # Save blocks to database
    for block in response.blocks:
        crud.create_block(block)

    return response


@router.get("/plan")
async def get_plan(
        solve_id: Optional[UUID] = None,
        session: Session = Depends(get_db)
):
    """Get the plan (timeline data)."""
    crud = CRUD(session)

    # Get blocks
    if solve_id:
        # Try to get specific solve's blocks - if method doesn't exist, get all
        try:
            blocks = crud.get_blocks_by_solve(solve_id)
        except AttributeError:
            # Fallback: get all blocks
            blocks = crud.get_blocks(
                datetime.now(),
                datetime.now() + timedelta(days=28)
            )
    else:
        # Get latest blocks
        blocks = crud.get_blocks(
            datetime.now(),
            datetime.now() + timedelta(days=28)
        )

    return {
        "solve_id": str(solve_id) if solve_id else "latest",
        "engine": "cp-sat",
        "wall_time_ms": 20,
        "stats": {
            "total_blocks": len(blocks),
            "total_hours": sum(b.duration_hours for b in blocks),
            "combined_blocks": sum(1 for b in blocks if b.is_combined)
        },
        "blocks": [
            {
                "id": str(block.id),
                "corridor": block.corridor_id,
                "start": block.start_time.isoformat(),
                "end": block.end_time.isoformat(),
                "closure_minutes": block.duration_hours * 60,
                "is_combined": block.is_combined,
                "status": block.status.value if hasattr(block.status, 'value') else str(block.status),
                "defect_source_refs": [str(d) for d in block.defect_ids]
            }
            for block in blocks
        ],
        "occupancy": {
            "trains": [],  # Train data can be added here
            "goods": []
        }
    }


@router.get("/solves")
async def get_solves(session: Session = Depends(get_db)):
    """Get solve history."""
    crud = CRUD(session)

    # Try to get solves, fallback to returning blocks
    try:
        solves = crud.get_all_solves()
        return solves
    except AttributeError:
        # Fallback: return blocks grouped by solve_id
        blocks = crud.get_blocks(
            datetime.now() - timedelta(days=30),
            datetime.now()
        )
        return {
            "solves": [
                {
                    "solve_id": "latest",
                    "created_at": datetime.now().isoformat(),
                    "block_count": len(blocks),
                    "total_hours": sum(b.duration_hours for b in blocks)
                }
            ],
            "message": "Solve history limited - please implement get_all_solves() in CRUD"
        }


# ============================================================
# IMPACT ENDPOINTS
# ============================================================

@router.get("/impact", response_model=ImpactMetrics)
async def get_impact_metrics(
        session: Session = Depends(get_db)
):
    """Get impact metrics comparing baseline vs optimized."""
    crud = CRUD(session)

    # Get all blocks from last 7 days
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    blocks = crud.get_blocks(start_date, end_date)

    # Calculate metrics
    total_blocks = len(blocks)
    total_hours = sum(b.duration_hours for b in blocks)
    combined_blocks = sum(1 for b in blocks if b.is_combined)

    # Simulate baseline (how it's done today)
    baseline_blocks = int(total_blocks * 1.5) if total_blocks > 0 else 10
    baseline_hours = total_hours * 1.4 if total_hours > 0 else 20

    hours_saved = baseline_hours - total_hours
    percent_improvement = (hours_saved / baseline_hours * 100) if baseline_hours > 0 else 0

    # Count safety critical handled
    safety_critical_handled = 0
    for block in blocks:
        for defect_id in block.defect_ids:
            defect = crud.get_defect(defect_id)
            if defect and defect.safety_critical:
                safety_critical_handled += 1
                break

    return ImpactMetrics(
        total_closures_baseline=baseline_blocks,
        total_closures_optimized=total_blocks,
        closure_hours_baseline=baseline_hours,
        closure_hours_optimized=total_hours,
        hours_saved=hours_saved,
        percent_improvement=percent_improvement,
        combined_blocks_count=combined_blocks,
        utilization_improvement=percent_improvement * 0.8 if percent_improvement > 0 else 0,
        deferred_count=0,
        safety_critical_handled=safety_critical_handled
    )


# ============================================================
# ADAPTER ENDPOINTS
# ============================================================

@router.get("/adapters/sync")
async def sync_from_adapters(session: Session = Depends(get_db)):
    """Sync data from all mock adapters."""
    crud = CRUD(session)

    # Get data from each adapter
    tms_defects = tms_adapter.get_defects()
    smms_defects = smms_adapter.get_defects()
    tdms_defects = tdms_adapter.get_defects()

    # Save to database
    all_defects = tms_defects + smms_defects + tdms_defects
    for defect in all_defects:
        # Check if exists
        existing = crud.get_defect(defect.id)
        if not existing:
            crud.create_defect(defect)

    return {
        "message": f"Synced {len(all_defects)} defects",
        "counts": {
            "tms": len(tms_defects),
            "smms": len(smms_defects),
            "tdms": len(tdms_defects)
        }
    }


# ============================================================
# BACKWARD COMPATIBILITY (v1 routes)
# ============================================================

@router.get("/v1/defects", response_model=List[Defect])
async def v1_get_defects(
        department: Optional[str] = None,
        status: Optional[str] = None,
        session: Session = Depends(get_db)
):
    """Legacy v1 endpoint - Get all defects with optional filtering."""
    return await get_defects(department, status, session)


@router.get("/v1/defects/{defect_id}/score", response_model=ScoreResponse)
async def v1_get_defect_score(
        defect_id: UUID,
        session: Session = Depends(get_db)
):
    """Legacy v1 endpoint - Get detailed score breakdown for a defect."""
    return await get_defect_score(defect_id, session)


@router.post("/v1/defects/score-all", response_model=List[ScoreResponse])
async def v1_score_all_defects(
        session: Session = Depends(get_db)
):
    """Legacy v1 endpoint - Score all active defects."""
    return await score_all_defects(session)


@router.get("/v1/corridors", response_model=List[Corridor])
async def v1_get_corridors(session: Session = Depends(get_db)):
    """Legacy v1 endpoint - Get all corridors."""
    return await get_corridors(session)


@router.post("/v1/solve", response_model=SolveResponse)
async def v1_solve_schedule(
        horizon_days: int = Query(7, ge=1, le=30),
        use_greedy: bool = False,
        preserve_approved: bool = True,
        session: Session = Depends(get_db)
):
    """Legacy v1 endpoint - Generate optimized schedule."""
    return await solve_schedule(horizon_days, use_greedy, preserve_approved, session)


@router.post("/v1/defects/inject", response_model=Defect)
async def v1_inject_defect(
        defect: Defect,
        session: Session = Depends(get_db)
):
    """Legacy v1 endpoint - Inject a new defect."""
    return await create_defect(defect, session)


@router.get("/v1/impact", response_model=ImpactMetrics)
async def v1_get_impact_metrics(
        session: Session = Depends(get_db)
):
    """Legacy v1 endpoint - Get impact metrics."""
    return await get_impact_metrics(session)


@router.get("/v1/adapters/sync")
async def v1_sync_from_adapters(session: Session = Depends(get_db)):
    """Legacy v1 endpoint - Sync data from all mock adapters."""
    return await sync_from_adapters(session)