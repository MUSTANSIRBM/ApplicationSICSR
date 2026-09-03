"""
planner/score_demo.py — run scoring against the actual seeded data.

    python -m planner.score_demo

core stays pure; THIS file is the glue that reads SQLite, computes
corridor pressure from COA data, and hands plain rows to core.scoring.
Step 5 (API) will do exactly this same dance inside endpoints.
"""
from collections import defaultdict
from datetime import datetime
from sqlmodel import Session, select

from core.scoring import score_all
from planner.db import engine
from planner.models import Corridor, Defect, GoodsForecastSlot, TimetableSlot
from planner.reference import PLAN_START


def corridor_pressure(session: Session) -> dict:
    """0..1 busy-ness per corridor: occupancy minutes of trains+goods
    per window day, normalized across the 5 corridors. The caller owns
    this computation — core never queries anything."""
    trains = defaultdict(int)
    for t in session.exec(select(TimetableSlot)).all():
        trains[t.corridor_id] += (t.end - t.start).total_seconds() / 60
    for g in session.exec(select(GoodsForecastSlot)).all():
        trains[g.corridor_id] += (g.end - g.start).total_seconds() / 60
    if not trains:
        return {}
    lo, hi = min(trains.values()), max(trains.values())
    span = (hi - lo) or 1.0
    return {cid: (v - lo) / span for cid, v in trains.items()}


def run_demo() -> None:
    with Session(engine) as s:
        defects = s.exec(select(Defect)).all()
        corridors = {c.id: c.code for c in s.exec(select(Corridor)).all()}
        pressure = corridor_pressure(s)

        # 'now' = end of week 1: some defects are already overdue
        now = PLAN_START.replace(day=10) if PLAN_START.day <= 10 else PLAN_START
        now = datetime(2024, 6, 10, 8, 0)

        results = score_all(defects, now=now, corridor_pressure=pressure)

        print("=" * 66)
        print(f"SCORED {len(results)} DEFECTS at {now:%Y-%m-%d %H:%M}")
        print("=" * 66)
        for i, r in enumerate(results[:8], start=1):
            d = next(x for x in defects if x.id == r.defect_id)
            tier = "SAFETY" if r.tier == 1 else "routine"
            print(f"#{i:2} {d.source_ref:14} | {tier:6} | total {r.total:>5} "
                  f"| {d.defect_type:22} | {corridors[d.corridor_id]}")
        print("-" * 66)
        print("full reasoning for rank #1:")
        top = results[0]
        for k, v in top.components.items():
            print(f"    {k:15} +{v['value']:>5}  ({v['detail']})")
        print("=" * 66)
        print(f"corridor pressure: "
              f"{ {corridors[c]: round(p, 2) for c, p in pressure.items()} }")


if __name__ == "__main__":
    run_demo()
