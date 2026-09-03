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

# Weather friction multipliers
WEATHER_FRICTION = {
    "clear": 1.0,
    "rain": 1.3,
    "heavy_rain": 1.8,
    "fog": 1.5,
    "snow": 2.0,
    "flood": 2.2,
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
                self.model = joblib.load(MODEL_PATH)
                logger.info(f"✅ ML model loaded from {MODEL_PATH}")
            else:
                logger.warning(f"⚠️ ML model not found at {MODEL_PATH}. Using rule-based fallback only.")
                self.model = None
        except Exception as e:
            logger.error(f"❌ Failed to load ML model: {e}")
            self.model = None

    def _calculate_physics(self, request: IncidentRequest) -> Physics:
        """Calculate physics metrics based on speed, distance, and weather."""
        # Get friction multiplier for weather
        friction = WEATHER_FRICTION.get(request.environmental_condition, 1.0)

        # Calculate base braking distance
        # distance = (speed^2) / (250 * friction)
        braking_distance = (request.train_speed_kmh ** 2) / (250 * friction)

        # Effective distance = obstacle distance - (latency impact)
        # Latency impact = (latency_ms / 1000) * (speed_kmh / 3.6)
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
        # Rule 1: High severity + cannot stop + no alternative → emergency_stop
        if (request.severity_score >= 8 and
                not physics.safe_stopping_possible and
                not request.alternative_route_available):
            return Decision(
                action="emergency_stop",
                confidence=1.0,
                source="hard_rule",
                reasons=[
                    f"Severity score {request.severity_score} >= 8",
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
        """Extract ONLY the 16 raw input features for ML inference."""
        # Order must match training data columns
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
            1.0 if request.create_repair_defect else 0.0,
            self._encode_corridor(request.corridor)
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
        """Encode obstruction type as float."""
        mapping = {
            "landslide_debris": 0.0,
            "boulder": 1.0,
            "track_buckling": 2.0,
            "fallen_tree": 3.0,
            "stranded_vehicle": 4.0,
            "water_logging": 5.0,
            "cattle_crossing": 6.0
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

    def _encode_corridor(self, value: str) -> float:
        """Encode corridor as float (hash-based)."""
        # Simple deterministic hash
        return float(hash(value) % 100) / 100.0

    def _ml_inference(self, request: IncidentRequest) -> Tuple[Decision, bool]:
        """Run ML inference. Returns (Decision, success)."""
        if self.model is None:
            return None, False

        try:
            features = self._extract_features(request)
            # Predict class and probabilities
            pred = self.model.predict(features)[0]
            probs = self.model.predict_proba(features)[0]
            confidence = float(max(probs))

            # Map prediction to action
            action_map = {
                0: "proceed_with_caution",
                1: "reduce_speed",
                2: "reroute",
                3: "emergency_stop"
            }
            action = action_map.get(pred, "reduce_speed")

            return Decision(
                action=action,
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
        # If severity is high and stopping not possible
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

        # If alternative route available
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

        # Default: proceed with caution
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
        # Step 1: Calculate physics
        physics = self._calculate_physics(request)

        # Step 2: Apply hard rules (override ML)
        hard_decision, hard_applied = self._hard_rule_decision(request, physics)
        if hard_applied:
            return IncidentResponse(
                decision=hard_decision,
                physics=physics,
                repair_defect_id=None
            )

        # Step 3: ML inference
        ml_decision, ml_success = self._ml_inference(request)
        if ml_success and ml_decision.confidence >= 0.55:
            return IncidentResponse(
                decision=ml_decision,
                physics=physics,
                repair_defect_id=None
            )

        # Step 4: Rule fallback (ML unavailable or low confidence)
        fallback_decision = self._rule_fallback(request, physics)
        return IncidentResponse(
            decision=fallback_decision,
            physics=physics,
            repair_defect_id=None
        )


# Singleton instance
decision_engine = DecisionEngine()