"""
core/scoring.py — the transparent live scoring engine.

PURITY CONTRACT: this module imports stdlib only. No FastAPI, no
SQLModel, no OR-Tools. It accepts duck-typed objects with these
attributes: severity, safety_flag, reported_at, due_by, corridor_id.
SQLModel Defect rows qualify. A test enforces this contract.

LOCKED DECISION 1: safety_flag is a hard TIER, not a weight. The rank
key is (tier, -total). A severity-1 safety task outranks a severity-5
routine task no matter what the formula says. Scoring only orders
WITHIN a tier.

LOCKED DECISION 7: the formula is transparent and every component is
returned, never just the total — the frontend renders components, it
never recomputes them. ML never touches this file's live path; it only
tunes DEFAULT_WEIGHTS offline, through weights.json.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# The four numbers the ML calibration corner will tune offline.
# Loading order: caller-provided > weights.json > these defaults.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "W_SEVERITY": 2.0,    # x (severity/5)     -> 0 .. 2.0
    "W_OVERDUE": 0.4,     # x overdue_days     -> 0 .. 2.0 (capped)
    "W_TRAFFIC": 1.0,     # x corridor_pressure-> 0 .. 1.0
    "W_AGING": 0.25,      # x prior_deferrals  -> 0 .. 0.75 (capped)
}

_OVERDUE_CAP_DAYS = 5.0    # 0.4 x 5 = 2.0 max contribution
_AGING_CAP = 3             # 0.25 x 3 = 0.75 max contribution

WEIGHTS_FILE = Path(__file__).resolve().parent.parent / "weights.json"


@dataclass
class ScoreResult:
    """One defect's score + its full reasoning. This IS the explainability
    payload — step 5 persists it straight into TaskScore.components."""
    defect_id: Optional[int]
    tier: int                          # 1 = safety, 2 = routine
    total: float
    components: Dict[str, Any] = field(default_factory=dict)
    # components = {
    #   "severity":       {"value": 1.2, "detail": "severity 3/5, w=2.0"},
    #   "overdue_days":   {"value": 0.8, "detail": "2 days overdue, w=0.4"},
    #   "traffic_impact": {"value": 0.3, "detail": "NGP-BSL pressure 0.30, w=1.0"},
    #   "aging_boost":    {"value": 0.0, "detail": "0 prior deferrals, w=0.25"},
    # }

    @property
    def rank_key(self):
        # THE tier wall: safety first, then score, newest report breaks ties.
        return (self.tier, -self.total)


def load_weights() -> Dict[str, float]:
    """Defaults <- weights.json <- nothing else. This file is the ONLY
    place ML output enters the live path: a JSON of four numbers."""
    if WEIGHTS_FILE.exists():
        import json
        with open(WEIGHTS_FILE) as f:
            user = json.load(f)
        return {**DEFAULT_WEIGHTS, **{k: float(v) for k, v in user.items()}}
    return dict(DEFAULT_WEIGHTS)


def score_defect(
    defect: Any,
    now: datetime,
    corridor_pressure: Optional[float] = None,
    prior_deferrals: int = 0,
    weights: Optional[Dict[str, float]] = None,
) -> ScoreResult:
    """Score ONE defect at time `now`.

    corridor_pressure: 0..1, how busy the defect's corridor is
    (trains+goods density). Caller computes it from COA data — core
    never queries anything. None -> neutral 0.5.

    prior_deferrals: how many times this defect was deferred before
    (the aging boost — decision 7).
    """
    w = weights or DEFAULT_WEIGHTS
    tier = 1 if defect.safety_flag else 2

    sev_norm = defect.severity / 5.0
    sev_val = round(w["W_SEVERITY"] * sev_norm, 2)

    overdue_days = (now - defect.due_by).total_seconds() / 86400.0
    overdue_days = max(0.0, min(overdue_days, _OVERDUE_CAP_DAYS))
    overdue_val = round(w["W_OVERDUE"] * overdue_days, 2)

    pressure = 0.5 if corridor_pressure is None else max(0.0, min(1.0, corridor_pressure))
    traffic_val = round(w["W_TRAFFIC"] * pressure, 2)

    aging_n = min(prior_deferrals, _AGING_CAP)
    aging_val = round(w["W_AGING"] * aging_n, 2)

    total = round(sev_val + overdue_val + traffic_val + aging_val, 2)

    return ScoreResult(
        defect_id=getattr(defect, "id", None),
        tier=tier,
        total=total,
        components={
            "severity": {"value": sev_val,
                         "detail": f"severity {defect.severity}/5, w={w['W_SEVERITY']}"},
            "overdue_days": {"value": overdue_val,
                             "detail": f"{overdue_days:.1f} days overdue, w={w['W_OVERDUE']}"},
            "traffic_impact": {"value": traffic_val,
                               "detail": f"corridor {getattr(defect, 'corridor_id', '?')} "
                                         f"pressure {pressure:.2f}, w={w['W_TRAFFIC']}"},
            "aging_boost": {"value": aging_val,
                            "detail": f"{prior_deferrals} prior deferrals, w={w['W_AGING']}"},
        },
    )


def score_all(
    defects: Iterable[Any],
    now: datetime,
    corridor_pressure: Optional[Dict[int, float]] = None,
    prior_deferrals: Optional[Dict[int, int]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> List[ScoreResult]:
    """Score a batch, ordered by rank key (tier, -total). Rank 1 = first
    in line. corridor_pressure / prior_deferrals are keyed by defect id."""
    pressure = corridor_pressure or {}
    deferrals = prior_deferrals or {}

    results = [
        score_defect(
            d,
            now=now,
            corridor_pressure=pressure.get(getattr(d, "id", None)),
            prior_deferrals=deferrals.get(getattr(d, "id", None), 0),
            weights=weights,
        )
        for d in defects
    ]
    results.sort(key=lambda r: r.rank_key)
    return results


# ------------------------------------------------------------------ smoke test

if __name__ == "__main__":
    # Pure-stdlib proof: plain namespace objects, NO database, NO sqlmodel.
    from datetime import timedelta
    from types import SimpleNamespace as NS

    now = datetime(2024, 6, 10, 8, 0)

    safety_low = NS(id=1, severity=1, safety_flag=True,
                    reported_at=now - timedelta(days=2),
                    due_by=now + timedelta(days=1), corridor_id=1)
    routine_big = NS(id=2, severity=5, safety_flag=False,
                     reported_at=now - timedelta(days=20),
                     due_by=now - timedelta(days=3), corridor_id=1)

    results = score_all([routine_big, safety_low], now=now,
                        corridor_pressure={1: 0.9})
    for r in results:
        print(f"defect {r.defect_id} | tier {r.tier} | total {r.total}")
        for k, v in r.components.items():
            print(f"    {k:15} {v['value']:>5}  ({v['detail']})")

    assert results[0].defect_id == 1, "TIER WALL BREACHED: safety must rank first"
    print("TIER WALL HOLDS: severity-1 safety beats severity-5 overdue routine")
    print("SCORING SMOKE TEST OK")

