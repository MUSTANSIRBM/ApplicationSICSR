"""
Step 7 tests: the minimal-diff anchors — soft pull, yields when blocked,
wired into run_solve's same-week re-plan, and demo_state builds a
demo-ready DB.
"""
from datetime import datetime, timedelta

from sqlmodel import Session, select

from core.solver import AnchorIn, OccupiedIn, TaskIn, solve

MON = datetime(2024, 6, 3)
TUE = datetime(2024, 6, 4)


def _task(id, dur, due_h, safety=False, score=3.0):
    return TaskIn(id=id, corridor_id=1, department_id=1,
                  duration_min=dur, tier=1 if safety else 2,
                  score=score, due_by=MON + timedelta(hours=due_h),
                  safety_flag=safety)


def _train(h1, h2, ref="EXP"):
    return OccupiedIn(1, MON + timedelta(hours=h1),
                      MON + timedelta(hours=h2), "train", f"{ref}-{h1:02d}{h2:02d}")


def test_anchor_holds_position_against_earlier_slot():
    # Without an anchor the solver goes earliest (lateness). With an
    # anchor at 20:00 the stability cost beats lateness -> block STAYS.
    task = _task(1, 120, 23)
    anchor = AnchorIn(1, MON + timedelta(hours=20),
                      MON + timedelta(hours=22), (1,))
    r = solve(MON, TUE, [task], [_train(6, 8)], anchors=[anchor])
    assert len(r.blocks) == 1
    assert r.blocks[0].start == MON + timedelta(hours=20), \
        "anchored position must win over the earlier free slot"


def test_anchor_yields_when_fixed_traffic_takes_the_spot():
    # A new train now covers the anchored window: the block moves, the
    # solve still succeeds. Soft means soft — never infeasible.
    task = _task(1, 120, 23)
    anchor = AnchorIn(1, MON + timedelta(hours=20),
                      MON + timedelta(hours=22), (1,))
    trains = [_train(6, 8), _train(18, 22)]
    r = solve(MON, TUE, [task], trains, anchors=[anchor])
    assert len(r.blocks) == 1
    b = r.blocks[0]
    for tr in trains:
        assert b.end <= tr.start or b.start >= tr.end


def test_replan_same_week_keeps_anchors():
    # Full pipeline: solve week 1, inject a safety defect, re-solve the
    # SAME week. Stats must show anchors captured and mostly kept.
    from planner.db import engine
    from planner.models import Corridor, Defect, Department, DepartmentCode, Solve
    from planner.reference import PLAN_START
    from planner.run_solve import run
    from planner.seed import seed

    seed(reset=True)
    run(week_start=PLAN_START, verbose=False)

    with Session(engine) as s:
        et = s.exec(select(Corridor).where(
            Corridor.code == "ET-NGP")).one()
        dept = s.exec(select(Department).where(
            Department.code == DepartmentCode.TRD)).one()
        n = len(s.exec(select(Defect).where(
            Defect.source_ref.startswith("INJ-"))).all())
        s.add(Defect(
            source_ref=f"INJ-{n + 1:04d}",
            source_system=dept.source_system,
            department_id=dept.id, corridor_id=et.id,
            title="Ohe Drop (test)", defect_type="OHE_DROP",
            severity=5, safety_flag=True,
            reported_at=PLAN_START,
            due_by=PLAN_START + timedelta(hours=36),
            base_duration_min=120))
        s.commit()

    sid = run(week_start=PLAN_START, verbose=False)
    with Session(engine) as s:
        sv = s.get(Solve, sid)
        assert sv.stats["anchors"] >= 2, \
            "re-plan must have captured the previous week's proposals"
        assert sv.stats["anchor_kept"] >= 1, \
            "at least one unpinned block must have held its position"

        # the re-plan must have placed the injected safety defect
        inj = s.exec(select(Defect).where(
            Defect.source_ref.startswith("INJ-"))).first()
        assert inj.status.value == "SCHEDULED"


def test_demo_state_builds():
    from planner.db import engine
    from planner.demo_state import build
    from planner.models import Block, BlockStatus, Solve, SolveKind

    last_id = build(verbose=False)
    with Session(engine) as s:
        weekly = s.exec(select(Solve).where(
            Solve.kind == SolveKind.WEEKLY)).all()
        assert len(weekly) == 4
        last = s.get(Solve, last_id)
        assert last.stats["in_scope"] >= 5, \
            "week 4 must be meaty enough for the impact dashboard"
        approved = s.exec(select(Block).where(
            Block.status == BlockStatus.APPROVED)).all()
        assert approved, "demo state must contain a pinned block"

