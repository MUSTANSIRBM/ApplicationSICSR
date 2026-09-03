from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, date, timedelta
from uuid import UUID
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
from sqlmodel import Session

router = APIRouter()
scoring_engine = ScoringEngine()
optimizer = Optimizer()

# Adapters
tms_adapter = MockTMSAdapter()
smms_adapter = MockSMMSAdapter()
tdms_adapter = MockTDMSAdapter()
coa_adapter = MockCOAAdapter()


@router.get("/defects", response_model=List[Defect])
async def get_defects(
    department: Optional[str] = None,
    status: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Get all defects with optional filtering."""
    crud = CRUD(session)
    defects = crud.get_all_defects()
    
    if department:
        defects = [d for d in defects if d.department.value == department]
    if status:
        defects = [d for d in defects if d.status.value == status]
    
    return defects


@router.get("/defects/{defect_id}/score", response_model=ScoreResponse)
async def get_defect_score(
    defect_id: UUID,
    session: Session = Depends(get_session)
):
    """Get detailed score breakdown for a defect."""
    crud = CRUD(session)
    defect = crud.get_defect(defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    
    return scoring_engine.score_defect(defect, date.today())


@router.post("/defects/score-all", response_model=List[ScoreResponse])
async def score_all_defects(
    session: Session = Depends(get_session)
):
    """Score all active defects."""
    crud = CRUD(session)
    defects = crud.get_all_defects()
    
    # Filter to only NEW and SCORED defects
    active_defects = [
        d for d in defects 
        if d.status.value in ["NEW", "SCORED"]
    ]
    
    return scoring_engine.score_defects(active_defects, date.today())


@router.get("/corridors", response_model=List[Corridor])
async def get_corridors(session: Session = Depends(get_session)):
    """Get all corridors."""
    crud = CRUD(session)
    return crud.get_all_corridors()


@router.post("/solve", response_model=SolveResponse)
async def solve_schedule(
    horizon_days: int = Query(7, ge=1, le=30),
    use_greedy: bool = False,
    preserve_approved: bool = True,
    session: Session = Depends(get_session)
):
    """Generate optimized schedule."""
    crud = CRUD(session)
    
    # Get all data
    defects = crud.get_all_defects()
    corridors = crud.get_all_corridors()
    
    # Get timetable and forecast data
    # For now, use mock adapters
    timetable = coa_adapter.get_timetable()
    goods_forecast = coa_adapter.get_goods_forecast()
    approved_blocks = crud.get_blocks(
        datetime.now(),
        datetime.now() + timedelta(days=horizon_days)
    )
    
    # Filter approved blocks
    approved_blocks = [b for b in approved_blocks if b.status.value == "APPROVED"]
    
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


@router.post("/defects/inject", response_model=Defect)
async def inject_defect(
    defect: Defect,
    session: Session = Depends(get_session)
):
    """Inject a new defect (for live demo)."""
    crud = CRUD(session)
    
    # Score the defect
    scored = scoring_engine.score_defect(defect, date.today())
    defect.score = scored.score
    
    # Save to database
    created = crud.create_defect(defect)
    return created


@router.get("/impact", response_model=ImpactMetrics)
async def get_impact_metrics(
    session: Session = Depends(get_session)
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
    # Assumption: 1.5x more closures and time wasted
    baseline_blocks = int(total_blocks * 1.5)
    baseline_hours = total_hours * 1.4
    
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
        utilization_improvement=percent_improvement * 0.8,  # Approximate
        deferred_count=0,  # Would need to track this
        safety_critical_handled=safety_critical_handled
    )


@router.get("/adapters/sync")
async def sync_from_adapters(session: Session = Depends(get_session)):
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