# backend/app/core/decision_engine.py
# Aligned with AIML/ml_sensor/decide.py -- loads the bundle's imputer,
# feature_columns, actions, weather_multipliers, obstruction_codes, and
# sensor_codes.  Falls back to the rule engine on any failure.
import logging
import time
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from app.core.incident_models import IncidentRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

AIML_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "AIML"
BUNDLE_PATH = AIML_ROOT / "ml_sensor" / "model" / "decision_model.joblib"
EVIDENCE_STATS_PATH = AIML_ROOT / "ml_sensor" / "model" / "evidence_stats.json"

# ---------------------------------------------------------------------------
# Physics constants (from AIML/ml_sensor/scenarios.py -- locked)
# ---------------------------------------------------------------------------

BRAKING_FORMULA_K = 2.0
SAFETY_MARGIN_KM = 0.3

WEATHER_MULTIPLIERS = {
    "clear": 1.0,
    "rain": 1.3,
    "fog": 1.1,
    "heavy_rain": 1.6,
    "snow": 1.9,
    "flood": 1.7,
}

OBSTRUCTION_TYPES = {
    "landslide_debris", "boulder", "track_buckling", "fallen_tree",
    "stranded_vehicle", "water_logging", "cattle_crossing", "broken_rail",
    "signal_cable_theft", "sensor_miscount", "environmental_false_positive",
    "unknown_obstruction", "equipment_failure_ahead",
}

SENSOR_TYPES = ("track_circuit", "axle_counter", "vibration", "accelerometer")

LONG_CLEARING_TYPES = frozenset(
    {"landslide_debris", "water_logging", "track_buckling",
     "broken_rail", "stranded_vehicle"})

BENIGN_TYPES = frozenset(
    {"cattle_crossing", "environmental_false_positive", "sensor_miscount"})
NEVER_DE_ESCALATE_TYPES = frozenset(
    {"broken_rail", "landslide_debris", "track_buckling"})

BENIGN_SIGNAL_QUALITY_MIN = 60.0
AXLE_IMBALANCE_THRESHOLD = 0.08

# Speed advisory constants (display-only, from AIML/ml_sensor/decide.py)
ADVISORY_MIN_KMH = 25.0
ADVISORY_COMFORT_FRACTION = 0.5
ADVISORY_SEV_FACTOR_MILD = 0.75
ADVISORY_SEV_FACTOR_SEVERE = 0.60

