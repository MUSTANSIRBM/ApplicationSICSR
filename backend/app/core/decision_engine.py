# backend/app/core/decision_engine.py
import logging
import joblib
import os
from typing import Dict, Any, List, Tuple
from pathlib import Path
import numpy as np

from app.core.incident_models import (
    IncidentRequest, Decision, Physics, IncidentResponse,
    Action, DecisionSource, EnvironmentalCondition
)

logger = logging.getLogger(__name__)

# Updated weather friction multipliers
WEATHER_FRICTION = {
    "clear": 1.0,
    "rain": 1.3,
    "heavy_rain": 1.6,
    "fog": 1.2,
    "snow": 1.9,
    "flood": 1.7,
}

# Model path
MODEL_PATH = Path(__file__).parent.parent.parent.parent / "AIML" / "ml_sensor" / "decision_model.joblib"


class DecisionEngine:
    """Sensor decision engine with physics, hard rules, and ML inference."""

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the ML model if available, otherwise fallback gracefully."""
        try:
            if MODEL_PATH.exists():
                loaded = joblib.load(MODEL_PATH)
                # Handle both old and new model formats
                if isinstance(loaded, dict) and 'model' in loaded:
                    self.model = loaded
                    logger.info(f"✅ ML model (with label encoder) loaded from {MODEL_PATH}")
                else:
                    self.model = loaded
                    logger.info(f"✅ ML model loaded from {MODEL_PATH}")
            else:
                logger.warning(f"⚠️ ML model not found at {MODEL_PATH}. Using rule-based fallback only.")
                self.model = None
        except Exception as e:
            logger.error(f"❌ Failed to load ML model: {e}")
            self.model = None

    def _calculate_physics(self, request: IncidentRequest) -> Physics:
        """Calculate physics metrics based on speed, distance, and weather."""
        # Updated friction multiplier
        friction = WEATHER_FRICTION.get(request.environmental_condition, 1.0)

        # Updated braking distance formula: ((speed / 100) ** 2) * 2.0 * friction
        braking_distance = ((request.train_speed_kmh / 100) ** 2) * 2.0 * friction

        # Effective distance = obstacle distance - (latency impact)
        latency_impact = (request.communication_latency_ms / 1000) * (request.train_speed_kmh / 3.6)
        effective_distance = max(0, request.distance_to_obstacle_km - latency_impact)

        # Safe stopping possible if effective_distance >= braking_distance + 0.5km margin
        safe_stopping = effective_distance >= (braking_distance + 0.5)

        # Time to obstacle in minutes
        if request.train_speed_kmh > 0:
            time_to_obstacle = (effective_distance / request.train_speed_kmh) * 60
        else:
            time_to_obstacle = 0

        return Physics(
            braking_distance_required_km=round(braking_distance, 3),
            time_to_obstacle_min=round(time_to_obstacle, 2),
            safe_stopping_possible=safe_stopping
        )

    def _hard_rule_decision(self, request: IncidentRequest, physics: Physics) -> Tuple[Decision, bool]:
        """Apply hard safety rules. Returns (Decision, was_applied)."""
        # Updated Rule 1: severity >= 9 (not 8)
        if (request.severity_score >= 9 and
                not physics.safe_stopping_possible and
                not request.alternative_route_available):
            return Decision(
                action="emergency_stop",
                confidence=1.0,
                source="hard_rule",
                reasons=[
                    f"Severity score {request.severity_score} >= 9",
                    "Safe stopping not possible",
                    "No alternative route available"
                ]
            ), True

        # Rule 2: Weather alert + poor visibility → reduce_speed
        if request.weather_alert and request.environmental_condition in ["fog", "heavy_rain", "snow"]:
            return Decision(
                action="reduce_speed",
                confidence=0.95,
                source="hard_rule",
                reasons=[
                    f"Weather alert active with {request.environmental_condition}",
                    "Poor visibility conditions"
                ]
            ), True

        # Rule 3: Obstruction + occupied section ahead → emergency_stop
        if request.ahead_section_status == "OCCUPIED" and request.distance_to_obstacle_km < 2.0:
            return Decision(
                action="emergency_stop",
                confidence=0.98,
                source="hard_rule",
                reasons=[
                    "Section ahead is occupied",
                    f"Obstacle detected at {request.distance_to_obstacle_km}km"
                ]
            ), True

        return None, False

    def _extract_features(self, request: IncidentRequest) -> np.ndarray:
        """
        Extract ONLY the 14 raw sensor features for ML inference.
        IMPORTANT: REMOVED create_repair_defect and corridor to prevent label leakage.
        """
        # Order must match training data columns (14 features, NOT 16)
        features = [
            request.train_speed_kmh,
            request.distance_to_obstacle_km,
            self._encode_environment(request.environmental_condition),
            1.0 if request.weather_alert else 0.0,
            request.severity_score,
            self._encode_obstruction(request.obstruction_type),
            1.0 if request.alternative_route_available else 0.0,
            request.communication_latency_ms,
            request.signal_quality_percent,
            self._encode_sensor(request.sensor_type),
            request.axle_balance if request.axle_balance is not None else 0.0,
            1.0 if request.ahead_section_status == "OCCUPIED" else 0.0,
            1.0 if request.known_train_schedule else 0.0,
            request.distance_from_station_km,
            # REMOVED: create_repair_defect (control flag)
            # REMOVED: corridor (control flag)
        ]
        return np.array(features).reshape(1, -1)

    def _encode_environment(self, value: str) -> float:
        """Encode environmental condition as float."""
        mapping = {
            "clear": 0.0,
            "rain": 1.0,
            "heavy_rain": 2.0,
            "fog": 3.0,
            "snow": 4.0,
            "flood": 5.0
        }
        return mapping.get(value, 0.0)

    def _encode_obstruction(self, value: str) -> float:
        """Encode obstruction type as float with all 13 types."""
        mapping = {
            "landslide_debris": 0.0,
            "boulder": 1.0,
            "track_buckling": 2.0,
            "fallen_tree": 3.0,
            "stranded_vehicle": 4.0,
            "water_logging": 5.0,
            "cattle_crossing": 6.0,
            "broken_rail": 7.0,
            "signal_cable_theft": 8.0,
            "sensor_miscount": 9.0,
            "environmental_false_positive": 10.0,
            "unknown_obstruction": 11.0,
            "equipment_failure_ahead": 12.0
        }
        return mapping.get(value, 0.0)

    def _encode_sensor(self, value: str) -> float:
        """Encode sensor type as float."""
        mapping = {
            "track_circuit": 0.0,
            "axle_counter": 1.0,
            "vibration": 2.0,
            "accelerometer": 3.0
        }
        return mapping.get(value, 0.0)

    # backend/app/core/decision_engine.py - Updated _ml_inference method

    def _ml_inference(self, request: IncidentRequest) -> Tuple[Decision, bool]:
        """Run ML inference. Returns (Decision, success)."""
        if self.model is None:
            return None, False

        try:
            features = self._extract_features(request)

            # Handle model saved as dict with label_encoder
            if isinstance(self.model, dict):
                model = self.model.get('model')
                label_encoder = self.model.get('label_encoder')
                if model is None:
                    logger.error("❌ No 'model' key in saved model dict")
                    return None, False
            else:
                model = self.model
                label_encoder = None

            # Make prediction
            pred = model.predict(features)[0]
            probs = model.predict_proba(features)[0]
            confidence = float(max(probs))

            # Decode prediction
            if label_encoder is not None:
                pred_decoded = label_encoder.inverse_transform([pred])[0]
            else:
                # Fallback mapping (just in case)
                action_map = {
                    0: "proceed_with_caution",
                    1: "reduce_speed",
                    2: "reroute",
                    3: "emergency_stop"
                }
                pred_decoded = action_map.get(pred, "reduce_speed")

            # Map action to valid Action type
            valid_actions = ["proceed_with_caution", "reduce_speed", "reroute", "emergency_stop"]
            if pred_decoded not in valid_actions:
                pred_decoded = "reduce_speed"

            return Decision(
                action=pred_decoded,  # type: ignore
                confidence=confidence,
                source="model",
                reasons=[
                    f"ML model prediction with {confidence:.1%} confidence",
                    "Based on sensor pattern analysis"
                ]
            ), True

        except Exception as e:
            logger.error(f"❌ ML inference failed: {e}")
            return None, False

    def _rule_fallback(self, request: IncidentRequest, physics: Physics) -> Decision:
        """Conservative rule-based fallback when ML is unavailable or low confidence."""
        if request.severity_score >= 6 and not physics.safe_stopping_possible:
            if request.distance_to_obstacle_km < 1.0:
                return Decision(
                    action="emergency_stop",
                    confidence=0.90,
                    source="rule_fallback",
                    reasons=[
                        f"Severity {request.severity_score} >= 6",
                        "Distance to obstacle < 1km",
                        "Safe stopping not possible"
                    ]
                )
            else:
                return Decision(
                    action="reduce_speed",
                    confidence=0.85,
                    source="rule_fallback",
                    reasons=[
                        f"Severity {request.severity_score} >= 6",
                        "Distance to obstacle > 1km",
                        "Reducing speed as precaution"
                    ]
                )

        if request.alternative_route_available and request.severity_score >= 5:
            return Decision(
                action="reroute",
                confidence=0.80,
                source="rule_fallback",
                reasons=[
                    "Alternative route available",
                    f"Severity {request.severity_score} >= 5",
                    "Rerouting to avoid incident"
                ]
            )

        return Decision(
            action="proceed_with_caution",
            confidence=0.70,
            source="rule_fallback",
            reasons=[
                "No high-risk conditions detected",
                "Proceeding with caution"
            ]
        )

    def evaluate(self, request: IncidentRequest) -> IncidentResponse:
        """Main entry point: evaluate incident and return decision."""
        physics = self._calculate_physics(request)

        hard_decision, hard_applied = self._hard_rule_decision(request, physics)
        if hard_applied:
            return IncidentResponse(
                decision=hard_decision,
                physics=physics,
                repair_defect_id=None
            )

        ml_decision, ml_success = self._ml_inference(request)
        if ml_success and ml_decision.confidence >= 0.55:
            return IncidentResponse(
                decision=ml_decision,
                physics=physics,
                repair_defect_id=None
            )

        fallback_decision = self._rule_fallback(request, physics)
        return IncidentResponse(
            decision=fallback_decision,
            physics=physics,
            repair_defect_id=None
        )


# Singleton instance
decision_engine = DecisionEngine()