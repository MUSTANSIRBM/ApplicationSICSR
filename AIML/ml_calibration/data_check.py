"""
ml_calibration/data_check.py — python -m ml_calibration.data_check

Answers one question before you waste a training run:
"Is there enough solve history in planner.db to learn from?"
Rule of thumb: >= 4 solves and >= 20 scored tasks = trainable.
"""
from sqlmodel import Session, select

from planner.db import engine
from planner.models import Deferral, Solve, SolveKind, TaskScore


def check(verbose=True) -> dict:
    with Session(engine) as s:
        weekly = s.exec(select(Solve).where(
            Solve.kind == SolveKind.WEEKLY)).all()
        scores = s.exec(select(TaskScore)).all()
        deferrals = s.exec(select(Deferral)).all()

    stats = {
        "weekly_solves": len(weekly),
        "task_scores": len(scores),
        "deferrals": len(deferrals),
        "trainable": len(weekly) >= 4 and len(scores) >= 20,
    }
    if verbose:
        print("=" * 52)
        print("ML TRAINING DATA CHECK — planner.db")
        print(f"  weekly solves   : {stats['weekly_solves']}")
        print(f"  scored tasks    : {stats['task_scores']}")
        print(f"  deferral events : {stats['deferrals']}")
        verdict = ("TRAINABLE — proceed to ml_calibration.train"
                   if stats["trainable"] else
                   "NOT ENOUGH — run ml_calibration.gen_history first")
        print(f"  verdict         : {verdict}")
        print("=" * 52)
    return stats


if __name__ == "__main__":
    check()

