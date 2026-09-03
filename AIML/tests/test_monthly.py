"""
Monthly-plan tests: soft-link semantics (pull, never block), generation
sanity (reservations never overlap trains), and the weekly-solve hookup.
"""
from datetime import datetime, timedelta

from core.solver import OccupiedIn, ReservationIn, TaskIn, solve

MON = datetime(2024, 6, 3)
TUE = datetime(2024, 6, 4)


def _task(id, dur, due_h, safety=False, score=3.0):
    return TaskIn(id=id, corridor_id=1, department_id=1,
                  duration_min=dur, tier=1 if safety else 2,
                  score=score, due_by=MON + timedelta(hours=due_h),
                  safety_flag=safety)


def test_reservation_pulls_a_free_choice():
    # Empty corridor, task due hour 12: lateness alone would place it at
    # 00:00. A 20:00-24:00 reservation is worth more than the lateness
    # penalty, so the block moves INTO the window. Soft pull works.
    res = [ReservationIn(1, MON + timedelta(hours=20), TUE)]
    r = solve(MON, TUE, [_task(1, 120, 12)], [], reservations=res)
    assert len(r.blocks) == 1
    assert r.blocks[0].start >= MON + timedelta(hours=20)
    assert r.blocks[0].end <= TUE


def test_reservation_never_blocks_scheduling():
    # Window too small for the task: the soft constraint yields, the
    # weekly plan still schedules the task. Decision 5: never a wall.
    res = [ReservationIn(1, MON + timedelta(hours=20),
                         MON + timedelta(hours=21))]
    r = solve(MON, TUE, [_task(1, 120, 12)], [], reservations=res)
    assert len(r.blocks) == 1


def test_reservation_loses_to_fixed_traffic():
    # Reservation overlapping a train: solver places around the train
    # (hygiene) and simply forfeits the bonus. No crash, no overlap.
    train = [OccupiedIn(1, MON + timedelta(hours=20),
                        MON + timedelta(hours=23), "train", "EXP-20")]
    res = [ReservationIn(1, MON + timedelta(hours=20), TUE)]
    r = solve(MON, TUE, [_task(1, 120, 12)], train, reservations=res)
    assert len(r.blocks) == 1
    b = r.blocks[0]
    assert b.end <= train[0].start or b.start >= train[0].end


def test_monthly_generation_end_to_end():
    from sqlmodel import Session, select

    from planner.db import engine
    from planner.models import (GoodsForecastSlot, MonthlyReservation, Solve,
                                SolveKind, SolveStatus, TimetableSlot)
    from planner.monthly import run_monthly
    from planner.seed import seed

    seed(reset=True)
    run_monthly(verbose=False)

    with Session(engine) as s:
        rows = s.exec(select(MonthlyReservation)).all()
        assert rows, "monthly plan produced no reservations"

        for r in rows:
            assert r.reserved_minutes >= 30
            # DB-team sanity rule baked into a test: reservations live in
            # train-free space by construction.
            for t in s.exec(select(TimetableSlot).where(
                    TimetableSlot.corridor_id == r.corridor_id)).all():
                assert r.window_end <= t.start or r.window_start >= t.end
            for g in s.exec(select(GoodsForecastSlot).where(
                    GoodsForecastSlot.corridor_id == r.corridor_id)).all():
                assert r.window_end <= g.start or r.window_start >= g.end

        ms = s.exec(select(Solve).where(
            Solve.kind == SolveKind.MONTHLY)).all()
        assert ms and ms[-1].status == SolveStatus.COMPLETED
        assert ms[-1].stats["reservations"] == len(rows)


def test_weekly_solve_consumes_reservations():
    from sqlmodel import Session

    from planner.db import engine
    from planner.models import Solve, SolveStatus
    from planner.monthly import run_monthly
    from planner.reference import PLAN_START
    from planner.run_solve import run
    from planner.seed import seed

    seed(reset=True)
    run_monthly(verbose=False)
    sid = run(week_start=PLAN_START + timedelta(days=7), verbose=False)

    with Session(engine) as s:
        sv = s.get(Solve, sid)
        assert sv.status == SolveStatus.COMPLETED
        # the soft-link plumbing exists and reports
        assert "res_aligned" in sv.stats
        assert "reservations_in_week" in sv.stats
        assert sv.stats["reservations_in_week"] > 0
