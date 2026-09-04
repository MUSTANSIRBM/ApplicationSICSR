# backend/app/core/incident_models.py
# Aligned with AIML/api/incident.py -- flat response, correct types.
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Type literals
# ---------------------------------------------------------------------------

EnvironmentalCondition = Literal["clear", "rain", "heavy_rain", "fog", "snow", "flood"]
ObstructionType = Literal[
    "landslide_debris", "boulder", "track_buckling", "fallen_tree",
    "stranded_vehicle", "water_logging", "cattle_crossing",
    "broken_rail", "signal_cable_theft", "sensor_miscount",
    "environmental_false_positive", "unknown_obstruction", "equipment_failure_ahead",
]
SensorType = Literal["track_circuit", "axle_counter", "vibration", "accelerometer"]
SectionStatus = Literal["OCCUPIED", "CLEAR"]
Action = Literal["proceed_with_caution", "reduce_speed", "reroute", "emergency_stop"]
DecisionSource = Literal["hard_rule", "model", "rule_fallback"]


# ---------------------------------------------------------------------------
# Request -- 14 raw sensor fields + control flags
# ---------------------------------------------------------------------------

class IncidentRequest(BaseModel):
    """14 raw sensor fields the frontend sends."""

    train_speed_kmh: float = Field(..., ge=45, le=200,
                                    description="Current train speed in km/h")
    distance_to_obstacle_km: float = Field(..., ge=0, le=20,
                                            description="Distance to obstacle in km")
    environmental_condition: EnvironmentalCondition = Field(
        ..., description="Current weather condition (dry is normalized to clear)")
    weather_alert: bool = Field(False, description="Whether a weather alert is active")
    signal_quality_percent: float = Field(..., ge=0, le=100,
                                          description="Signal quality percentage")
    severity_score: int = Field(..., ge=1, le=10,
                                description="Incident severity score 1-10")
    obstruction_type: ObstructionType = Field(..., description="Type of obstruction")
    alternative_route_available: bool = Field(False, description="Alternate route exists")
    communication_latency_ms: float = Field(..., ge=10, le=5000,
                                             description="Communication latency in ms")
    axle_balance: Optional[float] = Field(None, ge=0.3, le=1.7,
                                           description="Axle balance reading (optional)")
    ahead_section_status: SectionStatus = Field("CLEAR",
                                                 description="Status of section ahead")
    known_train_schedule: bool = Field(False, description="Whether train schedule is known")
    distance_from_station_km: float = Field(..., ge=0, le=25,
                                             description="Distance from station in km")
    sensor_type: SensorType = Field(..., description="Sensor type")

    # control flags (not features -- never sent to the model)
    create_repair_defect: bool = Field(False,
        description="Whether to create a repair defect in the planner")
    corridor: Optional[str] = Field(None, description="Corridor for defect creation")

    @field_validator("environmental_condition", mode="before")
    @classmethod
    def _norm_weather(cls, v: str) -> str:
        if v == "dry":
            return "clear"
        return v

    @field_validator("ahead_section_status", mode="before")
    @classmethod
    def _norm_ahead(cls, v: str) -> str:
        return v.upper() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Response -- flat, matching AIML/api/incident.py IncidentOut
# ---------------------------------------------------------------------------

class PhysicsOut(BaseModel):
    braking_distance_required_km: float
    time_to_obstacle_min: float
    effective_distance_km: float
    safe_stopping_possible: bool
    weather_braking_multiplier: Optional[float] = None
    speed_advisory: Optional[Dict[str, Any]] = None


class IncidentResponse(BaseModel):
    """Flat incident response matching the AIML output shape."""
    action: str
    confidence: Optional[float] = None
    source: str
    reasons: List[str]
    physics: PhysicsOut
    probabilities: Optional[Dict[str, float]] = None
    evidence: Optional[Dict[str, Any]] = None
    decision_latency_ms: float
    within_100ms_budget: bool
    repair_defect_id: Optional[str] = None
