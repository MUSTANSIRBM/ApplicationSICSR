"""
ml_calibration/evaluate.py — python -m ml_calibration.evaluate

The pitch slide generator: default weights vs ML-calibrated weights,
side by side, on the CURRENT defect set. Shows how the ranking shifts.
NOTE: the next actual solve uses the calibrated weights via
core.scoring.load_weights() — this script only LOOKS, never writes.
"""
from datetime import datetime

from sqlmodel import Session, select

from core.scoring import DEFAULT_WEIGHTS, load_weights, score_all
from planner.db import engine
from planner.models import Defect, TaskStatus

NOW = datetime(2024, 6, 10, 8, 0)   # same anchor as score_demo


def evaluate(verbose=True):
    calibrated = load_weights()
    with Session(engine) as s:
        defects = s.exec(select(Defect).where(
            Defect.status.in_((TaskStatus.NEW, TaskStatus.DEFERRED,
                               TaskStatus.ESCALATED)))).all()

    base = score_all(defects, now=NOW, weights=DEFAULT_WEIGHTS)
    calib = score_all(defects, now=NOW, weights=calibrated)

    base_rank = {r.defect_id: i for i, r in enumerate(base, 1)}
    calib_rank = {r.defect_id: i for i, r in enumerate(calib, 1)}

    moved = []
    for d in defects:
        delta = abs(base_rank[d.id] - calib_rank[d.id])
        if delta > 0:
            moved.append((delta, d.id, d, base_rank[d.id], calib_rank[d.id]))
    # sort by delta desc, then defect id as tie-breaker — NEVER compare
    # Defect objects directly (they don't support ordering).
    moved.sort(key=lambda m: (-m[0], m[1]))

    if verbose:
        print("=" * 62)
        print("WEIGHTS IN EFFECT")
        print(f"  defaults   : {DEFAULT_WEIGHTS}")
        print(f"  calibrated : {calibrated}")
        print("-" * 62)
        print(f"defects ranked: {len(defects)} | "
              f"rank changes: {len(moved)}")
        print("biggest movers (default rank -> calibrated rank):")
        for delta, _id, d, br, cr in moved[:8]:
            arrow = "↑" if cr < br else "↓"
            print(f"  {d.source_ref:14} #{br:>2} -> #{cr:>2} {arrow} "
                  f"| {d.defect_type}")
        if not moved:
            print("  (identical ordering — calibrated weights preserve "
                  "the default ranking)")
        print("=" * 62)
    return {"calibrated": calibrated, "rank_changes": len(moved)}


if __name__ == "__main__":
    evaluate()

