"""
planner/monthly.py — CLI: python -m planner.monthly

The MONTHLY plan (locked decision 5): rough corridor reservations for
each week of the 4-week window, sized from upcoming defect demand,
placed inside the largest train-free gap of each corridor-week.

These are SOFT: the weekly solver earns a bonus for aligning with them
but is never blocked by them. Coarse on purpose — durations rounded to
30 min, one window per corridor-week, no department-level detail.

Re-run safe: wipes existing reservations before writing.
"""
from collections import defaultdict
from datetime import timedelta

from sqlmodel import Session, select

from planner.db import engine
from planner.models import (
    Corridor, Defect, Department, GoodsForecastSlot, MonthlyReservation,
    Solve, SolveEngine, SolveKind, SolveStatus, TaskStatus, TimetableSlot,
)
from planner.reference import PLAN_DAYS, PLAN_START

WEEK = timedelta(days=7)
_ROUND = 30          # monthly plans speak in half-hours, not minutes


def _week_free_gaps(session, corridor_id, week_start, week_end):
    """Train/goods-free gaps for one corridor-week, as datetimes."""
    items = []
    for model in (TimetableSlot, GoodsForecastSlot):
        for row in session.exec(select(model).where(
                model.corridor_id == corridor_id)).all():
            s, e = max(row.start, week_start), min(row.end, week_end)
            if s < e:
                items.append((s, e))
    items.sort()
    gaps, cursor = [], week_start
    for s, e in items:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < week_end:
        gaps.append((cursor, week_end))
    return gaps


def run_monthly(verbose=True):
    with Session(engine) as s:
        # fresh reservations each run — the monthly plan is regenerable
        for old in s.exec(select(MonthlyReservation)).all():
            s.delete(old)
        s.commit()

        corridors = s.exec(select(Corridor)).all()
        departments = {d.id: d.code.value
                       for d in s.exec(select(Department)).all()}
        defects = s.exec(select(Defect).where(
            Defect.status.in_((TaskStatus.NEW, TaskStatus.DEFERRED,
                               TaskStatus.ESCALATED)))).all()

        rows, total_min = [], 0
        for w in range(PLAN_DAYS // 7):
            wk_start = PLAN_START + timedelta(weeks=w)
            wk_end = wk_start + WEEK

            # demand per corridor this week: minutes by department,
            # safety counts double (it WILL get corridor time).
            demand = defaultdict(lambda: defaultdict(int))
            for d in defects:
                if wk_start <= d.due_by < wk_end:
                    weight = 2 if d.safety_flag else 1
                    demand[d.corridor_id][d.department_id] += \
                        d.base_duration_min * weight

            for cor in corridors:
                dep_minutes = demand.get(cor.id)
                if not dep_minutes:
                    continue
                need = sum(dep_minutes.values())
                dept_id = max(dep_minutes, key=dep_minutes.get)

                gaps = _week_free_gaps(s, cor.id, wk_start, wk_end)
                if not gaps:
                    continue
                gs, ge = max(gaps, key=lambda g: g[1] - g[0])
                avail = int((ge - gs).total_seconds() // 60)
                reserve = min(need, avail)
                reserve = max(_ROUND, (reserve // _ROUND) * _ROUND)
                reserve = min(reserve, avail)      # never exceed the gap

                rows.append(MonthlyReservation(
                    corridor_id=cor.id, department_id=dept_id,
                    window_start=gs, window_end=gs + timedelta(minutes=reserve),
                    reserved_minutes=reserve,
                    note=f"week {w+1}: demand {need} min "
                         f"(dominant dept {departments[dept_id]})"))
                total_min += reserve

        s.add_all(rows)

        solve_row = Solve(
            kind=SolveKind.MONTHLY, engine=SolveEngine.GREEDY,  # heuristic
            horizon_start=PLAN_START,
            horizon_end=PLAN_START + timedelta(days=PLAN_DAYS),
            status=SolveStatus.COMPLETED,
            stats={"reservations": len(rows), "reserved_minutes": total_min},
        )
        s.add(solve_row)
        s.commit()
        solve_id = solve_row.id            # read before session closes

        if verbose:
            codes = {c.id: c.code for c in corridors}
            print("=" * 64)
            print(f"MONTHLY PLAN (solve #{solve_id})")
            print(f"reservations: {len(rows)} | total reserved: {total_min} min")
            print("-" * 64)
            for r in rows:
                print(f"  {codes[r.corridor_id]:7} wk "
                      f"{(r.window_start - PLAN_START).days // 7 + 1} "
                      f"| {r.window_start:%a %d %H:%M}-"
                      f"{r.window_end:%H:%M} ({r.reserved_minutes:3} min) "
                      f"| {r.note}")
            print("=" * 64)
    return solve_id


if __name__ == "__main__":
    run_monthly()
