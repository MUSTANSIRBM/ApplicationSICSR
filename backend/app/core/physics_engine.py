# backend/app/core/physics_engine.py
import math
from typing import Tuple, Optional
from app.core.incident_models import (
    IncidentRequest,
    PhysicsMetrics,
    DecisionResult,
    DecisionAction,
    DecisionSource,
    EnvironmentalCondition
)


class PhysicsEngine:
    """Physics calculations and hard rule enforcement"""

    # Weather multipliers for braking distance
    WEATHER_MULTIPLIERS = {
        EnvironmentalCondition.CLEAR: 1.0,
        EnvironmentalCondition.RAIN: 1.3,
        EnvironmentalCondition.HEAVY_RAIN: 1.6,
        EnvironmentalCondition.FOG: 1.4,
        EnvironmentalCondition.SNOW: 2.0,
        EnvironmentalCondition.FLOOD: 2.5,
    }

    # Friction coefficient (μ) - standard railway value
    FRICTION_COEFFICIENT = 0.25

    # Gravity constant (m/s²)
    GRAVITY = 9.81

    # Safety margin factor (20% extra distance)
    SAFETY_MARGIN = 1.2

    def __init__(self):
        pass

    def calculate_physics(self, request: IncidentRequest) -> PhysicsMetrics:
        """
        Calculate physics metrics from the incident request.

        Formula: braking_distance = v² / (2 * μ * g) * weather_multiplier * safety_margin
        """
        # Convert speed from km/h to m/s
        speed_mps = request.train_speed_kmh * 1000 / 3600

        # Get weather multiplier
        weather_multiplier = self.WEATHER_MULTIPLIERS.get(
            request.environmental_condition,
            1.0
        )

        # Calculate braking distance in meters
        braking_distance_m = (
                                     (speed_mps ** 2) /
                                     (2 * self.FRICTION_COEFFICIENT * self.GRAVITY)
                             ) * weather_multiplier * self.SAFETY_MARGIN

        # Convert to kilometers
        braking_distance_km = braking_distance_m / 1000

        # Calculate time to obstacle (in minutes)
        if request.train_speed_kmh > 0:
            time_to_obstacle_min = (request.distance_to_obstacle_km / request.train_speed_kmh) * 60
        else:
            time_to_obstacle_min = float('inf')

        # Check if safe stopping is possible
        # Effective distance = distance_to_obstacle_km - (braking_distance_km * 1.1)
        # We need a 10% margin
        safe_stopping_possible = (
                request.distance_to_obstacle_km > (braking_distance_km * 1.1)
        )

        # Calculate braking margin
        braking_margin_km = request.distance_to_obstacle_km - braking_distance_km

        return PhysicsMetrics(
            braking_distance_required_km=round(braking_distance_km, 4),
            time_to_obstacle_min=round(time_to_obstacle_min, 2),
            safe_stopping_possible=safe_stopping_possible,
            braking_margin_km=round(braking_margin_km, 4)
        )

    def apply_hard_rules(
            self,
            request: IncidentRequest,
            physics: PhysicsMetrics
    ) -> Optional[DecisionResult]:
        """
        Apply hard safety rules.
        Returns a DecisionResult if a hard rule is triggered, else None.
        """
        # HARD RULE 1: Severity >= 9 AND no safe stopping AND no alternative route
        if (
                request.severity_score >= 9 and
                not physics.safe_stopping_possible and
                not request.alternative_route_available
        ):
            return DecisionResult(
                action=DecisionAction.EMERGENCY_STOP,
                confidence=1.0,
                source=DecisionSource.HARD_RULE,
                reasons=[
                    f"⚠️ HARD RULE: Severity {request.severity_score}/10 (critical)",
                    f"⚠️ Cannot stop safely (braking distance: {physics.braking_distance_required_km:.2f}km, distance: {request.distance_to_obstacle_km:.2f}km)",
                    "⚠️ No alternative route available",
                    "🚨 EMERGENCY STOP MANDATED"
                ]
            )

        # HARD RULE 2: Weather alert + sensor indicates obstruction + speed > 150
        if (
                request.weather_alert and
                request.sensor_type in [SensorType.VIBRATION, SensorType.ACCELEROMETER] and
                request.train_speed_kmh > 150
        ):
            return DecisionResult(
                action=DecisionAction.REDUCE_SPEED,
                confidence=1.0,
                source=DecisionSource.HARD_RULE,
                reasons=[
                    f"⚠️ HARD RULE: Weather alert active with {request.environmental_condition.value}",
                    f"⚠️ Sensor ({request.sensor_type.value}) detecting anomalies",
                    f"⚠️ Speed {request.train_speed_kmh}km/h exceeds safe limit",
                    "📉 Reduce speed immediately"
                ]
            )

        # HARD RULE 3: Communication latency > 3000ms + signal quality < 50%
        if (
                request.communication_latency_ms > 3000 and
                request.signal_quality_percent < 50
        ):
            return DecisionResult(
                action=DecisionAction.PROCEED_WITH_CAUTION,
                confidence=1.0,
                source=DecisionSource.HARD_RULE,
                reasons=[
                    f"⚠️ HARD RULE: Communication latency {request.communication_latency_ms}ms (critical)",
                    f"⚠️ Signal quality {request.signal_quality_percent}% (poor)",
                    "📡 Proceed with extreme caution"
                ]
            )

        # HARD RULE 4: Obstruction type is landslide or boulder + severity > 7
        if (
                request.obstruction_type in [
            ObstructionType.LANDSLIDE_DEBRIS,
            ObstructionType.BOULDER
        ] and
                request.severity_score > 7
        ):
            return DecisionResult(
                action=DecisionAction.EMERGENCY_STOP,
                confidence=1.0,
                source=DecisionSource.HARD_RULE,
                reasons=[
                    f"⚠️ HARD RULE: Heavy obstruction ({request.obstruction_type.value})",
                    f"⚠️ Severity {request.severity_score}/10",
                    "🚨 EMERGENCY STOP MANDATED - Track blockage"
                ]
            )

        return None

    def get_rule_fallback(
            self,
            request: IncidentRequest,
            physics: PhysicsMetrics
    ) -> DecisionResult:
        """
        Deterministic rule-based fallback when ML confidence is low.
        """
        reasons = []

        # Determine action based on physics and severity
        if not physics.safe_stopping_possible:
            action = DecisionAction.EMERGENCY_STOP
            reasons.append(f"⚠️ Cannot stop safely (braking distance: {physics.braking_distance_required_km:.2f}km)")
        elif request.severity_score >= 7:
            action = DecisionAction.REDUCE_SPEED
            reasons.append(f"⚠️ High severity {request.severity_score}/10")
        elif request.weather_alert:
            action = DecisionAction.PROCEED_WITH_CAUTION
            reasons.append(f"⚠️ Weather alert: {request.environmental_condition.value}")
        elif request.alternative_route_available:
            action = DecisionAction.REROUTE
            reasons.append(f"🔄 Alternative route available")
        else:
            action = DecisionAction.PROCEED_WITH_CAUTION
            reasons.append(f"ℹ️ No critical issues detected")

        # Add physics context
        reasons.append(f"📊 Braking distance: {physics.braking_distance_required_km:.2f}km")
        reasons.append(f"⏱️ Time to obstacle: {physics.time_to_obstacle_min:.2f}min")

        return DecisionResult(
            action=action,
            confidence=0.50,  # Below threshold, but deterministic
            source=DecisionSource.RULE_FALLBACK,
            reasons=reasons
        )


# Create a singleton instance
physics_engine = PhysicsEngine()