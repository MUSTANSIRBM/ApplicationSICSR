"""
ml_sensor/explain.py -- per-decision evidence: WHY the model chose this.

The 'reasons' list in a decision is narrative. This module adds the
NUMBERS: for the predicted action and the runner-up, it compares the
live input's feature values against what each action's training
scenarios actually looked like (class-conditional means / shares).

  "severity_score: input 9; emergency_stop training avg 8.6,
   reduce_speed avg 5.2"

Method: plain class statistics over the seeded 4,000-scenario dataset
(deterministic, seed 42). No SHAP, no new dependencies, no network.
Stats are computed once, cached in memory, and persisted as
ml_sensor/model/evidence_stats.json -- the artifact is the contract,
same discipline as the joblib bundle.

Layer rules: pure Python + statistics/collections. No fastapi, no
sqlmodel. Attached only to model-source decisions (hard_rule has no
model to explain; rule_fallback's reasons already tell that story).

Run:  python -m ml_sensor.explain   -> (re)builds the stats artifact
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev

from ml_sensor.scenarios import (ACTIONS, FEATURE_COLUMNS, N_SCENARIOS,
                                  OBSTRUCTION_CODES, SEED, SENSOR_CODES,
                                  WEATHER_MULTIPLIERS, build_dataset,
                                  encode_features)

STATS_PATH = Path("ml_sensor/model/evidence_stats.json")
TOP_N = 6          # how many features appear in the evidence panel

CODE_INVERSE: dict[str, dict[int, str]] = {
    "obstruction_type_code": {v: k for k, v in OBSTRUCTION_CODES.items()},
    "sensor_type_code": {v: k for k, v in SENSOR_CODES.items()},
}
WEATHER_INVERSE: dict[float, str] = {
    v: k for k, v in WEATHER_MULTIPLIERS.items()
}
BOOL_FEATURES = frozenset({
    "weather_alert", "alternative_route_available", "axle_balance_missing",
    "ahead_section_occupied", "known_train_schedule",
})
# human-readable labels for the panel
FEATURE_LABELS: dict[str, str] = {
    "train_speed_kmh": "train speed",
    "distance_to_obstacle_km": "distance to obstacle",
    "time_to_obstacle_min": "time to obstacle",
    "environmental_braking_multiplier": "weather (braking effect)",
    "weather_alert": "weather alert active",
    "signal_quality_percent": "signal quality",
    "severity_score": "severity",
    "obstruction_type_code": "obstruction type",
    "alternative_route_available": "alternate route available",
    "communication_latency_ms": "communication latency",
    "axle_balance": "axle balance",
    "axle_balance_missing": "axle balance missing",
    "ahead_section_occupied": "ahead section occupied",
    "known_train_schedule": "known train schedule",
    "distance_from_station_km": "distance from station",
    "sensor_type_code": "sensor type",
}

_stats_cache: dict | None = None


# =====================================================================
# Stats building (offline, deterministic)
# =====================================================================

def build_stats(n: int = N_SCENARIOS, seed: int = SEED) -> dict:
    """Class-conditional feature stats over the training dataset.
    Deterministic: same seed -> identical artifact."""
    data = build_dataset(n, seed)
    rows = [encode_features(sc) for sc in data]

    per_action: dict[str, dict] = {}
    for action in ACTIONS:
        sub = [r for r, sc in zip(rows, data) if sc["label"] == action]
        feats: dict[str, dict] = {}
        for f in FEATURE_COLUMNS:
            vals = [r[f] for r in sub if r[f] is not None]
            if f in CODE_INVERSE:
                top_code, cnt = Counter(vals).most_common(1)[0]
                feats[f] = {
                    "kind": "code",
                    "top": CODE_INVERSE[f][int(top_code)],
                    "share": round(cnt / len(vals), 3),
                }
            elif f in BOOL_FEATURES:
                feats[f] = {
                    "kind": "bool",
                    "share": round(mean(vals), 3),
                }
            else:
                feats[f] = {
                    "kind": "num",
                    "mean": round(mean(vals), 2),
                    "std": round(pstdev(vals), 2) if len(vals) > 1 else 0.0,
                }
        per_action[action] = {"n": len(sub), "features": feats}
    return {"features": list(FEATURE_COLUMNS), "per_action": per_action}


def get_stats() -> dict:
    """Load-or-build, cached in memory for the process lifetime."""
    global _stats_cache
    if _stats_cache is None:
        if STATS_PATH.exists():
            _stats_cache = json.loads(STATS_PATH.read_text())
        else:
            _stats_cache = build_stats()
            STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATS_PATH.write_text(json.dumps(_stats_cache, indent=2))
    return _stats_cache


# =====================================================================
# Per-decision evidence
# =====================================================================

def _fmt_input(f: str, v) -> str:
    if f in BOOL_FEATURES:
        return "yes" if v >= 0.5 else "no"
    if f in CODE_INVERSE:
        return CODE_INVERSE[f][int(v)]
    if f == "environmental_braking_multiplier":
        return WEATHER_INVERSE.get(round(float(v), 2), f"{v:.2f}")
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def _reads(f: str, label: str, input_v, pred_stats: dict,
           action: str, ru_stats: dict | None,
           runner_up: str | None) -> str:
    kind = pred_stats["kind"]
    if kind == "num":
        left = (f"{label}: input {_fmt_input(f, input_v)}; typical for "
                f"{action} is {pred_stats['mean']}")
        right = (f", vs {ru_stats['mean']} for {runner_up}"
                 if ru_stats and runner_up else "")
        return left + right
    if kind == "bool":
        p_pct = int(round(pred_stats["share"] * 100))
        r_pct = (int(round(ru_stats["share"] * 100))
                 if ru_stats else None)
        left = (f"{label} was {'set' if input_v >= 0.5 else 'not set'}; "
                f"it is set in {p_pct}% of {action} training scenarios")
        right = (f" vs {r_pct}% for {runner_up}"
                 if r_pct is not None and runner_up else "")
        return left + right
    # code
    left = (f"{label}: input {_fmt_input(f, input_v)}; the most common "
            f"type among {action} scenarios is {pred_stats['top']} "
            f"({int(round(pred_stats['share'] * 100))}%)")
    right = (f" (for {runner_up}: {ru_stats['top']}, "
             f"{int(round(ru_stats['share'] * 100))}%)"
             if ru_stats and runner_up else "")
    return left + right


def explain_decision(values: dict, action: str, probs: dict | None,
                     top_features: list[str]) -> dict | None:
    """Build the evidence panel for a model-source decision.

    values: the ENCODED feature dict for this incident (from the
    engine's feature row). top_features: the winner model's most
    important features (from the bundle) -- evidence follows the
    model's own attention, not our guesses.
    Returns None if there's nothing to compare against.
    """
    if probs is None or len(probs) < 2:
        return None
    stats = get_stats()
    ranked = sorted(probs.items(), key=lambda kv: -kv[1])
    runner_up, ru_prob = ranked[1] if ranked[0][0] == action else ranked[0]
    # (if the top prob is somehow not the action, treat second as runner)
    if ranked[0][0] != action:
        runner_up, ru_prob = ranked[0]
    pred_conf = probs.get(action, 0.0)

    features = [f for f in top_features
                if f in stats["features"] and f in values][:TOP_N]
    entries = []
    for f in features:
        pred_feats = stats["per_action"].get(action, {}).get("features", {})
        ru_feats = (stats["per_action"].get(runner_up, {})
                    .get("features", {}))
        ps = pred_feats.get(f)
        rs = ru_feats.get(f)
        if ps is None or f not in values or values[f] is None:
            continue
        label = FEATURE_LABELS.get(f, f)
        entries.append({
            "feature": f,
            "label": label,
            "input": _fmt_input(f, values[f]),
            "predicted_action": action,
            "predicted_typical": (ps["mean"] if ps["kind"] == "num"
                                  else ps.get("top") or
                                  f"{int(round(ps['share'] * 100))}%"),
            "runner_up_action": runner_up,
            "runner_up_typical": (rs["mean"] if rs and rs["kind"] == "num"
                                  else (rs.get("top") if rs else None)),
            "reads": _reads(f, label, values[f], ps, action, rs, runner_up),
        })

    return {
        "summary": (f"model chose '{action}' at "
                    f"{round(pred_conf * 100, 2)}% -- runner-up "
                    f"'{runner_up}' at {round(ru_prob * 100, 2)}%; evidence "
                    f"compares this incident against what each action's "
                    f"training scenarios looked like"),
        "features": entries,
    }


# =====================================================================
# CLI: (re)build the stats artifact
# =====================================================================

def main() -> None:
    stats = build_stats()
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(json.dumps(stats, indent=2))
    print(f"wrote {STATS_PATH}")
    for a in ACTIONS:
        n = stats["per_action"][a]["n"]
        sev = stats["per_action"][a]["features"]["severity_score"]
        print(f"  {a:<22} n={n:<5} typical severity {sev['mean']}")


if __name__ == "__main__":
    main()

