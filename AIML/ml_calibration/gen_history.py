"""
ml_calibration/gen_history.py — python -m ml_calibration.gen_history

Manufactures training history: seeds, plans the month, solves all 4
weeks, injects safety defects mid-stream (forcing re-solves), and
injects one deliberately-oversized routine defect (guaranteeing a
deferral — training needs BOTH outcome classes). Deterministic.

*** FLAG: overlaps DB-team work order item C. If they've shipped their
own history generator, use theirs and delete this. ***
"""
from datetime import timedelta

from sqlmodel import Session, select

from planner.db import engine
from planner.models import (
    Block, BlockStatus, Corridor, Defect, Department, DepartmentCode,
    SourceSystem, TaskStatus,
)
from planner.monthly import run_monthly
from planner.reference import PLAN_START
from planner.run_solve import run
from planner.seed import seed


def _inject(session, corridor_code, dept_code, dtype, safety, dur, week_start):
    cor = session.exec(select(Corridor).where(
        Corridor.code == corridor_code)).one()
    dept = session.exec(select(Department).where(
        Department.code == DepartmentCode(dept_code))).one()
    n = len(session.exec(select(Defect).where(
        Defect.source_ref.startswith("INJ-"))).all())
    d = Defect(
        source_ref=f"INJ-{n + 1:04d}",
        source_system=SourceSystem(dept.source_system.value),
        department_id=dept.id, corridor_id=cor.id,
        title=dtype.replace("_", " ").title(), defect_type=dtype,
        severity=5 if safety else 3, safety_flag=safety,
        reported_at=week_start, due_by=week_start + timedelta(hours=36),
        base_duration_min=dur, status=TaskStatus.NEW)
    session.add(d)
    session.commit()
    session.refresh(d)
    return d.id


def generate(verbose=True) -> int:
    seed(reset=True)
    run_monthly(verbose=False)

    solve_ids = []
    for w in range(4):
        ws = PLAN_START + timedelta(weeks=w)

        if w == 1:
            with Session(engine) as s:
                # safety injection -> forces a re-solve cycle in history
                _inject(s, "ET-NGP", "TRD", "OHE_DROP", True, 120, ws)
                # pin the first proposed block: pinning in the history
                blk = s.exec(select(Block).where(
                    Block.status == BlockStatus.PROPOSED)).first()
                if blk:
                    blk.status = BlockStatus.APPROVED
                    s.add(blk)
                s.commit()
        if w == 2:
            with Session(engine) as s:
                # oversized routine defect on the HEAVY corridor:
                # guaranteed DEFERRAL with reasons -> outcome class 0
                _inject(s, "NGP-BSL", "ENG", "TRACK_GEOMETRY",
                        False, 600, ws)
        if w == 3:
            with Session(engine) as s:
                _inject(s, "MAS-TRY", "SNT", "POINT_MACHINE_DEFECT",
                        True, 90, ws)

        solve_ids.append(run(week_start=ws, verbose=False))

    if verbose:
        print(f"history generated: {len(solve_ids)} weekly solves "
              f"(ids {solve_ids})")
    return len(solve_ids)


if __name__ == "__main__":
    generate()

