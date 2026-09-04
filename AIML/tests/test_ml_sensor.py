"""
tests/test_ml_sensor.py -- the sensor module's 8 guards.

Every test here exists because something specific could silently go
wrong. Map (test -> fear):

  determinism     -> seed drift: two runs, two datasets, a model that
                      can never be reproduced at the demo bench
  leakage wall    -> the rejected-external-doc problem: computed
                      physics sneaking back in as features, at the
                      matrix level AND at the API schema level
  noise exactness -> "4% honest noise" quietly becoming 3.8% or 4.4%,
                      which changes the F1 ceiling and the story
  R1 spy          -> the wall eroding: model consulted on a
                      catastrophic case because someone reordered
                      the checks in decide.py
  R2 fallback     -> the leash snapping: low-confidence model answers
                      reaching the tracks
  anchor          -> the demo scenario drifting away from the spec
                      (the 8.46 number IS the spec, post flag-2 fix)
  API contract    -> junk accepted, dry rejected, computed fields
                      smuggled into the request schema
  bridge          -> the sqlmodel-select 500 returning, departments
                      mapping to the wrong enum member, defects
                      written half-shaped

Hermetic: the bridge test re-seeds planner.db (house rule -- tests
re-seed by design). Re-run `python -m planner.demo_state` before any
manual demo session afterward.
"""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from ml_sensor.decide import DecisionEngine
from ml_sensor.scenarios import (ACTIONS, BANNED_FEATURE_NAMES,
                                  FEATURE_COLUMNS, LABEL_NOISE_FRACTION,
                                  OBSTRUCTION_TYPES, DEMO_ANCHOR,
                                  build_dataset, encode_features)
from ml_sensor.train import features_matrix, load_bundle

# =====================================================================
# Shared fixtures / helpers
# =====================================================================

# A catastrophic scenario that MUST trigger R1: 180 km/h in snow with
# 3 km to go -- braking needs (1.8^2)*2*1.9 = 12.31 km, effective is
# ~2.97 km -> cannot stop; severity 9, no alternate -> the wall.
R1_SCENARIO = {
    "train_speed_kmh": 180.0, "distance_to_obstacle_km": 3.0,
    "environmental_condition": "snow", "weather_alert": True,
    "signal_quality_percent": 80.0, "severity_score": 9,
    "obstruction_type": "landslide_debris",
    "alternative_route_available": False,
    "communication_latency_ms": 300, "axle_balance": None,
    "ahead_section_status": "CLEAR", "known_train_schedule": True,
    "distance_from_station_km": 5.0, "sensor_type": "track_circuit",
}

# A gray-zone scenario for the R2 test: can stop comfortably, severity
# 5, fallen tree -> rule ladder says reduce_speed (rung 4).
R2_SCENARIO = {
    "train_speed_kmh": 80.0, "distance_to_obstacle_km": 10.0,
    "environmental_condition": "clear", "weather_alert": False,
    "signal_quality_percent": 70.0, "severity_score": 5,
    "obstruction_type": "fallen_tree",
    "alternative_route_available": False,
    "communication_latency_ms": 400, "axle_balance": None,
    "ahead_section_status": "CLEAR", "known_train_schedule": True,
    "distance_from_station_km": 4.0, "sensor_type": "track_circuit",
}


class SpyModel:
    """Mimics the sklearn/xgboost surface decide.py touches (predict,
    predict_proba, classes_) while COUNTING calls. The R1 test's whole
    claim rests on this counter honestly ticking."""

    def __init__(self, action_code: int = 3, probs=None):
        self.calls = 0
        self.action_code = action_code
        self.probs = probs if probs is not None else [0.05, 0.05, 0.05, 0.85]

    def predict(self, X):
        self.calls += 1
        return np.array([self.action_code])

    def predict_proba(self, X):
        self.calls += 1
        return np.array([self.probs])

    @property
    def classes_(self):
        return np.array([0, 1, 2, 3])


def _base_incident(**overrides) -> dict:
    """A valid 14-field incident payload, overridable per test."""
    sc = dict(DEMO_ANCHOR)
    sc.update(overrides)
    return sc


# =====================================================================
# 1) Generator determinism + coverage
# =====================================================================

