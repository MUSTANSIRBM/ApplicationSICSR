"""
core/solver.py — the weekly block planner (OR-Tools CP-SAT + greedy fallback).

PURITY: stdlib + ortools only. No sqlmodel, no fastapi — a test enforces it.

SOLVER HYGIENE (locked):
- Real NewIntervalVar / NewOptionalIntervalVar objects feed AddNoOverlap.
- Trains + goods are FIXED intervals inside each corridor's no-overlap set.
  APPROVED/LOCKED blocks arrive the same way (pinned = immovable).
- max_time_in_seconds always set.
- OPTIMAL and FEASIBLE are both success. INFEASIBLE / UNKNOWN never crash.

BUNDLING (locked decision 2): candidate bundles (singles, pairs, triples
with due dates within 3 days) are optional intervals; each task lands in
exactly one chosen bundle or none. Bundle duration is MAX of task
durations — never the sum.

DEFERRALS (locked decision 3): every unscheduled task returns
machine-readable reasons. ESCALATED = a deferred safety task.

MONTHLY LINK (locked decision 5): reservations are SOFT. A block fully
inside a reservation window earns a bonus in the objective. A window
too small can NEVER make the model infeasible — the weekly plan wins.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

from ortools.sat.python import cp_model

MAX_TIME_IN_SECONDS = 5.0

_BUNDLE_MAX_SIZE = 3
_BUNDLE_DUE_SPREAD = timedelta(days=3)
_SAFETY_BASE = 1000.0

_SCALE = 10000
_W_LATENESS_PER_MIN = 1
_W_CLOSURE_PER_MIN = 10
_W_RES_BONUS = 15000


@dataclass
class TaskIn:
    id: int
    corridor_id: int
    department_id: int
    duration_min: int
    tier: int
    score: float
    due_by: datetime
    safety_flag: bool


@dataclass
class OccupiedIn:
    corridor_id: int
    start: datetime
    end: datetime
    kind: str
    ref: str


@dataclass
class ReservationIn:
    """Monthly-plan soft window. Containment (block fully inside) earns
    the bonus; partial overlap earns nothing — rough plan, clean rule."""
    corridor_id: int
    start: datetime
    end: datetime


@dataclass
class BlockOut:
    corridor_id: int
    start: datetime
    end: datetime
    task_ids: tuple
    closure_minutes: int
    is_combined: bool


@dataclass
class DeferredOut:
    task_id: int
    escalated: bool
    reasons: List[dict] = field(default_factory=list)


@dataclass
class SolverResult:
    engine: str
    status: str
    blocks: List[BlockOut] = field(default_factory=list)
    deferred: List[DeferredOut] = field(default_factory=list)
    objective: Optional[int] = None
    wall_time_ms: int = 0


@dataclass
class _Cand:
    task_ids: tuple
    corridor_id: int
    duration_min: int
    value: float
    due_min: int


def _to_min(t: datetime, week_start: datetime) -> int:
    return int((t - week_start).total_seconds() // 60)


def _task_value(t: TaskIn) -> float:
    return (_SAFETY_BASE + t.score) if t.safety_flag else t.score


def _build_candidates(tasks: Sequence[TaskIn], week_start: datetime,
                      horizon: int) -> List[_Cand]:
    cands: List[_Cand] = []
    by_cor: Dict[int, List[TaskIn]] = {}
    for t in tasks:
        by_cor.setdefault(t.corridor_id, []).append(t)
    for cid, group in by_cor.items():
        group = sorted(group, key=lambda t: (t.tier, -t.score, t.due_by))
        for t in group:
            if t.duration_min > horizon:
                continue
            cands.append(_Cand((t.id,), cid, t.duration_min, _task_value(t),
                                max(0, _to_min(t.due_by, week_start))))
        for size in range(2, _BUNDLE_MAX_SIZE + 1):
            for i in range(len(group) - size + 1):
                window = group[i:i + size]
                if any(t.duration_min > horizon for t in window):
                    continue
                spread = (max(t.due_by for t in window)
                          - min(t.due_by for t in window))
                if spread > _BUNDLE_DUE_SPREAD:
                    continue
                dur = max(t.duration_min for t in window)
                val = sum(_task_value(t) for t in window)
                due = min(_to_min(t.due_by, week_start) for t in window)
                cands.append(_Cand(tuple(t.id for t in window), cid,
                                   dur, val, max(0, due)))
    return cands


def _fixed_by_corridor(occupied: Sequence[OccupiedIn], week_start: datetime,
                       week_end: datetime):
    horizon = int((week_end - week_start).total_seconds() // 60)
    fixed: Dict[int, list] = {}
    for o in occupied:
        s, e = max(o.start, week_start), min(o.end, week_end)
        if s >= e:
            continue
        fixed.setdefault(o.corridor_id, []).append(
            (_to_min(s, week_start), _to_min(e, week_start), o.kind, o.ref))
    for cid, items in fixed.items():
        items.sort()
        for (s1, e1, k1, r1), (s2, e2, k2, r2) in zip(items, items[1:]):
            if e1 > s2:
                raise ValueError(
                    f"Fixed-occupancy conflict on corridor {cid}: "
                    f"[{r1} ({k1})] overlaps [{r2} ({k2})]. "
                    f"Data error — solve refused, nothing silent.")
    return fixed, horizon


def _res_to_windows(reservations: Sequence[ReservationIn],
                    week_start: datetime, week_end: datetime) -> Dict[int, list]:
    out: Dict[int, list] = {}
    for r in reservations:
        s, e = max(r.start, week_start), min(r.end, week_end)
        if s >= e:
            continue
        out.setdefault(r.corridor_id, []).append(
            (_to_min(s, week_start), _to_min(e, week_start)))
    return out


def free_gaps(items: Sequence[tuple], horizon: int) -> List[tuple]:
    gaps, cursor = [], 0
    for s, e, *_ in items:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < horizon:
        gaps.append((cursor, horizon))
    return gaps


def _cp_sat(week_start, horizon, fixed, cands, windows):
    m = cp_model.CpModel()
    intervals: Dict[int, list] = {cid: [] for cid in fixed}

    for cid, items in fixed.items():
        for sm, em, kind, ref in items:
            iv = m.NewIntervalVar(sm, em - sm, em, f"fix_{kind}_{sm}")
            intervals[cid].append(iv)

    pres, starts, lates, durs, vals, cids = [], [], [], [], [], []
    cand_of_task: Dict[int, List[int]] = {}
    for i, c in enumerate(cands):
        p = m.NewBoolVar(f"p{i}")
        st = m.NewIntVar(0, horizon - c.duration_min, f"s{i}")
        en = m.NewIntVar(c.duration_min, horizon, f"e{i}")
        iv = m.NewOptionalIntervalVar(st, c.duration_min, en, p, f"iv{i}")
        intervals.setdefault(c.corridor_id, []).append(iv)
        late = m.NewIntVar(0, horizon, f"late{i}")
        m.Add(late >= en - c.due_min)
        pres.append(p); starts.append(st); lates.append(late)
        durs.append(c.duration_min); vals.append(c.value); cids.append(c.corridor_id)
        for tid in c.task_ids:
            cand_of_task.setdefault(tid, []).append(i)

    for tid, idxs in cand_of_task.items():
        tb = m.NewBoolVar(f"t{tid}")
        m.Add(sum(pres[j] for j in idxs) == tb)

    for ivs in intervals.values():
        if ivs:
            m.AddNoOverlap(ivs)

    obj = []
    for i, c in enumerate(cands):
        obj.append(pres[i] * int(round(vals[i] * _SCALE)))
        obj.append(-lates[i] * _W_LATENESS_PER_MIN)
        obj.append(-pres[i] * durs[i] * _W_CLOSURE_PER_MIN)
        # --- monthly soft link (decision 5): bonus for containment ---
        for j, (ws, we) in enumerate(windows.get(c.corridor_id, [])):
            if we - ws < c.duration_min:
                continue
            b = m.NewBoolVar(f"res{i}_{j}")
            m.Add(starts[i] >= ws).OnlyEnforceIf(b)
            m.Add(starts[i] + c.duration_min <= we).OnlyEnforceIf(b)
            m.AddImplication(b, pres[i])
            obj.append(b * _W_RES_BONUS)
    m.Maximize(sum(obj))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = MAX_TIME_IN_SECONDS
    status = solver.Solve(m)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    blocks = []
    for i, c in enumerate(cands):
        if solver.Value(pres[i]):
            sm = solver.Value(starts[i])
            blocks.append(BlockOut(
                c.corridor_id,
                week_start + timedelta(minutes=sm),
                week_start + timedelta(minutes=sm + c.duration_min),
                c.task_ids, c.duration_min, len(c.task_ids) > 1))
    return (solver.StatusName(status), blocks,
            int(solver.ObjectiveValue()), int(solver.WallTime() * 1000))


def _greedy(week_start, horizon, fixed, cands, windows=None):
    windows = windows or {}
    blocks, scheduled = [], set()
    dyn = {cid: list(items) for cid, items in fixed.items()}
    for c in sorted(cands, key=lambda c: -c.value):
        if any(tid in scheduled for tid in c.task_ids):
            continue
        items = sorted(dyn.get(c.corridor_id, []))
        fitting = []
        for gs, ge in free_gaps(items, horizon):
            if ge - gs >= c.duration_min:
                wins = windows.get(c.corridor_id, [])
                inside = any(gs >= ws and gs + c.duration_min <= we
                             for ws, we in wins)
                fitting.append((0 if inside else 1, gs))
        if fitting:
            fitting.sort()
            gs = fitting[0][1]
            blocks.append(BlockOut(
                c.corridor_id,
                week_start + timedelta(minutes=gs),
                week_start + timedelta(minutes=gs + c.duration_min),
                c.task_ids, c.duration_min, len(c.task_ids) > 1))
            dyn.setdefault(c.corridor_id, []).append(
                (gs, gs + c.duration_min, "block", f"B{len(blocks)}"))
            scheduled.update(c.task_ids)
    return blocks


def _deferrals(week_start, horizon, tasks, blocks, fixed):
    scheduled = set()
    for b in blocks:
        scheduled.update(b.task_ids)
    merged = {cid: list(items) for cid, items in fixed.items()}
    for b in blocks:
        sm = _to_min(b.start, week_start)
        merged.setdefault(b.corridor_id, []).append(
            (sm, sm + b.closure_minutes, "block", "planned block"))

    out = []
    for t in tasks:
        if t.id in scheduled:
            continue
        items = sorted(merged.get(t.corridor_id, []))
        gaps = free_gaps(items, horizon)
        reasons = []
        if not gaps:
            reasons.append({"kind": "corridor_saturated",
                            "detail": "no free gap in the week"})
        else:
            gs, ge = max(gaps, key=lambda g: g[1] - g[0])
            if (ge - gs) < t.duration_min:
                for s, e, kind, ref in items:
                    if e == gs or s == ge:
                        reasons.append({"kind": kind, "ref": ref})
                reasons.append({"kind": "window_too_small",
                                "needed_min": t.duration_min,
                                "longest_free_gap_min": int(ge - gs)})
            else:
                reasons.append({"kind": "outcompeted",
                                "detail": "corridor time went to higher-ranked tasks"})
        out.append(DeferredOut(t.id, t.safety_flag, reasons))
    return out


def solve(week_start: datetime, week_end: datetime,
          tasks: Sequence[TaskIn], occupied: Sequence[OccupiedIn],
          reservations: Sequence[ReservationIn] = (),
          force_greedy: bool = False) -> SolverResult:
    t0 = datetime.now()
    fixed, horizon = _fixed_by_corridor(occupied, week_start, week_end)
    windows = _res_to_windows(reservations, week_start, week_end)
    cands = _build_candidates(tasks, week_start, horizon)

    if force_greedy:
        blocks = _greedy(week_start, horizon, fixed, cands, windows)
        engine, status, objective = "GREEDY", "FALLBACK", None
    else:
        got = _cp_sat(week_start, horizon, fixed, cands, windows)
        if got is None:
            blocks = _greedy(week_start, horizon, fixed, cands, windows)
            engine, status, objective = "GREEDY", "FALLBACK", None
        else:
            status, blocks, objective, _ = got
            engine = "CP_SAT"

    deferred = _deferrals(week_start, horizon, tasks, blocks, fixed)
    wall = int((datetime.now() - t0).total_seconds() * 1000)
    return SolverResult(engine, status, blocks, deferred, objective, wall)


if __name__ == "__main__":
    MON = datetime(2024, 6, 3)
    TUE = MON + timedelta(days=1)

    trains = [OccupiedIn(1, MON + timedelta(hours=h),
                         MON + timedelta(hours=h + 2), "train", f"EXP-{h:02d}")
              for h in (6, 9, 13, 17, 21)]

    tasks = [
        TaskIn(1, 1, 1, 60, 1, 3.0, MON + timedelta(hours=18), False),
        TaskIn(2, 1, 3, 90, 3, 3.0, MON + timedelta(hours=18), False),
        TaskIn(3, 1, 2, 240, 2, 4.5, MON + timedelta(hours=12), True),
        TaskIn(4, 1, 1, 400, 1, 3.0, MON + timedelta(hours=18), False),
    ]
    res = solve(MON, TUE, tasks, trains)

    print(f"engine {res.engine} | status {res.status} | {res.wall_time_ms} ms")
    for b in res.blocks:
        tag = "COMBINED" if b.is_combined else "single  "
        print(f"  block {tag} {b.start:%H:%M}-{b.end:%H:%M} "
              f"({b.closure_minutes} min) tasks {b.task_ids}")
    for df in res.deferred:
        tag = "ESCALATED (safety)" if df.escalated else "deferred"
        print(f"  task {df.task_id} {tag}")
        for r in df.reasons:
            print(f"      - {r}")

    assert any(3 in b.task_ids for b in res.blocks), "safety must be scheduled"
    assert any(df.task_id == 4 and not df.escalated for df in res.deferred)
    print("SOLVER SMOKE TEST OK")









