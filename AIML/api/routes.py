"""
api/routes.py — every endpoint. Field names are the FROZEN contract.

Step 7 changes: inject no longer resets proposals itself (run_solve
resets same-week proposals and uses them as anchors — minimal diff).
diff entries carry a human-readable reason for the frontend tooltip.
"""
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from core.solver import free_gaps
from planner.db import get_session
from planner.models import (
    Block, BlockStatus, Corridor, Defect, Deferral, Department,
    DepartmentCode, GoodsForecastSlot, MonthlyReservation, Solve,
    SolveKind, TaskScore, TaskStatus, TimetableSlot,
)
from planner.reference import PLAN_END, PLAN_START
from planner.run_solve import run as run_weekly_solve

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------- helpers

def _iso(dt):
    return dt.isoformat() if dt else None


def _latest_weekly(session: Session) -> Optional[Solve]:
    return session.exec(
        select(Solve).where(Solve.kind == SolveKind.WEEKLY)
        .order_by(Solve.id.desc())).first()


def _maps(session: Session):
    corridors = {c.id: c.code for c in session.exec(select(Corridor)).all()}
    departments = {d.id: d.code.value
                   for d in session.exec(select(Department)).all()}
    return corridors, departments


def _defect_out(d: Defect, corridors: dict, departments: dict) -> dict:
    return {
        "id": d.id, "source_ref": d.source_ref,
        "source_system": d.source_system.value,
        "department": departments[d.department_id],
        "corridor": corridors[d.corridor_id],
        "title": d.title, "defect_type": d.defect_type,
        "severity": d.severity, "safety_flag": d.safety_flag,
        "tier": 1 if d.safety_flag else 2,
        "status": d.status.value,
        "due_by": _iso(d.due_by), "reported_at": _iso(d.reported_at),
        "base_duration_min": d.base_duration_min,
        "block_id": d.block_id,
    }


def _capture_active(session: Session) -> list:
    corridors, _ = _maps(session)
    out = []
    stmt = select(Block).where(Block.status.in_(
        (BlockStatus.PROPOSED, BlockStatus.APPROVED, BlockStatus.LOCKED)))
    for b in session.exec(stmt).all():
        ds = session.exec(select(Defect).where(
            Defect.block_id == b.id)).all()
        out.append({
            "block_id": b.id, "corridor": corridors[b.corridor_id],
            "start": _iso(b.start), "end": _iso(b.end),
            "closure_minutes": b.closure_minutes,
            "is_combined": b.is_combined, "status": b.status.value,
            "task_ids": sorted(d.id for d in ds),
            "source_refs": [d.source_ref for d in ds],
        })
    return out


def _diff_blocks(before: list, after: list) -> dict:
    """Match by (corridor, task set). Moved blocks carry a reason —
    who displaced them, or an honest 'not pinned' note."""
    key = lambda b: (b["corridor"], tuple(b["task_ids"]))
    bmap = {key(b): b for b in before}
    amap = {key(b): b for b in after}
    unchanged, moved, new, gone = [], [], [], []
    for k, b in amap.items():
        if k in bmap:
            if b["start"] == bmap[k]["start"]:
                unchanged.append(b)
            else:
                prev = bmap[k]
                displacers = [n for n in amap.values()
                              if n is not b
                              and n["corridor"] == b["corridor"]
                              and n["start"] < prev["end"]
                              and prev["start"] < n["end"]]
                if displacers:
                    reason = "displaced by " + ", ".join(
                        r for n in displacers for r in n["source_refs"])
                else:
                    reason = "re-plan shifted position (block not pinned)"
                moved.append({**b, "reason": reason})
        else:
            new.append(b)
    for k, b in bmap.items():
        if k not in amap:
            gone.append({**b, "reason":
                         "tasks re-grouped into a bundle or deferred"})
    return {"unchanged": unchanged, "moved": moved,
            "new": new, "gone": gone}


# ---------------------------------------------------------------- reference

