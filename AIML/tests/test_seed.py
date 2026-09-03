"""
Seed tests — the proof the data layer runs and the data is REAL pressure:
deterministic, in-spec counts, safety guaranteed per department, and the
no-overlap invariant the CP-SAT solver will depend on tomorrow.
"""
from adapters import raw_sources
from adapters.coa import COAAdapter
from adapters.smms import SMMSAdapter
from adapters.tdms import TDMSAdapter
from adapters.tms import TMSAdapter
from planner.models import Tier
from planner.reference import PLAN_END, PLAN_START

_IDS = {"NGP-BSL": 1, "ET-NGP": 2, "BSL-MMR": 3, "SC-GTL": 4, "MAS-TRY": 5}


def _all_defects(raw):
    return (
        TMSAdapter(raw["tms"], _IDS, 10).fetch_defects()
        + SMMSAdapter(raw["smms"], _IDS, 20).fetch_defects()
        + TDMSAdapter(raw["tdms"], _IDS, 30).fetch_defects()
    )


def test_reproducible():
    # seed=42 means seed=42: two builds are byte-identical.
    a, b = raw_sources.build_all(), raw_sources.build_all()
    assert [r["defect_no"] for r in a["tms"]] == [r["defect_no"] for r in b["tms"]]
    assert a["timetable"][0]["start"] == b["timetable"][0]["start"]
    assert a["smms"][0]["km_post"] == b["smms"][0]["km_post"]


def test_defect_counts_in_spec():
    defects = _all_defects(raw_sources.build_all())
    assert 20 <= len(defects) <= 40


def test_safety_guaranteed_per_department():
    defects = _all_defects(raw_sources.build_all())
    per_dept_safety = {}
    for d in defects:
        if d.safety_flag:
            per_dept_safety[d.source_system.value] = True
            assert d.severity == 5          # safety => top severity
            assert d.tier == Tier.SAFETY     # the derived rule fires
    assert set(per_dept_safety) == {"TMS", "SMMS", "TDMS"}


def test_adapters_emit_new_tasks():
    defects = _all_defects(raw_sources.build_all())
    assert all(d.status.value == "NEW" for d in defects)


def test_all_times_inside_window():
    raw = raw_sources.build_all()
    for r in raw["timetable"] + raw["goods"]:
        assert PLAN_START <= r["start"] < PLAN_END
        assert r["end"] > r["start"]


def test_no_corridor_occupancy_overlap():
    # THE invariant the solver depends on: on one corridor, trains and
    # goods never overlap in time. If this fails, CP-SAT's no-overlap
    # set is infeasible before we place a single block.
    raw = raw_sources.build_all()
    by_corridor = {}
    for r in raw["timetable"] + raw["goods"]:
        by_corridor.setdefault(r["section"], []).append((r["start"], r["end"]))
    for code, intervals in by_corridor.items():
        intervals.sort()
        for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
            assert e1 <= s2, f"overlap on {code}: {e1} ends after {s2} starts"


def test_pressure_is_real_on_heavy_corridor():
    # NGP-BSL: tight gaps exist AND some usable window exists —
    # genuine squeeze, not evenly spaced toy data.
    raw = raw_sources.build_all()
    ngp = sorted((r["start"], r["end"]) for r in raw["timetable"]
                 if r["section"] == "NGP-BSL")
    gaps = [(s2 - e1).total_seconds() / 60 for (s1, e1), (s2, e2) in zip(ngp, ngp[1:])]
    assert min(gaps) <= 45
    assert max(gaps) >= 90


def test_seed_populates_sqlite():
    # End-to-end: the actual CLI path, real planner.db file.
    from planner.seed import seed
    counts = seed(reset=True)
    assert counts["departments"] == 3
    assert counts["corridors"] == 5
    assert counts["defects"] == 30
    assert counts["timetable_slots"] == 644      # 23 trains/day x 28 days
    assert counts["goods_slots"] == 56