# Evidence constants (from AIML/ml_sensor/explain.py)
EVIDENCE_TOP_N = 6
EVIDENCE_BOOL_FEATURES = frozenset({
    "weather_alert", "alternative_route_available", "axle_balance_missing",
    "ahead_section_occupied", "known_train_schedule",
})
EVIDENCE_FEATURE_LABELS: dict[str, str] = {
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_weather(raw: str) -> Optional[str]:
    key = raw.strip().lower()
    if key in WEATHER_MULTIPLIERS:
        return key
    if key == "dry":
        return "clear"
    return None


def _physics_block(sc: dict) -> dict:
    speed = float(sc["train_speed_kmh"])
    dist = float(sc["distance_to_obstacle_km"])
    lat = float(sc["communication_latency_ms"])
    weather = sc["environmental_condition"]
    mult = WEATHER_MULTIPLIERS[weather]
    braking = (speed / 100.0) ** 2 * BRAKING_FORMULA_K * mult
    eff = dist - speed * (lat / 1000.0) / 3600.0
    return {
        "time_to_obstacle_min": round(dist / speed * 60.0 if speed > 0 else float("inf"), 2),
        "braking_distance_required_km": round(braking, 3),
        "effective_distance_km": round(eff, 3),
        "safe_stopping_possible": bool(eff > braking + SAFETY_MARGIN_KM),
        "weather_braking_multiplier": mult,
    }


def _speed_advisory(sc: dict, physics: dict) -> dict:
    speed = float(sc["train_speed_kmh"])
    sev = int(sc["severity_score"])
    mult = physics["weather_braking_multiplier"]
    eff = float(physics["effective_distance_km"])

    budget = ADVISORY_COMFORT_FRACTION * eff
    comfort = (100.0 * (budget / (2.0 * mult)) ** 0.5 if budget > 0 else 0.0)
    sev_factor = ADVISORY_SEV_FACTOR_MILD if sev <= 6 else ADVISORY_SEV_FACTOR_SEVERE
    target = min(comfort, speed * sev_factor, speed)
    target = int(target / 5.0) * 5

    if target < ADVISORY_MIN_KMH:
        return {"recommended_speed_kmh": None,
                "basis": f"no safe crawl speed above {ADVISORY_MIN_KMH:.0f} km/h -- treat as stop-worthy"}
    return {
        "recommended_speed_kmh": target,
        "basis": (f"braking at {target} km/h uses at most "
                  f"{int(ADVISORY_COMFORT_FRACTION * 100)}% of the remaining "
                  f"{eff:.2f} km; severity {sev}/10 caps prudence at "
                  f"{int(sev_factor * 100)}% of current speed"),
    }


# ---------------------------------------------------------------------------
# Rule engine (from AIML/ml_sensor/scenarios.py rule_engine_action)
# ---------------------------------------------------------------------------

def _rule_engine_action(sc: dict) -> str:
    speed = float(sc["train_speed_kmh"])
    dist = float(sc["distance_to_obstacle_km"])
    lat = float(sc["communication_latency_ms"])
    weather = sc["environmental_condition"]
    sev = int(sc["severity_score"])
    arb = bool(sc.get("alternative_route_available"))
    typ = str(sc["obstruction_type"])
    sig = float(sc["signal_quality_percent"])

    eff = dist - speed * (lat / 1000.0) / 3600.0
    braking = (speed / 100.0) ** 2 * BRAKING_FORMULA_K * WEATHER_MULTIPLIERS[weather]
    can_stop = eff > braking + SAFETY_MARGIN_KM

    if not can_stop:
        return "reroute" if arb else "emergency_stop"

    if sev >= 9:
        action = "emergency_stop"
    elif sev >= 7:
        action = "reroute" if (arb and typ in LONG_CLEARING_TYPES) else "reduce_speed"
    elif sev >= 5:
        action = "reduce_speed"
    else:
        calm = (typ in BENIGN_TYPES and sig >= BENIGN_SIGNAL_QUALITY_MIN
                and not bool(sc.get("weather_alert")))
        action = "proceed_with_caution" if calm else "reduce_speed"

    # trust gates
    if typ in BENIGN_TYPES:
        rank = {"proceed_with_caution": 0, "reduce_speed": 1, "reroute": 2, "emergency_stop": 3}
        if rank[action] > rank["reduce_speed"]:
            action = "reduce_speed"
    if typ in NEVER_DE_ESCALATE_TYPES:
        rank = {"proceed_with_caution": 0, "reduce_speed": 1, "reroute": 2, "emergency_stop": 3}
        if rank[action] < rank["reduce_speed"]:
            action = "reduce_speed"
    balance = sc.get("axle_balance")
    if (str(sc.get("sensor_type")) == "axle_counter" and balance is not None
            and abs(float(balance) - 1.0) > AXLE_IMBALANCE_THRESHOLD):
        rank = {"proceed_with_caution": 0, "reduce_speed": 1, "reroute": 2, "emergency_stop": 3}
        if rank[action] > rank["reduce_speed"]:
            action = "reduce_speed"

    return action


# ---------------------------------------------------------------------------
# Evidence helpers (from AIML/ml_sensor/explain.py)
# ---------------------------------------------------------------------------

def _fmt_input_evidence(f: str, v) -> str:
    """Format a feature value for human display in the evidence panel."""
    if f in EVIDENCE_BOOL_FEATURES:
        return "yes" if v >= 0.5 else "no"
    if f == "obstruction_type_code":
        return OBSTRUCTION_TYPES_LABELS.get(int(v), str(v))
    if f == "sensor_type_code":
        return SENSOR_TYPES_LABELS.get(int(v), str(v))
    if f == "environmental_braking_multiplier":
        inv = {v: k for k, v in WEATHER_MULTIPLIERS.items()}
        return inv.get(round(float(v), 2), f"{v:.2f}")
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


# Lookup tables for evidence formatting
OBSTRUCTION_TYPES_LABELS: dict[int, str] = {i: t for i, t in enumerate(
    ["landslide_debris", "boulder", "track_buckling", "fallen_tree",
     "stranded_vehicle", "water_logging", "cattle_crossing", "broken_rail",
     "signal_cable_theft", "sensor_miscount", "environmental_false_positive",
     "unknown_obstruction", "equipment_failure_ahead"])}
SENSOR_TYPES_LABELS: dict[int, str] = {i: s for i, s in enumerate(
    ["track_circuit", "axle_counter", "vibration", "accelerometer"])}


def _explain_decision(values: dict, action: str, probs: dict,
                      evidence_features: list[str],
                      evidence_stats: dict) -> Optional[dict]:
    """Build evidence panel for a model-source decision.

    Compares live input against class-conditional training stats.
    Returns None if there's nothing to compare.
    """
    if probs is None or len(probs) < 2 or evidence_stats is None:
        return None

    ranked = sorted(probs.items(), key=lambda kv: -kv[1])
    runner_up = ranked[1][0] if ranked[0][0] == action else ranked[0][0]
    runner_up_prob = ranked[1][1] if ranked[0][0] == action else ranked[0][1]
    pred_conf = probs.get(action, 0.0)

    features_list = evidence_stats.get("features", [])
    per_action = evidence_stats.get("per_action", {})

    top = [f for f in evidence_features
           if f in features_list and f in values][:EVIDENCE_TOP_N]
    entries = []
    for f in top:
        pred_feats = per_action.get(action, {}).get("features", {})
        ru_feats = per_action.get(runner_up, {}).get("features", {})
        ps = pred_feats.get(f)
        rs = ru_feats.get(f)
        if ps is None or f not in values or values[f] is None:
            continue
        label = EVIDENCE_FEATURE_LABELS.get(f, f)

        # Build human-readable comparison
        kind = ps["kind"]
        if kind == "num":
            reads = (f"{label}: input {_fmt_input_evidence(f, values[f])}; "
                     f"typical for {action} is {ps['mean']}")
            if rs and runner_up:
                reads += f", vs {rs['mean']} for {runner_up}"
        elif kind == "bool":
            p_pct = int(round(ps["share"] * 100))
            reads = (f"{label} was {'set' if values[f] >= 0.5 else 'not set'}; "
                     f"it is set in {p_pct}% of {action} training scenarios")
            if rs and runner_up:
                r_pct = int(round(rs["share"] * 100))
                reads += f" vs {r_pct}% for {runner_up}"
        else:
            reads = (f"{label}: input {_fmt_input_evidence(f, values[f])}; "
                     f"the most common type among {action} scenarios is "
                     f"{ps['top']} ({int(round(ps['share'] * 100))}%)")
            if rs and runner_up:
                reads += (f" (for {runner_up}: {rs['top']}, "
                          f"{int(round(rs['share'] * 100))}%)")

        entries.append({
            "feature": f,
            "label": label,
            "input": _fmt_input_evidence(f, values[f]),
            "predicted_action": action,
            "predicted_typical": (ps["mean"] if ps["kind"] == "num"
                                  else ps.get("top") or
                                  f"{int(round(ps['share'] * 100))}%"),
            "runner_up_action": runner_up,
            "runner_up_typical": (rs["mean"] if rs and rs["kind"] == "num"
                                  else (rs.get("top") if rs else None)),
            "reads": reads,
        })

    return {
        "summary": (f"model chose '{action}' at "
                    f"{round(pred_conf * 100, 2)}% -- runner-up "
                    f"'{runner_up}' at {round(runner_up_prob * 100, 2)}%; "
                    f"evidence compares this incident against what each "
                    f"action's training scenarios looked like"),
        "features": entries,
    }


# ---------------------------------------------------------------------------
# DecisionEngine
# ---------------------------------------------------------------------------

class DecisionEngine:
    """Stateless, thread-safe decision engine aligned with the AIML bundle."""

    def __init__(self, bundle_path: Path = BUNDLE_PATH):
        self.bundle = None
        self.model = None
        self.feature_columns: list[str] = []
        self.confidence_floor: float = 0.55
        self.actions: list[str] = []
        self.evidence_features: list[str] = []
        self.evidence_stats: Optional[dict] = None
        self._load_model(bundle_path)

    def _load_model(self, bundle_path: Path):
        if not bundle_path.exists():
            logger.warning("ML model not found at %s -- rule-based fallback only", bundle_path)
            return
        try:
            self.bundle = joblib.load(str(bundle_path))
            self.model = self.bundle["model"]
            self.feature_columns = list(self.bundle["feature_columns"])
            self.confidence_floor = float(self.bundle.get("confidence_floor", 0.55))
            self.actions = list(self.bundle["actions"])
            imps = self.bundle.get("test_metrics", {}).get("importances") or []
            self.evidence_features = [i["feature"] for i in imps
                                      if i["feature"] in self.feature_columns][:6]
            logger.info("ML model loaded: %s (confidence_floor=%s, features=%d)",
                        self.bundle.get("model_name", "?"),
                        self.confidence_floor, len(self.feature_columns))
            self._load_evidence_stats()
        except Exception as exc:
            logger.error("Failed to load ML model: %s", exc)
            self.bundle = None

    def _load_evidence_stats(self):
        """Load pre-computed class-conditional stats for evidence panel."""
        if not EVIDENCE_STATS_PATH.exists():
            logger.warning("Evidence stats not found at %s", EVIDENCE_STATS_PATH)
            return
        try:
            self.evidence_stats = json.loads(EVIDENCE_STATS_PATH.read_text())
            logger.info("Evidence stats loaded: %d features, %d actions",
                        len(self.evidence_stats.get("features", [])),
                        len(self.evidence_stats.get("per_action", {})))
        except Exception as exc:
            logger.warning("Failed to load evidence stats: %s", exc)

    # -- validation + normalization ------------------------------------------

    def _validate(self, request: IncidentRequest) -> dict:
        sc = {
            "train_speed_kmh": float(request.train_speed_kmh),
            "distance_to_obstacle_km": float(request.distance_to_obstacle_km),
            "environmental_condition": request.environmental_condition,
            "weather_alert": request.weather_alert,
            "signal_quality_percent": float(request.signal_quality_percent),
            "severity_score": int(request.severity_score),
            "obstruction_type": request.obstruction_type,
            "alternative_route_available": request.alternative_route_available,
            "communication_latency_ms": float(request.communication_latency_ms),
            "axle_balance": request.axle_balance,
            "ahead_section_status": request.ahead_section_status.upper(),
            "known_train_schedule": request.known_train_schedule,
            "distance_from_station_km": float(request.distance_from_station_km),
            "sensor_type": request.sensor_type,
        }
        weather = _normalize_weather(sc["environmental_condition"])
        if weather is None:
            raise ValueError(f"unknown environmental_condition: {sc['environmental_condition']!r}")
        sc["environmental_condition"] = weather
        return sc

    # -- 16-feature row (matches bundle's feature_columns) -------------------

    def _feature_row(self, sc: dict) -> tuple[pd.DataFrame, dict]:
        weather = str(sc["environmental_condition"])
        typ = str(sc["obstruction_type"])
        sensor = str(sc["sensor_type"])
        speed = float(sc["train_speed_kmh"])
        dist = float(sc["distance_to_obstacle_km"])
        balance = sc.get("axle_balance")
        balance = float(balance) if balance is not None else None

        values = {
            "train_speed_kmh": speed,
            "distance_to_obstacle_km": dist,
            "time_to_obstacle_min": dist / speed * 60.0 if speed > 0 else float("inf"),
            "environmental_braking_multiplier": float(self.bundle["weather_multipliers"][weather]),
            "weather_alert": 1.0 if sc.get("weather_alert") else 0.0,
            "signal_quality_percent": float(sc["signal_quality_percent"]),
            "severity_score": float(sc["severity_score"]),
            "obstruction_type_code": float(self.bundle["obstruction_codes"][typ]),
            "alternative_route_available": 1.0 if sc.get("alternative_route_available") else 0.0,
            "communication_latency_ms": float(sc["communication_latency_ms"]),
            "axle_balance": balance,
            "axle_balance_missing": 1.0 if balance is None else 0.0,
            "ahead_section_occupied": 1.0 if sc["ahead_section_status"] == "OCCUPIED" else 0.0,
            "known_train_schedule": 1.0 if sc.get("known_train_schedule") else 0.0,
            "distance_from_station_km": float(sc["distance_from_station_km"]),
            "sensor_type_code": float(self.bundle["sensor_codes"][sensor]),
        }
        X = pd.DataFrame([values], columns=self.feature_columns)
        X = X.apply(pd.to_numeric, errors="raise").astype(float)
        return X, values

    # -- assemble output -----------------------------------------------------

    def _assemble(self, sc: dict, physics: dict, action: str,
                  confidence: Optional[float], source: str,
                  probabilities: Optional[dict], reasons: list[str],
                  t0: float, evidence: Optional[dict] = None) -> dict:
        if action == "reduce_speed":
            adv = _speed_advisory(sc, physics)
            physics = {**physics, "speed_advisory": adv}
            if adv["recommended_speed_kmh"] is not None:
                reasons = reasons + [
                    f"Speed advisory: reduce to {adv['recommended_speed_kmh']} km/h "
                    f"(display-only, physics + severity based)."]
            else:
                reasons = reasons + ["Speed advisory: " + adv["basis"]]

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "action": action,
            "confidence": confidence,
            "source": source,
            "reasons": reasons,
            "physics": physics,
            "probabilities": probabilities,
            "evidence": evidence,
            "decision_latency_ms": latency_ms,
            "within_100ms_budget": latency_ms < 100.0,
        }

    # -- the decision --------------------------------------------------------

    def decide(self, request: IncidentRequest) -> dict:
        t0 = time.perf_counter()
        sc = self._validate(request)
        physics = _physics_block(sc)

        # R1 hard safety rule (before model -- a wall, not a suggestion)
        r1_fires = (
            int(sc["severity_score"]) >= 9
            and not physics["safe_stopping_possible"]
            and not bool(sc.get("alternative_route_available"))
        )
        if r1_fires:
            return self._assemble(
                sc, physics,
                action="emergency_stop", confidence=1.0,
                source="hard_rule", probabilities=None,
                reasons=[
                    "R1 hard safety rule fired: severity >= 9, train "
                    "cannot stop within available distance, and no "
                    "alternate route exists.",
                    f"Effective distance {physics['effective_distance_km']} km vs "
                    f"braking requirement {physics['braking_distance_required_km']} km "
                    f"+ {SAFETY_MARGIN_KM} km safety margin.",
                    "Emergency stop enforced by rule; ML model was not "
                    "consulted (locked decision 9).",
                ],
                t0=t0,
            )

        # ML inference
        if self.model is not None:
            try:
                X, values = self._feature_row(sc)
                X_i = self.bundle["imputer"].transform(X)
                codes = self.model.predict(X_i)
                action_code = int(np.asarray(codes).ravel()[0])
                action = self.actions[action_code]

                proba = np.asarray(self.model.predict_proba(X_i)).ravel()
                classes = list(np.asarray(self.model.classes_).ravel())
                probs = {self.actions[int(c)]: float(p)
                         for c, p in zip(classes, proba)}
                confidence = float(probs[action])

                if confidence < self.confidence_floor:
                    rule_action = _rule_engine_action(sc)
                    return self._assemble(
                        sc, physics,
                        action=rule_action,
                        confidence=round(confidence, 4),
                        source="rule_fallback",
                        probabilities={a: round(p, 4) for a, p in probs.items()},
                        reasons=[
                            f"Model confidence {confidence:.4f} is below the "
                            f"{self.confidence_floor} floor (R2).",
                            f"Model leaned toward '{action}' but was not "
                            "confident enough to own the decision.",
                            f"Rule-engine answer '{rule_action}' returned "
                            "instead (locked decision 9: R2).",
                        ],
                        t0=t0,
                    )

                return self._assemble(
                    sc, physics,
                    action=action,
                    confidence=round(confidence, 4),
                    source="model",
                    probabilities={a: round(p, 4) for a, p in probs.items()},
                    reasons=[
                        f"Trained decision model ({self.bundle.get('model_name', 'XGBoost')}) "
                        f"predicted '{action}' with confidence {confidence:.4f} "
                        f"(above the {self.confidence_floor} floor).",
                        f"Key drivers: severity {int(sc['severity_score'])}, "
                        f"alternate route "
                        f"{'available' if sc.get('alternative_route_available') else 'not available'}, "
                        f"weather '{sc['environmental_condition']}', "
                        f"time-to-obstacle {physics['time_to_obstacle_min']} min.",
                        "R1 did not fire (scenario is in the gray zone the "
                        "model is licensed to decide).",
                    ],
                    t0=t0,
                    evidence=_explain_decision(
                        values, action,
                        {a: round(p, 4) for a, p in probs.items()},
                        self.evidence_features, self.evidence_stats),
                )

            except Exception as exc:
                logger.error("ML inference failed: %s", exc)
                # fall through to rule fallback below

        # Rule fallback (model unavailable or failed)
        rule_action = _rule_engine_action(sc)
        return self._assemble(
            sc, physics,
            action=rule_action, confidence=None,
            source="rule_fallback", probabilities=None,
            reasons=[
                f"Rule-engine answer '{rule_action}' returned "
                + ("(ML model not loaded)" if self.model is None
                   else "(ML inference failed, safe degradation)."),
            ],
            t0=t0,
        )


# singleton
decision_engine = DecisionEngine()
