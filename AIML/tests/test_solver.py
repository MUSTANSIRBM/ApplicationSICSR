"""
Solver tests: bundling = max not sum, safety escalation with reasons,
pinning, explicit fixed-conflict handling, greedy fallback, purity,
and an end-to-end solve against the seeded DB.
"""
import inspect
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

import core.solver as solver_mod
from core.solver import OccupiedIn, TaskIn, solve

MON = datetime(2024, 6, 3)
TUE = datetime(2024, 6, 4)


def _task(id, dur, due_h, tier=2, score=3.0, corridor=1, dept=1, safety=False):
    return TaskIn(id=id, corridor_id=corridor, department_id=dept,
                  duration_min=dur, tier=1 if safety else tier,
                  score=score, due_by=MON + timedelta(hours=due_h),
                  safety_flag=safety)


def _train(h1, h2, corridor=1, ref="EXP"):
    return OccupiedIn(corridor, MON + timedelta(hours=h1),
                      MON + timedelta(hours=h2), "train", f"{ref}-{h1:02d}{h2:02d}")


def test_bundling_duration_is_max_not_sum():
    # Locked decision 2: one combined block, duration = MAX, never the sum.
    tasks = [_task(1, 60, 18, dept=1), _task(2, 90, 18, dept=2)]
    res = solve(MON, TUE, tasks, [_train(10, 12)])
    assert len(res.blocks) == 1
    b = res.blocks[0]
    assert set(b.task_ids) == {1, 2}
    assert b.closure_minutes == 90            # max(60, 90), not 150
    assert b.is_combined
    assert res.deferred == []


def test_safety_escalates_with_reasons():
    # Locked decision 3: a safety task that cannot fit is ESCALATED with
    # machine-readable reasons — never silently dropped.
    trains = [_train(h, h + 1) for h in range(0, 24, 2)]   # 60-min gaps
    safety = _task(9, 240, 12, safety=True, score=4.0)
    res = solve(MON, TUE, [safety], trains)
    assert res.blocks == []
    assert len(res.deferred) == 1
    df = res.deferred[0]
    assert df.escalated is True
    kinds = [r["kind"] for r in df.reasons]
    assert "window_too_small" in kinds
    assert any(k in ("train", "goods") for k in kinds)     # who's in the way


def test_pinned_block_is_immovable():
    # Locked decision 4: APPROVED/LOCKED blocks are fixed intervals.
    pinned = [OccupiedIn(1, MON, MON + timedelta(hours=6),
                         "pinned_block", "block #7")]
    res = solve(MON, TUE, [_task(1, 60, 20)], pinned)
    assert len(res.blocks) == 1
    assert res.blocks[0].start >= MON + timedelta(hours=6)


def test_overlapping_fixed_intervals_raise():
    # Hygiene: an infeasible FIXED set is a named data error before CP-SAT.
    bad = [_train(6, 8), _train(7, 9, ref="CLASH")]
    with pytest.raises(ValueError, match="Fixed-occupancy conflict"):
        solve(MON, TUE, [_task(1, 60, 18)], bad)


def test_greedy_fallback_path():
    tasks = [_task(1, 60, 18, dept=1), _task(2, 90, 18, dept=2)]
    res = solve(MON, TUE, tasks, [_train(10, 12)], force_greedy=True)
    assert res.engine == "GREEDY"
    ids = {tid for b in res.blocks for tid in b.task_ids}
    assert ids == {1, 2}
    for b in res.blocks:                       # respects the train
        assert b.end <= MON + timedelta(hours=10) or \
               b.start >= MON + timedelta(hours=12)


def test_cp_sat_never_overlaps_fixed_traffic():
    trains = [_train(h, h + 2) for h in (6, 10, 14, 18, 22)]
    tasks = [_task(i, d, 20, dept=(i % 3) + 1)
             for i, d in [(1, 60), (2, 90), (3, 120), (4, 30)]]
    res = solve(MON, TUE, tasks, trains)
    assert res.blocks
    for b in res.blocks:
        for tr in trains:
            assert b.end <= tr.start or b.start >= tr.end

def test_core_solver_purity():
    # Parse actual IMPORTS via ast — comments/docstrings can't false-positive.
    import ast
    import inspect
    import core.solver as solver_mod
    
    tree = ast.parse(inspect.getsource(solver_mod))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    banned = {"sqlmodel", "fastapi", "uvicorn", "sklearn", "xgboost"}
    breached = imported & banned
    assert not breached, f"PURITY BREACH: core/solver.py imports {breached}"

def test_run_solve_end_to_end():
    # The full pipeline on real seeded data: seed -> score -> solve ->
    # persist. Blocks never touch trains or goods; deferrals carry
    # reasons; safety is scheduled or escalated, never dropped.
    from planner.db import engine
    from planner.models import (Block, Defect, Deferral, GoodsForecastSlot,
                                Solve, SolveStatus, TaskScore, TaskStatus,
                                TimetableSlot)
    from planner.reference import PLAN_START
    from planner.run_solve import run
    from planner.seed import seed

    seed(reset=True)
    solve_id = run(verbose=False)

    with Session(engine) as s:
        sv = s.get(Solve, solve_id)
        assert sv.status == SolveStatus.COMPLETED
        assert sv.stats["scheduled"] >= 1

        blocks = s.exec(select(Block).where(Block.solve_id == solve_id)).all()
        assert blocks
        for b in blocks:
            assert PLAN_START <= b.start
            assert b.end <= PLAN_START + timedelta(days=7)
            for t in s.exec(select(TimetableSlot).where(
                    TimetableSlot.corridor_id == b.corridor_id)).all():
                assert b.end <= t.start or b.start >= t.end
            for g in s.exec(select(GoodsForecastSlot).where(
                    GoodsForecastSlot.corridor_id == b.corridor_id)).all():
                assert b.end <= g.start or b.start >= g.end

        # explainability persisted: one TaskScore per in-scope defect
        scores = s.exec(select(TaskScore).where(
            TaskScore.solve_id == solve_id)).all()
        assert len(scores) == sv.stats["in_scope"]
        assert all(sc.components for sc in scores)

        # every deferral row carries reasons
        for row in s.exec(select(Deferral).where(
                Deferral.solve_id == solve_id)).all():
            assert row.reasons

        # safety: scheduled or escalated — nothing silent
        for d in s.exec(select(Defect).where(
                Defect.safety_flag == True)).all():    # noqa: E712
            assert d.status in (TaskStatus.SCHEDULED, TaskStatus.ESCALATED)

        # scheduled defects point at their blocks
        for d in s.exec(select(Defect).where(
                Defect.status == TaskStatus.SCHEDULED)).all():
            assert d.block_id is not None
