"""
Schema tests: FK wiring, the tier rule, JSON explainability round-trip.
Fast on purpose — these run before every other layer later.
"""
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from planner.models import (
    Block, BlockStatus, Defect, Deferral, Department, DepartmentCode,
    Solve, SolveEngine, SolveKind, SolveStatus, SourceSystem, TaskScore, Tier,
)

@pytest.fixture(name="engine")
def engine_fixture():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    return eng


def _seed_one_defect(session: Session, safety: bool) -> Defect:
    dept = Department(code=DepartmentCode.ENG, name="Engineering / Track",
                      source_system=SourceSystem.TMS)
    session.add(dept)
    session.commit()
    session.refresh(dept)

    from planner.models import Corridor
    cor = Corridor(code="NGP-BSL", name="Nagpur - Bhusaval", zone="CR",
                   km_start=0.0, km_end=310.5)
    session.add(cor)
    session.commit()
    session.refresh(cor)

    d = Defect(source_ref="TMS-24-0001", source_system="TMS",
               department_id=dept.id, corridor_id=cor.id,
               title="Rail fracture", defect_type="RAIL_FRACTURE",
               severity=5, safety_flag=safety,
               reported_at=datetime(2024, 6, 3, 8, 0),
               due_by=datetime(2024, 6, 5, 18, 0),
               base_duration_min=180)
    session.add(d)
    session.commit()
    session.refresh(d)
    return d

def test_tier_is_derived_not_stored(engine):
    # Decision 1 audit: safety_flag flips the tier, nothing else does.
    with Session(engine) as s:
        d = _seed_one_defect(s, safety=True)
        assert d.tier == Tier.SAFETY
        assert d.safety_flag is True


def test_block_defect_relationship(engine):
    # Bundling anatomy: many defects point at one block, one back-ref.
    with Session(engine) as s:
        d = _seed_one_defect(s, safety=False)
        solve = Solve(kind=SolveKind.WEEKLY, engine=SolveEngine.CP_SAT,
                      horizon_start=datetime(2024, 6, 3),
                      horizon_end=datetime(2024, 6, 10),
                      status=SolveStatus.COMPLETED)
        s.add(solve)
        s.commit()
        s.refresh(solve)

        blk = Block(corridor_id=d.corridor_id,
                    start=datetime(2024, 6, 4, 1, 0),
                    end=datetime(2024, 6, 4, 4, 0),
                    closure_minutes=180, solve_id=solve.id,
                    status=BlockStatus.PROPOSED)
        s.add(blk)
        s.commit()
        s.refresh(blk)

        d.block_id = blk.id
        s.add(d)
        s.commit()
        s.refresh(blk)

        assert blk.defects[0].id == d.id
        assert blk.defects[0].block.id == blk.id


def test_explainability_round_trips(engine):
    # Decisions 7 + 8: score components and deferral reasons survive
    # a SQLite write + read unchanged. Frontend renders, never recomputes.
    with Session(engine) as s:
        d = _seed_one_defect(s, safety=False)
        solve = Solve(kind=SolveKind.WEEKLY, engine=SolveEngine.CP_SAT,
                      horizon_start=datetime(2024, 6, 3),
                      horizon_end=datetime(2024, 6, 10))
        s.add(solve)
        s.commit()
        s.refresh(solve)

        s.add(TaskScore(solve_id=solve.id, defect_id=d.id, tier=Tier.ROUTINE,
                        total=7.4,
                        components={"severity": 4.0, "overdue_days": 2.0,
                                    "traffic_impact": 1.0, "aging_boost": 0.4}))
        s.add(Deferral(solve_id=solve.id, defect_id=d.id, escalated=False,
                       reasons=[{"kind": "train", "ref": "12155 Howrah Mail"},
                                {"kind": "block", "ref": "B-7 (locked, ENG)"}]))
        s.commit()

        score = s.exec(select(TaskScore)).one()
        defer = s.exec(select(Deferral)).one()

        assert score.components["overdue_days"] == 2.0
        assert defer.reasons[0]["ref"] == "12155 Howrah Mail"
        assert defer.reasons[1]["kind"] == "block"


def test_solve_lifecycle_defaults(engine):
    # A solve starts RUNNING and stats is an empty dict, not NULL —
    # the API layer can always read stats without a None-check.
    with Session(engine) as s:
        solve = Solve(kind=SolveKind.BASELINE, engine=SolveEngine.BASELINE_FCFS,
                      horizon_start=datetime(2024, 6, 3),
                      horizon_end=datetime(2024, 6, 10))
        s.add(solve)
        s.commit()
        s.refresh(solve)
        assert solve.status == SolveStatus.RUNNING
        assert solve.stats == {}
