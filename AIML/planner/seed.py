"""
planner/seed.py — the Day 1 CLI.

    python -m planner.seed

Wipes planner.db (no-migrations policy), creates tables, pulls every
source through its adapter, writes unified rows, prints a summary.
"""
import os

from sqlmodel import Session, select

from adapters import raw_sources
from adapters.coa import COAAdapter
from adapters.smms import SMMSAdapter
from adapters.tdms import TDMSAdapter
from adapters.tms import TMSAdapter
from planner.db import DB_FILE, create_all, engine
from planner.models import (
    Corridor, Defect, Department, DepartmentCode, GoodsForecastSlot,
    SourceSystem, TimetableSlot,
)
from planner.reference import CORRIDORS, DEPARTMENTS, PLAN_END, PLAN_START

def seed(reset: bool = True):
    if reset and os.path.exists(DB_FILE):
        engine.dispose()          # release pooled "ghost" connections BEFORE deleting
        os.remove(DB_FILE)        # dev reset: nuke + re-seed, by design
    create_all()

    raw = raw_sources.build_all()

    with Session(engine) as s:
        # reference data first — everything else hangs off these ids
        corridors = [Corridor(code=c["code"], name=c["name"], zone=c["zone"],
                              km_start=c["km_start"], km_end=c["km_end"],
                              lines=c["lines"], notes=f'traffic: {c["traffic"]}')
                     for c in CORRIDORS]
        departments = [Department(code=DepartmentCode(d["code"]), name=d["name"],
                                  source_system=SourceSystem(d["source"]))
                       for d in DEPARTMENTS]
        s.add_all(corridors + departments)
        s.commit()
        for obj in corridors + departments:
            s.refresh(obj)

        corridor_ids = {c.code: c.id for c in corridors}
        dept_ids = {d.code.value: d.id for d in departments}

        # the adapter wall: sources in, unified schema out
        defects = (
            TMSAdapter(raw["tms"], corridor_ids, dept_ids["ENG"]).fetch_defects()
            + SMMSAdapter(raw["smms"], corridor_ids, dept_ids["TRD"]).fetch_defects()
            + TDMSAdapter(raw["tdms"], corridor_ids, dept_ids["SNT"]).fetch_defects()
        )
        coa = COAAdapter(raw["timetable"], raw["goods"], corridor_ids)
        slots = coa.fetch_timetable_slots()
        goods = coa.fetch_goods_slots()

        s.add_all(defects)
        s.add_all(slots)
        s.add_all(goods)
        s.commit()

        counts = {
            "departments":     len(s.exec(select(Department)).all()),
            "corridors":       len(s.exec(select(Corridor)).all()),
            "defects":         len(s.exec(select(Defect)).all()),
            "timetable_slots": len(s.exec(select(TimetableSlot)).all()),
            "goods_slots":     len(s.exec(select(GoodsForecastSlot)).all()),
        }
        _print_summary(counts, defects, slots, goods)
    return counts


def _print_summary(counts, defects, slots, goods):
    print("=" * 62)
    print("SEED COMPLETE (seed=42)")
    print(f"window : {PLAN_START:%Y-%m-%d} to {PLAN_END:%Y-%m-%d} (4 weeks)")
    print(f"db file: {DB_FILE}")
    print("-" * 62)
    for k, v in counts.items():
        print(f"  {k:16} {v}")
    print("-" * 62)
    per_source = {}
    safety_n = 0
    for d in defects:
        per_source[d.source_system.value] = per_source.get(d.source_system.value, 0) + 1
        safety_n += d.safety_flag
    print(f"  defects per source : {per_source}")
    print(f"  safety-flagged     : {safety_n}  (Tier 1 — hard tier)")
    print("-" * 62)
    print("  sample defects:")
    for d in defects[:2]:
        print(f"    {d.source_ref} | {d.defect_type} | sev {d.severity}"
              f" | safety {d.safety_flag} | {d.base_duration_min} min"
              f" | due {d.due_by:%Y-%m-%d %H:%M}")
    print("  sample trains:")
    for t in slots[:2]:
        print(f"    {t.train_no} {t.train_name} ({t.train_type.value})"
              f" {t.start:%a %H:%M} - {t.end:%H:%M}")
    print("  sample goods:")
    g = goods[0]
    print(f"    {g.label} | {g.start:%a %H:%M} - {g.end:%H:%M} | {g.expected_rakes} rake(s)")
    print("=" * 62)


if __name__ == "__main__":
    seed()
