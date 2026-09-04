"""
ml_sensor/decide.py -- the LIVE decision engine.

Step 3 of 7. Locked decision 9 is the whole design:

  R1 (hard rule): severity >= 9 AND cannot stop AND no alternate route
      -> emergency_stop. The MODEL IS NEVER CONSULTED.
  R2 (confidence leash): model confidence < 0.55 -> rule-engine answer.

Order of operations: normalize -> physics -> R1 (before the model) ->
model -> R2 -> assemble. R1 is a wall, not a suggestion.

v2 -- SPEED ADVISORY: display-only recommended speed on reduce_speed
  (physics + severity based; never a model feature; vocabulary stays 4).

v3 -- EVIDENCE (owner request): model-source decisions now carry an
  'evidence' block -- the input's feature values compared against the
  class-conditional stats of the predicted action vs the runner-up,
  over the model's own top-important features. Built by
  ml_sensor/explain.py from the seeded dataset, cached, artifact-
  persisted. Microseconds per request (stats are precomputed).
  hard_rule: evidence is None (no model to explain). rule_fallback:
  evidence is None (the reasons already tell that story).

Serving discipline: matrix rebuilt FROM THE BUNDLE, predictions decode
through classes_, missing/corrupt model degrades LOUD and SAFE.

Run:  python -m ml_sensor.decide

Layer rules: pure Python + joblib + numpy + pandas. No fastapi, no
sqlmodel.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml_sensor.explain import explain_decision, get_stats
from ml_sensor.scenarios import (DEMO_ANCHOR, OBSTRUCTION_TYPES,
                                  SENSOR_TYPES, normalize_weather,
                                  physics_block, rule_engine_action)

BUNDLE_PATH = Path("ml_sensor/model/decision_model.joblib")

SOURCE_HARD_RULE = "hard_rule"
SOURCE_MODEL = "model"
SOURCE_RULE_FALLBACK = "rule_fallback"

DECISION_BUDGET_MS = 100.0

# --- v2: speed advisory constants (owner-tunable, display-only) ---
ADVISORY_MIN_KMH = 25.0
ADVISORY_COMFORT_FRACTION = 0.5
ADVISORY_SEV_FACTOR_MILD = 0.75    # severity <= 6
ADVISORY_SEV_FACTOR_SEVERE = 0.60  # severity 7-8


def speed_advisory(sc: dict, physics: dict) -> dict:
    """DISPLAY-ONLY recommended speed for reduce_speed decisions.
    Two factors, most conservative wins; see module docstring (v2)."""
    speed = float(sc["train_speed_kmh"])
    weather = str(sc["environmental_condition"])
    mult = physics["weather_braking_multiplier"]
    eff = float(physics["effective_distance_km"])
    sev = int(sc["severity_score"])

    budget = ADVISORY_COMFORT_FRACTION * eff
    comfort = (100.0 * (budget / (2.0 * mult)) ** 0.5
               if budget > 0 else 0.0)

    sev_factor = (ADVISORY_SEV_FACTOR_MILD if sev <= 6
                  else ADVISORY_SEV_FACTOR_SEVERE)
    severity_cap = speed * sev_factor

    target = min(comfort, severity_cap, speed)
    target = int(target / 5.0) * 5

    if target < ADVISORY_MIN_KMH:
        return {
            "recommended_speed_kmh": None,
            "basis": (f"no safe crawl speed above "
                      f"{ADVISORY_MIN_KMH:.0f} km/h -- treat as "
                      "stop-worthy"),
        }
    return {
        "recommended_speed_kmh": target,
        "basis": (f"braking at {target} km/h uses at most "
                  f"{int(ADVISORY_COMFORT_FRACTION * 100)}% of the "
                  f"remaining {eff:.2f} km (sensor-error headroom); "
                  f"severity {sev}/10 caps prudence at "
                  f"{int(sev_factor * 100)}% of current speed"),
    }


class DecisionEngine:
    """Stateless, thread-safe decision engine."""

    def __init__(self, bundle_path: Path | str = BUNDLE_PATH,
                 bundle: dict | None = None,
                 model=None):
        if bundle is not None:
            self.bundle = bundle
        else:
            path = Path(bundle_path)
            if not path.exists():
                raise FileNotFoundError(
                    f"no trained model at {path} -- run: "
                    f"python -m ml_sensor.train"
                )
            self.bundle = joblib.load(path)
        self.model = model if model is not None else self.bundle["model"]
        self.feature_columns: list[str] = list(self.bundle["feature_columns"])
        self.confidence_floor: float = float(self.bundle["confidence_floor"])
        self.actions: list[str] = list(self.bundle["actions"])
        # v3: the model's own top-important features drive the evidence
        # panel (its attention, not our guesses).
        imps = (self.bundle.get("test_metrics", {})
                .get("importances") or [])
        self.evidence_features = [i["feature"] for i in imps
                                  if i["feature"] in self.feature_columns][:6]
        # v3: warm the evidence stats at construction (boot time), so
        # the first live decision never pays the build cost. A stats
        # failure must NEVER break decisions -- evidence is optional.
        try:
            get_stats()
        except Exception:  # noqa: BLE001
            pass

    # -- validation + normalization at the boundary ----------------

    def _validate(self, incident: dict) -> dict:
        sc = dict(incident)
        weather = normalize_weather(str(sc["environmental_condition"]))
        if weather is None:
            raise ValueError(
                f"unknown environmental_condition: "
                f"{sc['environmental_condition']!r}")
        sc["environmental_condition"] = weather

        if str(sc["obstruction_type"]) not in OBSTRUCTION_TYPES:
            raise ValueError(
                f"unknown obstruction_type: {sc['obstruction_type']!r}")
        if str(sc["sensor_type"]) not in SENSOR_TYPES:
            raise ValueError(f"unknown sensor_type: {sc['sensor_type']!r}")
        if str(sc["ahead_section_status"]).upper() not in ("OCCUPIED", "CLEAR"):
            raise ValueError(
                f"unknown ahead_section_status: "
                f"{sc['ahead_section_status']!r}")
        sc["ahead_section_status"] = str(sc["ahead_section_status"]).upper()
        return sc

    # -- feature matrix from the bundle (v3: also returns values) ----

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
            "environmental_braking_multiplier":
                float(self.bundle["weather_multipliers"][weather]),
            "weather_alert": 1.0 if sc.get("weather_alert") else 0.0,
            "signal_quality_percent": float(sc["signal_quality_percent"]),
            "severity_score": float(sc["severity_score"]),
            "obstruction_type_code":
                float(self.bundle["obstruction_codes"][typ]),
            "alternative_route_available":
                1.0 if sc.get("alternative_route_available") else 0.0,
            "communication_latency_ms": float(sc["communication_latency_ms"]),
            "axle_balance": balance,
            "axle_balance_missing": 1.0 if balance is None else 0.0,
            "ahead_section_occupied":
                1.0 if sc["ahead_section_status"] == "OCCUPIED" else 0.0,
            "known_train_schedule": 1.0 if sc.get("known_train_schedule") else 0.0,
            "distance_from_station_km": float(sc["distance_from_station_km"]),
            "sensor_type_code": float(self.bundle["sensor_codes"][sensor]),
        }
        X = pd.DataFrame([values], columns=self.feature_columns)
        X = X.apply(pd.to_numeric, errors="raise").astype(float)
        return X, values

    # -- the decision ------------------------------------------------

    def decide(self, incident: dict) -> dict:
        t0 = time.perf_counter()

        sc = self._validate(incident)
        physics = physics_block(sc)

        r1_fires = (
            int(sc["severity_score"]) >= 9
            and not physics["safe_stopping_possible"]
            and not bool(sc.get("alternative_route_available"))
        )
        if r1_fires:
            return self._assemble(
                sc, physics,
                action="emergency_stop",
                confidence=1.0,
                source=SOURCE_HARD_RULE,
                probabilities=None,
                reasons=[
                    "R1 hard safety rule fired: severity >= 9, train "
                    "cannot stop within available distance, and no "
                    "alternate route exists.",
                    f"Effective distance {physics['effective_distance_km']} km "
                    f"vs braking requirement "
                    f"{physics['braking_distance_required_km']} km + "
                    f"0.3 km safety margin.",
                    "Emergency stop enforced by rule; ML model was not "
                    "consulted (locked decision 9).",
                ],
                t0=t0,
            )

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
                rule_action = rule_engine_action(sc)
                return self._assemble(
                    sc, physics,
                    action=rule_action,
                    confidence=round(confidence, 4),
                    source=SOURCE_RULE_FALLBACK,
                    probabilities={a: round(p, 4) for a, p in probs.items()},
                    reasons=[
                        f"Model confidence {confidence:.4f} is below the "
                        f"{self.confidence_floor} floor (R2).",
                        f"Model leaned toward '{action}' but was not "
                        f"confident enough to own the decision.",
                        f"Rule-engine answer '{rule_action}' returned "
                        f"instead (locked decision 9: R2).",
                    ],
                    t0=t0,
                )

            # v3: numeric evidence -- only the model's own answer gets
            # explained with numbers; failures here must never break
            # the decision.
            evidence = None
            try:
                evidence = explain_decision(
                    values, action,
                    {a: round(p, 4) for a, p in probs.items()},
                    self.evidence_features)
            except Exception:  # noqa: BLE001
                evidence = None

            return self._assemble(
                sc, physics,
                action=action,
                confidence=round(confidence, 4),
                source=SOURCE_MODEL,
                probabilities={a: round(p, 4) for a, p in probs.items()},
                reasons=[
                    f"Trained decision model ({self.bundle['model_name']}) "
                    f"predicted '{action}' with confidence "
                    f"{confidence:.4f} (above the {self.confidence_floor} "
                    f"floor).",
                    f"Key drivers: severity {int(sc['severity_score'])}, "
                    f"alternate route "
                    f"{'available' if sc.get('alternative_route_available') else 'not available'}, "
                    f"weather '{sc['environmental_condition']}', "
                    f"time-to-obstacle "
                    f"{physics['time_to_obstacle_min']} min.",
                    "R1 did not fire (scenario is in the gray zone the "
                    "model is licensed to decide).",
                ],
                t0=t0,
                evidence=evidence,
            )

        except Exception as exc:  # noqa: BLE001
            rule_action = rule_engine_action(sc)
            return self._assemble(
                sc, physics,
                action=rule_action,
                confidence=None,
                source=SOURCE_RULE_FALLBACK,
                probabilities=None,
                reasons=[
                    f"Decision model failed at runtime: "
                    f"{type(exc).__name__}: {exc}",
                    f"Rule-engine answer '{rule_action}' returned "
                    f"instead (safe degradation).",
                ],
                t0=t0,
            )

    # -- output assembly (v2 advisory + v3 evidence) ------------------

    def _assemble(self, sc: dict, physics: dict, action: str,
                  confidence: float | None, source: str,
                  probabilities: dict | None, reasons: list[str],
                  t0: float, evidence: dict | None = None) -> dict:
        if action == "reduce_speed":
            adv = speed_advisory(sc, physics)
            physics = {**physics, "speed_advisory": adv}
            if adv["recommended_speed_kmh"] is not None:
                reasons = reasons + [
                    f"Speed advisory: reduce to "
                    f"{adv['recommended_speed_kmh']} km/h "
                    f"(display-only, physics + severity based)."
                ]
            else:
                reasons = reasons + [
                    "Speed advisory: " + adv["basis"],
                ]

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
            "within_100ms_budget": latency_ms < DECISION_BUDGET_MS,
        }


# =====================================================================
# CLI
# =====================================================================

def main() -> None:
    engine = DecisionEngine()
    print("=== RailGuard DecisionEngine -- demo anchor ===")
    print(f"model: {engine.bundle['model_name']} | "
          f"confidence floor: {engine.confidence_floor} | "
          f"features: {len(engine.feature_columns)}")
    decision = engine.decide(DEMO_ANCHOR)
    print("\nDecision (watch evidence + reasons):")
    print(json.dumps(decision, indent=2))
    ok = decision["action"] == "emergency_stop"
    print(f"\nanchor invariant (action == emergency_stop): "
          f"{'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()