def test_generator_determinism_and_coverage():
    a = build_dataset(500, seed=7)
    b = build_dataset(500, seed=7)
    assert a == b, "same seed must give byte-identical scenarios"

    full = build_dataset(4000, seed=42)
    types = {sc["obstruction_type"] for sc in full}
    assert types == set(OBSTRUCTION_TYPES), "all 13 types must appear"
    labels = {sc["label"] for sc in full}
    assert labels == set(ACTIONS), "all 4 actions must appear"

    counts = {a: 0 for a in ACTIONS}
    for sc in full:
        counts[sc["label"]] += 1
    for action, c in counts.items():
        assert c / len(full) >= 0.10, (
            f"{action} at {c/len(full):.1%} -- macro-F1 starves "
            f"below 10% support; revisit TYPE_WEIGHTS")


# =====================================================================
# 2) The leakage wall, at both layers
# =====================================================================

def test_leakage_wall_feature_and_api():
    # layer 1: the feature matrix
    full = build_dataset(400, seed=42)
    X = features_matrix(full)
    assert list(X.columns) == list(FEATURE_COLUMNS)
    assert not (set(X.columns) & BANNED_FEATURE_NAMES), (
        "computed physics leaked into features -- the exact "
        "rejected-external-doc failure mode")

    # the ban must actually BITE: assert_leakage_free must reject a
    # matrix containing a banned column (a guard that can't fail is
    # decoration, not a guard)
    from ml_sensor.scenarios import assert_leakage_free
    with pytest.raises(AssertionError):
        assert_leakage_free(list(FEATURE_COLUMNS) + ["braking_ratio"])
    with pytest.raises(AssertionError):
        assert_leakage_free(list(FEATURE_COLUMNS)[:-1])  # drift, too

    # layer 2: the API schema -- the frontend physically cannot send
    # computed values because the fields don't exist
    from api.incident import IncidentIn
    fields = set(IncidentIn.model_fields)
    assert not (fields & BANNED_FEATURE_NAMES), (
        "computed physics accepted as request input (decision 12 wall "
        "breached at the schema)")
    assert "time_to_obstacle_min" not in fields, (
        "time-to-obstacle must be backend-computed, never sent")


# =====================================================================
# 3) Label noise is exact
# =====================================================================

def test_label_noise_exact():
    full = build_dataset(4000, seed=42)
    n = len(full)
    noised = [sc for sc in full if sc["label_noised"]]
    assert len(noised) == round(LABEL_NOISE_FRACTION * n), (
        f"expected exactly {round(LABEL_NOISE_FRACTION * n)} noised "
        f"rows, got {len(noised)}")
    for sc in noised:
        assert sc["label"] != sc["rule_label"], (
            "a 'noised' row must actually differ from its rule label")
    for sc in full:
        if not sc["label_noised"]:
            assert sc["label"] == sc["rule_label"]


# =====================================================================
# 4) R1: the model is never consulted on catastrophic cases
# =====================================================================

def test_r1_model_never_consulted():
    bundle = load_bundle()
    spy = SpyModel(action_code=0)   # would say proceed_with_caution!
    engine = DecisionEngine(bundle=bundle, model=spy)

    decision = engine.decide(R1_SCENARIO)

    assert decision["action"] == "emergency_stop"
    assert decision["source"] == "hard_rule"
    assert spy.calls == 0, (
        "R1 fired but the model was consulted -- the wall has a hole; "
        "check the order of operations in decide.py")
    assert decision["physics"]["safe_stopping_possible"] is False
    assert decision["confidence"] == 1.0  # rule firing, not statistics


# =====================================================================
# 5) R2: low confidence falls back to the rule engine
# =====================================================================

def test_r2_low_confidence_falls_back_to_rules():
    bundle = load_bundle()
    # uniform probabilities: max = 0.25 < 0.55 floor, whichever action
    # the spy's predict nominally picks
    spy = SpyModel(action_code=2, probs=[0.25, 0.25, 0.25, 0.25])
    engine = DecisionEngine(bundle=bundle, model=spy)

    decision = engine.decide(R2_SCENARIO)

    assert spy.calls >= 2, "model must have been tried before fallback"
    assert decision["source"] == "rule_fallback"
    from ml_sensor.scenarios import rule_engine_action
    assert decision["action"] == rule_engine_action(R2_SCENARIO), (
        "R2 must return the RULE answer, not a watered-down model one")
    assert decision["action"] == "reduce_speed"
    assert decision["probabilities"] is not None  # doubt is shown, not hidden


# =====================================================================
# 6) The anchor invariant + spec physics numbers
# =====================================================================