@router.get("/reference")
def reference(session: Session = Depends(get_session)):
    cor_rows = session.exec(select(Corridor)).all()
    dep_rows = session.exec(select(Department)).all()
    return {
        "plan_start": _iso(PLAN_START), "plan_end": _iso(PLAN_END),
        "corridors": [{"id": c.id, "code": c.code, "name": c.name,
                       "zone": c.zone, "km_start": c.km_start,
                       "km_end": c.km_end, "lines": c.lines,
                       "notes": c.notes} for c in cor_rows],
        "departments": [{"id": d.id, "code": d.code.value, "name": d.name,
                         "source_system": d.source_system.value}
                        for d in dep_rows],
    }


# ---------------------------------------------------------------- defects

@router.get("/defects")
def list_defects(status: Optional[str] = None, corridor: Optional[str] = None,
                 department: Optional[str] = None,
                 session: Session = Depends(get_session)):
    corridors, departments = _maps(session)
    stmt = select(Defect)
    if status:
        try:
            stmt = stmt.where(Defect.status == TaskStatus(status))
        except ValueError:
            raise HTTPException(400, f"unknown status: {status}")
    out = [_defect_out(d, corridors, departments)
           for d in session.exec(stmt).all()]
    if corridor:
        out = [o for o in out if o["corridor"] == corridor]
    if department:
        out = [o for o in out if o["department"] == department]
    return out


@router.get("/defects/{defect_id}")
def get_defect(defect_id: int, session: Session = Depends(get_session)):
    d = session.get(Defect, defect_id)
    if not d:
        raise HTTPException(404, "defect not found")
    corridors, departments = _maps(session)
    return _defect_out(d, corridors, departments)


@router.get("/defects/{defect_id}/score")
def get_score(defect_id: int, session: Session = Depends(get_session)):
    if not session.get(Defect, defect_id):
        raise HTTPException(404, "defect not found")
    ts = session.exec(select(TaskScore).where(
        TaskScore.defect_id == defect_id)
        .order_by(TaskScore.solve_id.desc())).first()
    if not ts:
        raise HTTPException(404, "no score yet — run a solve first")
    return {"defect_id": defect_id, "solve_id": ts.solve_id,
            "tier": ts.tier.value, "total": ts.total,
            "components": ts.components}


@router.get("/defects/{defect_id}/deferrals")
def get_deferrals(defect_id: int, session: Session = Depends(get_session)):
    if not session.get(Defect, defect_id):
        raise HTTPException(404, "defect not found")
    rows = session.exec(select(Deferral).where(
        Deferral.defect_id == defect_id)
        .order_by(Deferral.solve_id.desc())).all()
    return [{"solve_id": r.solve_id, "escalated": r.escalated,
             "reasons": r.reasons, "created_at": _iso(r.created_at)}
            for r in rows]


# ---------------------------------------------------------------- plan / solves

@router.get("/plan")
def get_plan(solve_id: Optional[int] = None,
             session: Session = Depends(get_session)):
    if solve_id:
        sv = session.get(Solve, solve_id)
        if not sv:
            raise HTTPException(404, "solve not found")
    else:
        sv = _latest_weekly(session)
        if not sv:
            raise HTTPException(404, "no solve yet — POST /api/solve first")

    corridors, _ = _maps(session)
    blocks = session.exec(select(Block).where(
        Block.solve_id == sv.id)).all()
    block_json = []
    for b in blocks:
        refs = [d.source_ref for d in session.exec(
            select(Defect).where(Defect.block_id == b.id)).all()]
        block_json.append({
            "id": b.id, "corridor": corridors[b.corridor_id],
            "corridor_id": b.corridor_id,
            "start": _iso(b.start), "end": _iso(b.end),
            "closure_minutes": b.closure_minutes,
            "is_combined": b.is_combined, "status": b.status.value,
            "source_refs": refs})

    occupancy = []
    for t in session.exec(select(TimetableSlot).where(
            TimetableSlot.start < sv.horizon_end,
            TimetableSlot.end > sv.horizon_start)).all():
        occupancy.append({"corridor": corridors[t.corridor_id],
                          "kind": "train", "start": _iso(t.start),
                          "end": _iso(t.end),
                          "label": f"{t.train_no} {t.train_name}",
                          "priority": t.priority})
    for g in session.exec(select(GoodsForecastSlot).where(
            GoodsForecastSlot.start < sv.horizon_end,
            GoodsForecastSlot.end > sv.horizon_start)).all():
        occupancy.append({"corridor": corridors[g.corridor_id],
                          "kind": "goods", "start": _iso(g.start),
                          "end": _iso(g.end), "label": g.label,
                          "priority": 3})

    reservations = [
        {"corridor": corridors[r.corridor_id],
         "start": _iso(r.window_start), "end": _iso(r.window_end),
         "reserved_minutes": r.reserved_minutes}
        for r in session.exec(select(MonthlyReservation).where(
            MonthlyReservation.window_end > sv.horizon_start,
            MonthlyReservation.window_start < sv.horizon_end)).all()]

    return {"solve_id": sv.id, "kind": sv.kind.value,
            "engine": sv.engine.value, "wall_time_ms": sv.wall_time_ms,
            "stats": sv.stats,
            "horizon_start": _iso(sv.horizon_start),
            "horizon_end": _iso(sv.horizon_end),
            "blocks": block_json, "occupancy": occupancy,
            "reservations": reservations}


