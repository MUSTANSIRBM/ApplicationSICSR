"""
ml_sensor/decide.py -- the LIVE decision engine.

Step 3 of 7. This is the piece that runs in seconds when a train is
closing on an obstruction. Locked decision 9 is the whole design:

  R1 (hard rule): severity >= 9 AND cannot stop AND no alternate route
      -> emergency_stop. The MODEL IS NEVER CONSULTED. Physics owns
      the black zones.
  R2 (confidence leash): model confidence < 0.55 -> rule-engine answer
      instead. ML owns the gray zones, on a leash.

Order of operations matters more than anything else in this file:
  normalize -> physics -> R1 (before the model) -> model -> R2 ->
  assemble. If the R2 check ever runs before R1, the model could see
  a catastrophic case -- R1 is a wall, not a suggestion.

Serving discipline:
  - the feature matrix is rebuilt FROM THE BUNDLE (column order, code
    maps, weather multipliers, imputer, confidence floor) -- never
    from memory. train/serve drift is structurally impossible here.
  - this module loads the joblib file directly; it NEVER imports
    train.py, so the live path drags in zero training machinery.
  - predictions decode through the model's own classes_ order --
    predict_proba columns are never assumed alphabetical or
    index-ordered.
  - if the model raises or the bundle is missing, the engine degrades
    to the rule engine (source: rule_fallback) with the failure in
    the reasons. A live safety component fails LOUD and SAFE, never
    silent.

Output contract (what the API returns, what the frontend renders --
locked decision 12: frontend displays physics, never sends it back):
  action, confidence, source, reasons (data structure, rendered never
  recomputed), physics block, probabilities, decision_latency_ms.

Run:  python -m ml_sensor.decide   -> runs the demo anchor, prints JSON

Layer rules: pure Python + joblib + numpy + pandas. No fastapi, no
sqlmodel. Unknown weather/type/sensor raises ValueError; the API layer
turns that into a 422 -- never a silent guess.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml_sensor.scenarios import (ACTIONS, DEMO_ANCHOR, OBSTRUCTION_TYPES,
                                  SENSOR_TYPES, normalize_weather,
                                  physics_block, rule_engine_action,
                                  safe_stopping_possible)

BUNDLE_PATH = Path("ml_sensor/model/decision_model.joblib")

# Sources, in escalation-of-authority order. Exactly three -- this is
# the "source" field of every decision.
SOURCE_HARD_RULE = "hard_rule"          # R1: physics decided
SOURCE_MODEL = "model"                  # gray zone, confident
SOURCE_RULE_FALLBACK = "rule_fallback"  # R2 low confidence, or model failure

# Sub-100ms is a design requirement, not a hope. This budget only
# measures engine time (validation to answer); network/serialization
# belong to the API layer, and the API reports its own number.
DECISION_BUDGET_MS = 100.0


class DecisionEngine:
    """Stateless, thread-safe decision engine. One instance can serve
    many requests (the planner API runs the same pattern)."""

    def __init__(self, bundle_path: Path | str = BUNDLE_PATH,
                 bundle: dict | None = None,
                 model=None):
        """bundle: pre-loaded bundle (tests). model: an object with
        .predict / .predict_proba (tests use a spy to prove R1 never
        consults the model). Both None -> load from disk."""
        if bundle is not None:
            self.bundle = bundle
        else:
            path = Path(bundle_path)
            if not path.exists():
                # Missing model is a boot problem, not a request
                # problem: raise loudly. api/main.py self-heals by
                # training; this module never trains on its own.
                raise FileNotFoundError(
                    f"no trained model at {path} -- run: "
                    f"python -m ml_sensor.train"
                )
            self.bundle = joblib.load(path)
        # The live model. Injected spy overrides the bundled one
        # WITHOUT touching the rest of the contract (imputer, floors,
        # code maps stay real) -- that is what makes the R1 test an
        # honest spy rather than a strawman.
        self.model = model if model is not None else self.bundle["model"]
        self.feature_columns: list[str] = list(self.bundle["feature_columns"])
        self.confidence_floor: float = float(self.bundle["confidence_floor"])
        self.actions: list[str] = list(self.bundle["actions"])

    # -----------------------------------------------------------------
    # Validation + normalization at the boundary
    # -----------------------------------------------------------------

    def _validate(self, incident: dict) -> dict:
        """Strict boundary checks. Returns a NORMALIZED copy: weather
        'dry' -> 'clear' (locked), everything else must already be in
        vocabulary or we raise. Unknown obstruction type / sensor /
        weather is a 422 upstream -- we never guess."""
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

    # -----------------------------------------------------------------
    # Feature matrix: rebuilt FROM THE BUNDLE, never from memory
    # -----------------------------------------------------------------

    def _feature_row(self, sc: dict) -> pd.DataFrame:
        """One scenario -> 1x16 float DataFrame in the bundle's column
        order, using the bundle's code maps and weather multipliers.
        If scenarios.py constants ever drift from a trained bundle, the
        bundle wins -- the artifact is the contract."""
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
        return X

    # -----------------------------------------------------------------
    # The decision
    # -----------------------------------------------------------------

    def decide(self, incident: dict) -> dict:
        """Incident in -> full decision out. Raises ValueError on junk
        input (API -> 422). Everything else degrades safely."""
        t0 = time.perf_counter()

        # 1) boundary: normalize + strict validation
        sc = self._validate(incident)

        # 2) physics block (display + R1 inputs). Computed here, shown
        #    to the frontend, NEVER fed back as a model feature.
        physics = physics_block(sc)

        # 3) R1 -- the wall. Model never consulted past this point if
        #    it fires. (severity>=9 AND can't stop AND no alternate.)
        r1_fires = (
            int(sc["severity_score"]) >= 9
            and not physics["safe_stopping_possible"]
            and not bool(sc.get("alternative_route_available"))
        )
        if r1_fires:
            result = self._assemble(
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
            return result

        # 4) the model, on the bundle's terms
        try:
            X = self._feature_row(sc)
            X_i = self.bundle["imputer"].transform(X)
            codes = self.model.predict(X_i)
            action_code = int(np.asarray(codes).ravel()[0])
            action = self.actions[action_code]

            # decode predict_proba THROUGH classes_ -- never assume the
            # column order. classes_ holds codes; column i is the
            # probability of classes_[i].
            proba = np.asarray(self.model.predict_proba(X_i)).ravel()
            classes = list(np.asarray(self.model.classes_).ravel())
            probs = {self.actions[int(c)]: float(p)
                     for c, p in zip(classes, proba)}
            confidence = float(probs[action])

            # 5) R2 -- the leash: low confidence -> rule engine answers
            if confidence < self.confidence_floor:
                rule_action = rule_engine_action(sc)
                result = self._assemble(
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
                return result

            # 6) the model owns it
            result = self._assemble(
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
            )
            return result

        except Exception as exc:  # noqa: BLE001
            # Model failure degrades LOUD and SAFE: rule engine answers,
            # the failure is in the reasons, the source says what
            # happened. A live safety path never fails silent.
            rule_action = rule_engine_action(sc)
            result = self._assemble(
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
            return result

    # -----------------------------------------------------------------
    # Output assembly
    # -----------------------------------------------------------------

    def _assemble(self, sc: dict, physics: dict, action: str,
                  confidence: float | None, source: str,
                  probabilities: dict | None, reasons: list[str],
                  t0: float) -> dict:
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        out = {
            "action": action,
            "confidence": confidence,
            "source": source,
            "reasons": reasons,
            "physics": physics,
            "probabilities": probabilities,
            "decision_latency_ms": latency_ms,
            "within_100ms_budget": latency_ms < DECISION_BUDGET_MS,
        }
        return out


# =====================================================================
# CLI -- the demo anchor, printed as the full decision JSON
# =====================================================================

def main() -> None:
    engine = DecisionEngine()
    print("=== RailGuard DecisionEngine -- demo anchor ===")
    print(f"model: {engine.bundle['model_name']} | "
          f"confidence floor: {engine.confidence_floor} | "
          f"features: {len(engine.feature_columns)}")
    decision = engine.decide(DEMO_ANCHOR)
    print("\nInput (DEMO_ANCHOR):")
    print(json.dumps(DEMO_ANCHOR, indent=2))
    print("\nDecision:")
    print(json.dumps(decision, indent=2))

    # invariant check: the anchor must land emergency_stop
    ok = decision["action"] == "emergency_stop"
    print(f"\nanchor invariant (action == emergency_stop): "
          f"{'PASS' if ok else 'FAIL'}")
    if decision["source"] == SOURCE_MODEL:
        print("note: anchor ran THROUGH the model (gray zone rung 2) -- "
              "the model earned this answer, R1 did not hand it one.")


if __name__ == "__main__":
    main()

