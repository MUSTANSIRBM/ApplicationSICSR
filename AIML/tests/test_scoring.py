"""
Scoring tests: the tier wall, component math, caps, purity contract,
and the aging boost. All with plain namespace objects — core scoring
is proven without touching the DB.
"""
import inspect
from datetime import datetime, timedelta
from types import SimpleNamespace as NS

import core.scoring as scoring
from core.scoring import DEFAULT_WEIGHTS, score_all, score_defect

NOW = datetime(2024, 6, 10, 8, 0)


def _defect(**kw):
    base = dict(id=1, severity=3, safety_flag=False, corridor_id=1,
                reported_at=NOW - timedelta(days=5),
                due_by=NOW + timedelta(days=5))
    base.update(kw)
    return NS(**base)


def test_tier_wall_is_absolute():
    # Decision 1: severity-1 SAFETY ranks above a maxed-out routine task.
    safety = _defect(id=1, severity=1, safety_flag=True)
    routine = _defect(id=2, severity=5, due_by=NOW - timedelta(days=30))
    results = score_all([routine, safety], now=NOW, corridor_pressure={1: 1.0})
    assert results[0].defect_id == 1
    assert results[0].tier == 1


def test_total_is_sum_of_components():
    # Decision 8: the total must be reconstructible from the components.
    d = _defect(id=1, severity=4, due_by=NOW - timedelta(days=2))
    r = score_defect(d, now=NOW, corridor_pressure=0.8, prior_deferrals=1)
    component_sum = round(sum(c["value"] for c in r.components.values()), 2)
    assert abs(r.total - component_sum) < 0.02


def test_overdue_component_math():
    d = _defect(id=1, due_by=NOW - timedelta(days=2))
    r = score_defect(d, now=NOW)
    assert abs(r.components["overdue_days"]["value"]
               - round(DEFAULT_WEIGHTS["W_OVERDUE"] * 2, 2)) < 0.01


def test_overdue_caps():
    d = _defect(id=1, due_by=NOW - timedelta(days=60))
    r = score_defect(d, now=NOW)
    assert r.components["overdue_days"]["value"] <= \
        round(DEFAULT_WEIGHTS["W_OVERDUE"] * 5, 2) + 0.01


def test_aging_boost_small_and_capped():
    # Decision 7: deferred retries get a small boost, capped at 3.
    d = _defect(id=1)
    r0 = score_defect(d, now=NOW, prior_deferrals=0)
    r1 = score_defect(d, now=NOW, prior_deferrals=1)
    r9 = score_defect(d, now=NOW, prior_deferrals=9)
    assert r1.total > r0.total
    assert r9.total == score_defect(d, now=NOW, prior_deferrals=3).total


def test_not_yet_due_scores_no_overdue():
    d = _defect(id=1, due_by=NOW + timedelta(days=3))
    r = score_defect(d, now=NOW)
    assert r.components["overdue_days"]["value"] == 0


def test_ranking_is_deterministic():
    defects = [_defect(id=i, severity=(i % 5) + 1,
                       due_by=NOW - timedelta(days=i)) for i in range(1, 8)]
    a = score_all(defects, now=NOW)
    b = score_all(defects, now=NOW)
    assert [r.defect_id for r in a] == [r.defect_id for r in b]


def test_core_purity_contract():
    # ARCHITECTURE RULE enforced by test: core/ imports no sqlmodel,
    # no fastapi, no ortools. ML (sklearn/xgboost) stays out too.
    src = inspect.getsource(scoring)
    for banned in ("import sqlmodel", "from sqlmodel",
                   "import fastapi", "from fastapi",
                   "import sklearn", "from sklearn",
                   "import xgboost", "from xgboost"):
        assert banned not in src, f"PURITY BREACH: core/scoring.py contains '{banned}'"