@router.get("/solves")
def list_solves(session: Session = Depends(get_session)):
    return [{"id": s.id, "kind": s.kind.value, "engine": s.engine.value,
             "status": s.status.value,
             "horizon_start": _iso(s.horizon_start),
             "horizon_end": _iso(s.horizon_end),
             "wall_time_ms": s.wall_time_ms, "objective": s.objective,
             "stats": s.stats}
            for s in session.exec(select(Solve)
                                   .order_by(Solve.id.desc())).all()]


# ---------------------------------------------------------------- solve

class SolveRequest(BaseModel):
    week_start: Optional[date] = None


@router.post("/solve")
def post_solve(req: SolveRequest, session: Session = Depends(get_session)):
    ws = (datetime.combine(req.week_start, time())
          if req.week_start else PLAN_START)
    if not (PLAN_START <= ws < PLAN_END):
        raise HTTPException(400, "week_start outside the plan window")
    solve_id = run_weekly_solve(week_start=ws, verbose=False)
    sv = session.get(Solve, solve_id)
    return {"solve_id": solve_id, "stats": sv.stats,
            "horizon_start": _iso(sv.horizon_start),
            "horizon_end": _iso(sv.horizon_end)}


# ---------------------------------------------------------------- inject (money moment)

class InjectDefectRequest(BaseModel):
    corridor: str
    department: str
    defect_type: str
    safety_flag: bool = False
    severity: Optional[int] = Field(default=None, ge=1, le=5)
    base_duration_min: int = Field(default=120, ge=15)
    title: Optional[str] = None
    due_in_hours: int = 24


@router.post("/defects")
def inject_defect(req: InjectDefectRequest,
                  session: Session = Depends(get_session)):
    cor = session.exec(select(Corridor).where(
        Corridor.code == req.corridor)).first()
    if not cor:
        raise HTTPException(404, f"unknown corridor: {req.corridor}")
    try:
        dept_code = DepartmentCode(req.department)
    except ValueError:
        raise HTTPException(404, f"unknown department: {req.department}")
    dept = session.exec(select(Department).where(
        Department.code == dept_code)).first()

    latest = _latest_weekly(session)
    now = latest.horizon_start if latest else PLAN_START
    severity = req.severity if req.severity is not None \
        else (5 if req.safety_flag else 3)
    n = len(session.exec(select(Defect).where(
        Defect.source_ref.startswith("INJ-"))).all())

    d = Defect(
        source_ref=f"INJ-{n + 1:04d}", source_system=dept.source_system,
        department_id=dept.id, corridor_id=cor.id,
        title=req.title or req.defect_type.replace("_", " ").title(),
        defect_type=req.defect_type, severity=severity,
        safety_flag=req.safety_flag, reported_at=now,
        due_by=now + timedelta(hours=req.due_in_hours),
        base_duration_min=req.base_duration_min,
        status=TaskStatus.NEW)
    session.add(d)
    session.commit()
    session.refresh(d)

    # Locked behavior: non-safety defects QUEUE for the next re-plan.
    if not req.safety_flag:
        return {"defect_id": d.id, "replanned": False,
                "message": "non-safety defect queued for next re-plan"}

    # ---- safety: immediate re-solve with diff ----
    # run_solve resets this week's proposals and uses them as ANCHORS
    # (minimal diff). Other weeks' plans survive. APPROVED/LOCKED pinned.
    before = _capture_active(session)
    session.close()

    solve_id = run_weekly_solve(week_start=now, verbose=False)

    with Session(engine_from_dep()) as s2:
        after = _capture_active(s2)
        diff = _diff_blocks(before, after)
        sv = s2.get(Solve, solve_id)

    return {"defect_id": d.id, "solve_id": solve_id, "replanned": True,
            "stats": sv.stats, "diff": diff}


