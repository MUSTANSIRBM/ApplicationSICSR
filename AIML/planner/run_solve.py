"""
planner/run_solve.py — CLI: python -m planner.run_solve

Reads the seeded DB, scores in-scope defects (core), runs the CP-SAT
weekly solver (core) with monthly reservations as SOFT windows,
persists Solve + Blocks + TaskScores + Deferrals, prints the plan.
"""
from datetime import timedelta

from sqlmodel import Session, select

from core.scoring import score_all
from core.solver import OccupiedIn, ReservationIn, TaskIn, solve
from planner.db import engine
from planner.models import (
    Block, BlockStatus, Corridor, Defect, Deferral, GoodsForecastSlot,
    MonthlyReservation, Solve, SolveEngine, SolveKind, SolveStatus,
    TaskScore, TaskStatus, Tier, TimetableSlot,
)
from planner.reference import PLAN_START
from planner.score_demo import corridor_pressure

WEEK = timedelta(days=7)


def run(week_start=PLAN_START, verbose=True):
    week_end = week_start + WEEK

    # ---------- read + score ----------
    with Session(engine) as s:
        defects = s.exec(select(Defect).where(
            Defect.status.in_((TaskStatus.NEW, TaskStatus.DEFERRED)))).all()
        pressure = corridor_pressure(s)
        prior = {}
        for row in s.exec(select(Deferral)).all():
            prior[row.defect_id] = prior.get(row.defect_id, 0) + 1
        scored = score_all(defects, now=week_start,
                           corridor_pressure=pressure, prior_deferrals=prior)
        by_id = {r.defect_id: r for r in scored}
        dmap = {d.id: d for d in defects}

        in_scope = [d for d in defects
                    if d.safety_flag or d.due_by <= week_end + timedelta(days=1)]
        tasks = [TaskIn(id=d.id, corridor_id=d.corridor_id,
                        department_id=d.department_id,
                        duration_min=d.base_duration_min,
                        tier=1 if d.safety_flag else 2,
                        score=by_id[d.id].total, due_by=d.due_by,
                        safety_flag=d.safety_flag)
                 for d in in_scope]

        occupied = []
        for t in s.exec(select(TimetableSlot)).all():
            occupied.append(OccupiedIn(t.corridor_id, t.start, t.end,
                                       "train", f"{t.train_no} {t.train_name}"))
        for g in s.exec(select(GoodsForecastSlot)).all():
            occupied.append(OccupiedIn(g.corridor_id, g.start, g.end,
                                       "goods", g.label))
        for b in s.exec(select(Block).where(Block.status.in_(
                (BlockStatus.APPROVED, BlockStatus.LOCKED)))).all():
            occupied.append(OccupiedIn(b.corridor_id, b.start, b.end,
                                       "pinned_block", f"block #{b.id}"))

        reservations = [ReservationIn(r.corridor_id, r.window_start, r.window_end)
                        for r in s.exec(select(MonthlyReservation)).all()
                        if r.window_end > week_start and r.window_start < week_end]

        codes = {c.id: c.code for c in s.exec(select(Corridor)).all()}

    result = solve(week_start, week_end, tasks, occupied,
                   reservations=reservations)

    # ---------- persist ----------
    with Session(engine) as s:
        scheduled_ids = {tid for b in result.blocks for tid in b.task_ids}
        bundled = [b for b in result.blocks if len(b.task_ids) > 1]
        closure_saved = sum(
            dmap[tid].base_duration_min for b in bundled for tid in b.task_ids
        ) - sum(b.closure_minutes for b in bundled)

        res_aligned = sum(
            1 for b in result.blocks
            if any(r.corridor_id == b.corridor_id and b.start >= r.start
                   and b.end <= r.end for r in reservations))

        solve_row = Solve(
            kind=SolveKind.WEEKLY,
            engine=(SolveEngine.CP_SAT if result.engine == "CP_SAT"
                    else SolveEngine.GREEDY),
            horizon_start=week_start, horizon_end=week_end,
            status=SolveStatus.COMPLETED,
            objective=result.objective,
            wall_time_ms=result.wall_time_ms,
            stats={
                "in_scope": len(in_scope),
                "scheduled": len(scheduled_ids),
                "deferred": len(result.deferred),
                "escalated": sum(1 for d in result.deferred if d.escalated),
                "blocks": len(result.blocks),
                "bundled_blocks": len(bundled),
                "closure_saved_min": closure_saved,
                "reservations_in_week": len(reservations),
                "res_aligned": res_aligned,
            },
        )
        s.add(solve_row); s.commit(); s.refresh(solve_row)

        for b in result.blocks:
            depts = {dmap[tid].department_id for tid in b.task_ids}
            blk = Block(corridor_id=b.corridor_id, start=b.start, end=b.end,
                        closure_minutes=b.closure_minutes,
                        is_combined=len(depts) > 1, solve_id=solve_row.id,
                        status=BlockStatus.PROPOSED)
            s.add(blk); s.commit(); s.refresh(blk)
            for tid in b.task_ids:
                d = s.get(Defect, tid)
                d.block_id = blk.id
                d.status = TaskStatus.SCHEDULED
                s.add(d)

        for d in in_scope:
            r = by_id[d.id]
            s.add(TaskScore(solve_id=solve_row.id, defect_id=d.id,
                            tier=Tier.SAFETY if d.safety_flag else Tier.ROUTINE,
                            total=r.total, components=r.components))

        for df in result.deferred:
            d = s.get(Defect, df.task_id)
            d.status = (TaskStatus.ESCALATED if df.escalated
                        else TaskStatus.DEFERRED)
            s.add(Deferral(solve_id=solve_row.id, defect_id=df.task_id,
                           escalated=df.escalated, reasons=df.reasons))
        s.commit()

        solve_id = solve_row.id          # read BEFORE the session closes
        if verbose:
            _print(solve_row, result, dmap, codes)
    return solve_id