def test_anchor_invariant_and_physics():
    engine = DecisionEngine()
    decision = engine.decide(DEMO_ANCHOR)

    assert decision["action"] == "emergency_stop", (
        "the demo anchor must land emergency_stop")
    assert decision["source"] == "model", (
        "anchor is rung 2 (can stop + sev 9): the gray zone, the "
        "model's answer, not R1's")
    assert decision["confidence"] >= 0.55

    p = decision["physics"]
    # flag-2 corrected numbers, locked into the test so drift is loud
    assert p["braking_distance_required_km"] == pytest.approx(4.608, abs=0.001)
    assert p["effective_distance_km"] == pytest.approx(8.46, abs=0.001)
    assert p["safe_stopping_possible"] is True
    assert decision["decision_latency_ms"] < 100


# =====================================================================
# 7) API contract: 200s, 422s, and nothing computed accepted
# =====================================================================

def test_api_incident_contract():
    from api.main import app
    with TestClient(app) as client:
        # anchor without bridge -> full decision, no defect
        r = client.post("/api/incident", json=_base_incident())
        assert r.status_code == 200
        body = r.json()
        assert body["action"] == "emergency_stop"
        assert body["repair_defect"] is None
        assert body["within_100ms_budget"] is True

        # unknown obstruction type -> 422, never a guess
        r = client.post("/api/incident",
                        json=_base_incident(obstruction_type="space_laser"))
        assert r.status_code == 422

        # out-of-range speed -> 422
        r = client.post("/api/incident",
                        json=_base_incident(train_speed_kmh=300))
        assert r.status_code == 422

        # dry -> clear normalization -> 200 (locked boundary rule)
        r = client.post("/api/incident",
                        json=_base_incident(
                            environmental_condition="dry",
                            train_speed_kmh=60,
                            distance_to_obstacle_km=11.0,
                            severity_score=3,
                            obstruction_type="sensor_miscount",
                            communication_latency_ms=400,
                            signal_quality_percent=88.0))
        assert r.status_code == 200

        # bridge flag without corridor -> 422
        r = client.post("/api/incident",
                        json=_base_incident(create_repair_defect=True))
        assert r.status_code == 422

        # computed fields in the body are UNKNOWN fields: pydantic
        # ignores extras by default, but our schema has no such field,
        # so sending braking data changes nothing -- assert the wall
        r = client.post("/api/incident",
                        json=_base_incident(
                            braking_distance_required_km=0.1,
                            safe_stopping_possible=False))
        assert r.status_code == 200
        assert r.json()["action"] == "emergency_stop", (
            "sent computed values must not change the decision -- "
            "they are not features")


# =====================================================================
# 8) The bridge: defect written, departments pinned to enum truth
# =====================================================================

@pytest.fixture(scope="module")
def fresh_db():
    from planner.seed import seed
    seed()          # house rule: tests re-seed planner.db
    yield


def test_bridge_creates_defect_and_departments(fresh_db):
    from api.main import app
    from planner.db import get_session
    from planner.models import Defect, Department, DepartmentCode

    with TestClient(app) as client:
        # --- no flag -> no write ---
        r = client.post("/api/incident", json=_base_incident())
        assert r.status_code == 200
        assert r.json()["repair_defect"] is None

        # --- anchor + bridge -> INC-0001, ENG, safety tier ---
        r = client.post("/api/incident", json=_base_incident(
            create_repair_defect=True, corridor="ET-NGP"))
        assert r.status_code == 200
        rd = r.json()["repair_defect"]
        assert rd["source_ref"] == "INC-0001"
        assert rd["department"] == "ENG"
        assert rd["severity"] == 5 and rd["safety_flag"] is True
        assert rd["base_duration_min"] == 720

        # --- department mapping pinned to the pasted enum truth ---
        r = client.post("/api/incident", json=_base_incident(
            severity_score=6, obstruction_type="signal_cable_theft",
            create_repair_defect=True, corridor="ET-NGP"))
        assert r.json()["repair_defect"]["department"] == "SNT"

        r = client.post("/api/incident", json=_base_incident(
            severity_score=6, obstruction_type="equipment_failure_ahead",
            create_repair_defect=True, corridor="ET-NGP"))
        assert r.json()["repair_defect"]["department"] == "TRD"

        # --- unknown corridor -> 404, nothing written ---
        r = client.post("/api/incident", json=_base_incident(
            create_repair_defect=True, corridor="XX-XXX"))
        assert r.status_code == 404

    # --- DB-level truth: the defect exists, correctly joined ---
    # (uses sqlmodel's select: today's v3 500 would fail RIGHT HERE
    # if it ever came back)
    session_gen = get_session()
    session = next(session_gen)
    try:
        d = session.exec(select(Defect).where(
            Defect.source_ref == "INC-0001")).first()
        assert d is not None, "bridge claimed success but wrote nothing"
        assert d.defect_type == "LANDSLIDE_DEBRIS"
        assert d.safety_flag is True and d.severity == 5
        assert d.description.startswith("Repair from sensor incident")
        assert "emergency_stop" in d.description, (
            "the defect must remember the decision that created it "
            "(explainability is a data structure)")
        dept = session.exec(select(Department).where(
            Department.id == d.department_id)).first()
        assert dept is not None and dept.code == DepartmentCode.ENG
        snt = session.exec(select(Defect).where(
            Defect.source_ref == "INC-0002")).first()
        assert snt is not None
        snt_dept = session.exec(select(Department).where(
            Department.id == snt.department_id)).first()
        assert snt_dept.code == DepartmentCode.SNT
        trd = session.exec(select(Defect).where(
            Defect.source_ref == "INC-0003")).first()
        assert trd is not None
        trd_dept = session.exec(select(Department).where(
            Department.id == trd.department_id)).first()
        assert trd_dept.code == DepartmentCode.TRD
    finally:
        session_gen.close()

