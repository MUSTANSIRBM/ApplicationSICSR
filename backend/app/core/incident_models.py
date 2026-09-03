# backend/app/core/incident_models.py
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# Type definitions
EnvironmentalCondition = Literal["clear", "rain", "heavy_rain", "fog", "snow", "flood"]
ObstructionType = Literal[
    "landslide_debris", "boulder", "track_buckling", "fallen_tree",
    "stranded_vehicle", "water_logging", "cattle_crossing",
    "broken_rail", "signal_cable_theft", "sensor_miscount",
    "environmental_false_positive", "unknown_obstruction", "equipment_failure_ahead"
]
SensorType = Literal["track_circuit", "axle_counter", "vibration", "accelerometer"]
SectionStatus = Literal["OCCUPIED", "CLEAR"]
Action = Literal["proceed_with_caution", "reduce_speed", "reroute", "emergency_stop"]
DecisionSource = Literal["hard_rule", "model", "rule_fallback"]


class IncidentRequest(BaseModel):
    """16 raw sensor inputs for the decision pipeline."""

    train_speed_kmh: int = Field(..., ge=45, le=200, description="Current train speed in km/h")
    distance_to_obstacle_km: float = Field(..., ge=0, le=20, description="Distance to obstacle in km")
    environmental_condition: EnvironmentalCondition = Field(..., description="Current weather condition")
    weather_alert: bool = Field(..., description="Whether a weather alert is active")
    severity_score: int = Field(..., ge=1, le=10, description="Incident severity score 1-10")
    obstruction_type: ObstructionType = Field(..., description="Type of obstruction detected")
    alternative_route_available: bool = Field(..., description="Whether an alternate route exists")
    communication_latency_ms: int = Field(..., ge=10, le=5000, description="Communication latency in ms")
    signal_quality_percent: int = Field(..., ge=0, le=100, description="Signal quality percentage")
    sensor_type: SensorType = Field(..., description="Type of sensor that detected the incident")
    axle_balance: Optional[float] = Field(None, ge=0, le=100, description="Axle balance reading (optional)")
    ahead_section_status: SectionStatus = Field(..., description="Status of the section ahead")
    known_train_schedule: bool = Field(..., description="Whether train schedule is known")
    distance_from_station_km: float = Field(..., ge=0, description="Distance from nearest station in km")
    create_repair_defect: bool = Field(False, description="Whether to create a repair defect in the planner")
    corridor: str = Field(..., description="Corridor identifier for defect creation")

    @field_validator('train_speed_kmh')
    def validate_speed(cls, v):
        if v < 45 or v > 200:
            raise ValueError('train_speed_kmh must be between 45 and 200')
        return v

    @field_validator('severity_score')
    def validate_severity(cls, v):
        if v < 1 or v > 10:
            raise ValueError('severity_score must be between 1 and 10')
        return v

    # backend/app/core/incident_models.py - Updated field validator

    @field_validator('environmental_condition', mode='before')
    def normalize_environment(cls, v):
        """Normalize 'dry' to 'clear' before validation."""
        if v == "dry":
            return "clear"
        return v


class Decision(BaseModel):
    """Decision output from the evaluation pipeline."""

    action: Action = Field(..., description="Recommended action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the decision")
    source: DecisionSource = Field(..., description="Source of the decision")
    reasons: List[str] = Field(..., description="List of reasons for the decision")


class Physics(BaseModel):
    """Physics calculations for the incident."""

    braking_distance_required_km: float = Field(..., description="Braking distance required in km")
    time_to_obstacle_min: float = Field(..., description="Time to obstacle in minutes")
    safe_stopping_possible: bool = Field(..., description="Whether safe stopping is possible")


class IncidentResponse(BaseModel):
    """Complete incident response."""

    decision: Decision = Field(..., description="Decision output")
    physics: Physics = Field(..., description="Physics calculations")
    repair_defect_id: Optional[str] = Field(None, description="ID of created repair defect if requested")