def _print(solve_row, result, dmap, codes):
    st = solve_row.stats
    print("=" * 68)
    print(f"WEEKLY SOLVE #{solve_row.id} — engine {result.engine}, "
          f"status {result.status}, {result.wall_time_ms} ms")
    if result.objective is not None:
        print(f"objective: {result.objective}")
    print(f"in scope {st['in_scope']} | scheduled {st['scheduled']} | "
          f"deferred {st['deferred']} | escalated {st['escalated']}")
    print(f"blocks {st['blocks']} | bundled {st['bundled_blocks']} | "
          f"closure minutes saved by bundling: {st['closure_saved_min']}")
    print(f"monthly alignment: {st['res_aligned']}/"
          f"{st['blocks']} blocks inside reservation windows "
          f"({st['reservations_in_week']} windows this week)")
    print("-" * 68)
    for b in result.blocks:
        refs = ", ".join(dmap[tid].source_ref for tid in b.task_ids)
        tag = "COMBINED" if len(b.task_ids) > 1 else "single  "
        print(f"  {codes[b.corridor_id]:7} {b.start:%a %d %H:%M}-{b.end:%H:%M} "
              f"({b.closure_minutes:3} min) [{tag}] {refs}")
    print("-" * 68)
    if result.deferred:
        print("DEFERRED / ESCALATED (with reasons):")
        for df in result.deferred:
            d = dmap[df.task_id]
            tag = "ESCALATED (safety)" if df.escalated else "deferred     "
            print(f"  {d.source_ref:14} {tag} | {d.defect_type:22} "
                  f"| needs {d.base_duration_min} min")
            for r in df.reasons:
                print(f"      - {r}")
    print("-" * 68)
    print(f"out of this week's scope (due later, stays NEW): "
          f"{len(dmap) - st['in_scope']}")
    print("=" * 68)


if __name__ == "__main__":
    run()