# =====================================================================
# 9) Speed advisory (v2): display-only, only on reduce_speed
# =====================================================================

def test_speed_advisory_on_reduce_only():
    from ml_sensor.decide import DecisionEngine
    from ml_sensor.scenarios import DEMO_ANCHOR
    
    engine = DecisionEngine()

    # a reduce_speed scenario (80 km/h, clear, fallen_tree, sev 5)
    reduce_sc = {
        "train_speed_kmh": 80.0,
        "distance_to_obstacle_km": 2.5,
        "environmental_condition": "clear",
        "weather_alert": False,
        "signal_quality_percent": 70.0,
        "severity_score": 5,
        "obstruction_type": "fallen_tree",
        "alternative_route_available": False,
        "communication_latency_ms": 500,
        "axle_balance": None,
        "ahead_section_status": "CLEAR",
        "known_train_schedule": True,
        "distance_from_station_km": 6.0,
        "sensor_type": "track_circuit",
    }
    d = engine.decide(reduce_sc)
    assert d["action"] == "reduce_speed"
    adv = d["physics"]["speed_advisory"]
    v = adv["recommended_speed_kmh"]
    assert v is not None
    assert v <= reduce_sc["train_speed_kmh"], "never advise speeding UP"
    assert v % 5 == 0, "railway speeds are multiples of 5"
    assert v >= 25, "below 25 km/h is not a crawl, it is a stop"
    assert any("Speed advisory" in r for r in d["reasons"])

    # formula spot-check: sev 5 -> 75% cap = 60; comfort is higher ->
    # advisory must be the severity cap, rounded down to 5
    assert v == 60, f"expected severity-cap 60, got {v}"

    # non-reduce actions carry NO advisory key (vocabulary untouched)
    d2 = engine.decide(DEMO_ANCHOR)      # emergency_stop
    assert "speed_advisory" not in d2["physics"]

    # the advisory must NOT be a model feature (leakage wall holds)
    from ml_sensor.scenarios import FEATURE_COLUMNS
    assert "speed_advisory" not in FEATURE_COLUMNS
    assert "recommended_speed_kmh" not in FEATURE_COLUMNS


# =====================================================================
# 10) Evidence: why the model chose this (v3)
# =====================================================================

def test_evidence_on_model_decisions():
    from ml_sensor.decide import DecisionEngine
    from ml_sensor.scenarios import FEATURE_COLUMNS
    
    engine = DecisionEngine()

    # model-source decision -> evidence present, well-formed
    d = engine.decide(DEMO_ANCHOR)
    assert d["source"] == "model"
    ev = d["evidence"]
    assert ev is not None
    assert "summary" in ev and "features" in ev
    assert len(ev["features"]) >= 3, "evidence should cover the model's top features"
    for entry in ev["features"]:
        assert entry["reads"], "every evidence entry must be renderable"
        assert entry["feature"] in FEATURE_COLUMNS
    # leakage wall: evidence describes, never feeds
    assert not ({"speed_advisory", "recommended_speed_kmh"} &
                {e["feature"] for e in ev["features"]})

    # hard_rule decision -> no model, no evidence
    d2 = engine.decide(R1_SCENARIO)
    assert d2["source"] == "hard_rule"
    assert d2["evidence"] is None


def test_evidence_via_api():
    from fastapi.testclient import TestClient
    from api.main import app
    from ml_sensor.scenarios import DEMO_ANCHOR
    with TestClient(app) as client:
        r = client.post("/api/incident", json=dict(DEMO_ANCHOR))
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "model"
        assert body["evidence"] is not None
        assert len(body["evidence"]["features"]) >= 3
        assert body["decision_latency_ms"] < 100