def engine_from_dep():
    from planner.db import engine
    return engine


# ---------------------------------------------------------------- impact

def _baseline(session: Session, week_start, week_end, defects) -> dict:
    """Today's way (decision 6): per-department FCFS, blind to others."""
    horizon = int((week_end - week_start).total_seconds() // 60)

    def to_min(t):
        return int((t - week_start).total_seconds() // 60)

    fixed = {}
    for model in (TimetableSlot, GoodsForecastSlot):
        for row in session.exec(select(model)).all():
            s, e = max(row.start, week_start), min(row.end, week_end)
            if s < e:
                fixed.setdefault(row.corridor_id, []).append(
                    (to_min(s), to_min(e), "traffic", "ref"))

    by_dept = {}
    for d in defects:
        by_dept.setdefault(d.department_id, []).append(d)

    placed, deferred = [], 0
    for dept_id, group in by_dept.items():
        occ = {cid: list(items) for cid, items in fixed.items()}
        for d in sorted(group, key=lambda x: x.reported_at):   # FCFS
            done = False
            for gs, ge in free_gaps(sorted(occ.get(d.corridor_id, [])),
                                    horizon):
                if ge - gs >= d.base_duration_min:
                    occ.setdefault(d.corridor_id, []).append(
                        (gs, gs + d.base_duration_min, "block", d.source_ref))
                    placed.append((d.corridor_id, gs, d.base_duration_min,
                                   dept_id))
                    done = True
                    break
            if not done:
                deferred += 1

    conflicts = 0
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            if (a[0] == b[0] and a[3] != b[3]
                    and a[1] < b[1] + b[2] and b[1] < a[1] + a[2]):
                conflicts += 1

    return {"in_scope": len(defects), "scheduled": len(placed),
            "deferred": deferred, "escalated": 0, "bundled_blocks": 0,
            "closure_minutes": sum(p[2] for p in placed),
            "closure_saved_min": 0,
            "cross_dept_conflicts": conflicts,
            "method": "per-department FCFS, no bundling (today's way)"}


@router.get("/impact")
def get_impact(session: Session = Depends(get_session)):
    sv = _latest_weekly(session)
    if not sv:
        raise HTTPException(404, "no weekly solve yet — POST /api/solve first")
    week_start, week_end = sv.horizon_start, sv.horizon_end

    defects = session.exec(select(Defect)).all()
    in_scope = [d for d in defects
                if d.safety_flag or d.due_by <= week_end + timedelta(days=1)]

    baseline = _baseline(session, week_start, week_end, in_scope)
    blocks = session.exec(select(Block).where(
        Block.solve_id == sv.id)).all()
    planner = {
        "in_scope": sv.stats.get("in_scope", 0),
        "scheduled": sv.stats.get("scheduled", 0),
        "deferred": sv.stats.get("deferred", 0),
        "escalated": sv.stats.get("escalated", 0),
        "bundled_blocks": sv.stats.get("bundled_blocks", 0),
        "closure_minutes": sum(b.closure_minutes for b in blocks),
        "closure_saved_min": sv.stats.get("closure_saved_min", 0),
        "cross_dept_conflicts": 0,      # no-overlap by construction
        "method": "CP-SAT + cross-department bundling (ours)",
    }
    return {"solve_id": sv.id, "week_start": _iso(week_start),
            "baseline": baseline, "planner": planner}

