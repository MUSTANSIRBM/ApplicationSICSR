"""
ml_calibration/train.py — python -m ml_calibration.train

THE ML CORNER. Offline only. Never imported by core/, api/, or anything
in the live path (a purity test enforces the reverse direction too).

WHAT IT DOES:
1. Reads solve history from planner.db: every TaskScore row = one
   (defect, solve) pair with its four scoring inputs + the outcome
   (scheduled=1, deferred/escalated=0).
2. Trains RandomForest and XGBoost classifiers to predict the outcome
   from the inputs.
3. Extracts feature importances — WHICH inputs actually mattered.
4. Converts importances into MULTIPLIERS on the four default weights,
   clamped to 0.5x-2.0x: ML can re-balance the formula, never blow it up.
   SAFETY IS NEVER A WEIGHT (locked decision 1): the tier lives in the
   solver's rank key, untouched by anything here.
5. Backtests old vs new weights on the historical solves.
6. Writes weights.json at repo root — the ONLY integration point.
   core/scoring.load_weights() already picks it up.

Run order:  data_check -> (gen_history if thin) -> train -> evaluate
"""
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from sqlmodel import Session, select

from core.scoring import DEFAULT_WEIGHTS, load_weights
from planner.db import engine
from planner.models import (
    Defect, Deferral, GoodsForecastSlot, Solve, SolveKind, TaskScore,
    TimetableSlot,
)

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

SEED = 42
WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "weights.json"

FEATURES = ["severity", "overdue_days", "traffic_pressure",
            "prior_deferrals", "duration_min"]
WEIGHT_KEYS = ["W_SEVERITY", "W_OVERDUE", "W_TRAFFIC", "W_AGING"]
MULT_MIN, MULT_MAX = 0.5, 2.0
OVERDUE_CAP_DAYS = 5.0
AGING_CAP = 3


# ------------------------------------------------------------------ dataset

def _corridor_pressure(session) -> Dict[int, float]:
    minutes = defaultdict(int)
    for t in session.exec(select(TimetableSlot)).all():
        minutes[t.corridor_id] += (t.end - t.start).total_seconds() / 60
    for g in session.exec(select(GoodsForecastSlot)).all():
        minutes[g.corridor_id] += (g.end - g.start).total_seconds() / 60
    if not minutes:
        return {}
    lo, hi = min(minutes.values()), max(minutes.values())
    span = (hi - lo) or 1.0
    return {c: (v - lo) / span for c, v in minutes.items()}


def build_dataset() -> Tuple[np.ndarray, np.ndarray, list]:
    """Rows: one per (defect, weekly solve) pair that was in scope.
    Label: 1 = scheduled in that solve, 0 = deferred or escalated."""
    with Session(engine) as s:
        solves = s.exec(select(Solve).where(
            Solve.kind == SolveKind.WEEKLY)
            .order_by(Solve.id)).all()
        if not solves:
            raise SystemExit("No weekly solves in planner.db — "
                             "run ml_calibration.gen_history first.")
        pressure = _corridor_pressure(s)
        defects = {d.id: d for d in session_defects(s)}

        deferred_at = {(r.solve_id, r.defect_id)
                       for r in s.exec(select(Deferral)).all()}

        rows, labels, meta = [], [], []
        for sv in solves:
            # aging input: deferrals recorded BEFORE this solve
            prior = defaultdict(int)
            for r in s.exec(select(Deferral)).all():
                if r.solve_id < sv.id:
                    prior[r.defect_id] += 1

            for ts in s.exec(select(TaskScore).where(
                    TaskScore.solve_id == sv.id)).all():
                d = defects.get(ts.defect_id)
                if d is None:
                    continue
                overdue = (sv.horizon_start - d.due_by).total_seconds() / 86400
                overdue = max(0.0, min(overdue, OVERDUE_CAP_DAYS))
                rows.append([
                    d.severity / 5.0,
                    overdue,
                    pressure.get(d.corridor_id, 0.5),
                    min(prior.get(d.id, 0), AGING_CAP),
                    d.base_duration_min,
                ])
                was_deferred = (sv.id, d.id) in deferred_at
                labels.append(0 if was_deferred else 1)
                meta.append((sv.id, d.id))

    return np.array(rows, dtype=float), np.array(labels), meta


def session_defects(session):
    return session.exec(select(Defect)).all()


# ------------------------------------------------------------------ training

def _importances(X, y) -> Tuple[np.ndarray, np.ndarray]:
    rf = RandomForestClassifier(
        n_estimators=300, random_state=SEED, class_weight="balanced")
    rf.fit(X, y)
    xgb = XGBClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.1,
        random_state=SEED, eval_metric="logloss", verbosity=0)
    xgb.fit(X, y)
    return rf.feature_importances_, xgb.feature_importances_


def _multipliers(importances: np.ndarray) -> Dict[str, float]:
    """4 scoring inputs (skip duration) -> clamped multipliers."""
    scoring_imp = importances[:4]
    mean = scoring_imp.mean() or 1.0
    out = {}
    for key, imp in zip(WEIGHT_KEYS, scoring_imp):
        mult = float(np.clip(imp / mean, MULT_MIN, MULT_MAX))
        out[key] = mult
    return out


def _apply(defaults: Dict[str, float], mults: Dict[str, float]) -> dict:
    return {k: round(defaults[k] * mults[k], 3) for k in WEIGHT_KEYS}


# ------------------------------------------------------------------ backtest

def _score_rows(X: np.ndarray, weights: dict) -> np.ndarray:
    sev, overdue, traffic, aging, _dur = X.T
    return (weights["W_SEVERITY"] * sev + weights["W_OVERDUE"] * overdue
            + weights["W_TRAFFIC"] * traffic + weights["W_AGING"] * aging)


def _backtest(X, y, meta, weights: dict) -> float:
    """Metric: of the tasks that ACTUALLY got scheduled in a solve, how
    highly did this weight-set rank them? Mean of (scheduled rank from
    top / class size), higher = the ranking matches what worked."""
    by_solve = defaultdict(list)
    for i, (sv, dID) in enumerate(meta):
        by_solve[sv].append(i)

    scores = _score_rows(X, weights)
    hits = []
    for sv, idxs in by_solve.items():
        n_sched = int(y[idxs].sum())
        if n_sched == 0 or n_sched == len(idxs):
            continue
        order = sorted(idxs, key=lambda i: -scores[i])
        sched_pos = [order.index(i) for i in idxs if y[i] == 1]
        hits.extend(p / len(order) for p in sched_pos)
    return float(np.mean(hits)) if hits else 0.0


# ------------------------------------------------------------------ main

def train(verbose=True) -> dict:
    X, y, meta = build_dataset()
    if len(set(y)) < 2:
        raise SystemExit("History has only one outcome class (everything "
                         "scheduled or everything deferred) — nothing to "
                         "learn. Generate richer history first.")

    rf_imp, xgb_imp = _importances(X, y)
    rf_weights = _apply(DEFAULT_WEIGHTS, _multipliers(rf_imp))
    xgb_weights = _apply(DEFAULT_WEIGHTS, _multipliers(xgb_imp))

    base_score = _backtest(X, y, meta, DEFAULT_WEIGHTS)
    rf_score = _backtest(X, y, meta, rf_weights)
    xgb_score = _backtest(X, y, meta, xgb_weights)

    winner, winner_name = max(
        [(rf_weights, "RandomForest"), (xgb_weights, "XGBoost"),
         (dict(DEFAULT_WEIGHTS), "defaults")],
        key=lambda p: _backtest(X, y, meta, p[0]))

    import json
    WEIGHTS_FILE.write_text(json.dumps(winner, indent=2) + "\n")

    if verbose:
        print("=" * 60)
        print(f"ML CALIBRATION — {len(X)} training rows "
              f"({int(y.sum())} scheduled / {len(y) - int(y.sum())} deferred)")
        print("-" * 60)
        print(f"{'weight':12} {'default':>8} {'RF':>8} {'XGB':>8} "
              f"{'CHOSEN':>8}")
        for k in WEIGHT_KEYS:
            print(f"{k:12} {DEFAULT_WEIGHTS[k]:>8} {rf_weights[k]:>8} "
                  f"{xgb_weights[k]:>8} {winner[k]:>8}")
        print("-" * 60)
        print("backtest (higher = ranking matched real outcomes):")
        print(f"  defaults     : {base_score:.3f}")
        print(f"  RandomForest : {rf_score:.3f}")
        print(f"  XGBoost      : {xgb_score:.3f}")
        print(f"  CHOSEN       : {winner_name}")
        print(f"wrote {WEIGHTS_FILE}")
        print("=" * 60)
    return winner


if __name__ == "__main__":
    train()

