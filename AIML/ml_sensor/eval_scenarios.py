"""
ml_sensor/eval_scenarios.py -- the held-out generalization proof.

Step 4 of 7. Ten HAND-CRAFTED scenarios (data no generator made) are
run through the trained DecisionEngine and scored against HAND LABELS.
Target: 7+/10 agreement. Disagreements are LISTED FOR OWNER REVIEW --
never auto-failed -- because a disagreement is either (a) the model
being wrong, which we want to know, or (b) the hand label being wrong,
which we ALSO want to know. Both are wins for the demo story.

DRAFT STATUS: the 10 scenarios below are my stand-ins built from the
owner's section-5 titles. To swap in the owner's real scenarios:
  1. write them to ml_sensor/eval_scenarios.json as a list of objects,
     each with the 14 incident fields + "expected_action",
  2. re-run this module. The file prefers the JSON when it exists and
     says so loudly. DRAFTS are only used when the JSON is absent.

Safety rails built in:
  - CONTAMINATION GUARD: every eval scenario is checked against the
    4000 generated training rows; identical feature signature -> hard
    error. The eval suite must be data the generator never made.
  - hand labels pass through normalize_action (the same alias ladder
    the API uses), so an owner label like "reduce_speed_to_50kmh"
    maps DOWN to the 4-action vocabulary instead of failing.
  - normalization of weather ("dry" -> "clear") happens inside the
    engine's boundary, exactly as in production. The eval suite tests
    the production path, not a parallel one.

Run:  python -m ml_sensor.eval_scenarios
      -> console table + ml_sensor/model/eval_report.json

Layer rules: pure Python + the engine. No fastapi, no sqlmodel.
"""

from __future__ import annotations

import json
from pathlib import Path

from ml_sensor.decide import DecisionEngine
from ml_sensor.scenarios import (FEATURE_COLUMNS, RAW_FIELD_ORDER,
                                  SEED, build_dataset, encode_features,
                                  normalize_action)

EVAL_JSON_PATH = Path("ml_sensor/eval_scenarios.json")   # owner's real data
REPORT_PATH = Path("ml_sensor/model/eval_report.json")
TARGET_AGREEMENT = 7          # of 10 -- locked target
N_TRAIN_ROWS = 4000

# =====================================================================
# DRAFT scenarios (stand-ins -- owner swaps via eval_scenarios.json)
# =====================================================================
# Each entry: the 14 incident fields + expected_action (hand label).
# Hand labels were derived by tracing the rule ladder on paper:
#   1  landslide/heavy_rain/120kmh  -> rung 2 (can stop, sev 9) -> e-stop
#   2  freight axle miscount        -> benign + high SQ + no alert -> caution
#   3  fog false positive           -> benign + high SQ -> caution
#   4  200kmh equipment failure     -> rung 1 (can't stop, no arb) -> e-stop
#   5  snow + broken rail           -> rung 2 (can stop, sev 9) -> e-stop
#   6  ARB caution                  -> sev 7 + arb + long-clearing -> reroute
#   7  cable theft                  -> rung 4 (sev 5) -> reduce
#   8  fog miscount high speed      -> not calm (alert) -> reduce (capped)
#   9  flooding                     -> rung 4 (sev 6, no arb) -> reduce
#  10  unknown obstruction          -> sev 7, not long-clearing -> reduce
# Scenario 2 deliberately carries weather "dry" to exercise the
# dry->clear boundary normalization inside the engine.

DRAFT_SCENARIOS: list[dict] = [
    {
        "id": "ev01", "title": "landslide in heavy rain at 120 km/h",
        "train_speed_kmh": 120.0, "distance_to_obstacle_km": 8.5,
        "environmental_condition": "heavy_rain", "weather_alert": True,
        "signal_quality_percent": 45.0, "severity_score": 9,
        "obstruction_type": "landslide_debris",
        "alternative_route_available": False,
        "communication_latency_ms": 1200, "axle_balance": None,
        "ahead_section_status": "CLEAR", "known_train_schedule": True,
        "distance_from_station_km": 6.0, "sensor_type": "track_circuit",
        "expected_action": "emergency_stop",
    },
    {
        "id": "ev02", "title": "freight train, axle counter miscount",
        "train_speed_kmh": 60.0, "distance_to_obstacle_km": 11.0,
        "environmental_condition": "dry", "weather_alert": False,
        "signal_quality_percent": 88.0, "severity_score": 3,
        "obstruction_type": "sensor_miscount",
        "alternative_route_available": False,
        "communication_latency_ms": 400,
        "axle_balance": 1.15,   # imbalanced -> sensor suspect, caps apply
        "ahead_section_status": "CLEAR", "known_train_schedule": True,
        "distance_from_station_km": 4.0, "sensor_type": "axle_counter",
        "expected_action": "proceed_with_caution",
    },
    {
        "id": "ev03", "title": "fog, likely environmental false positive",
        "train_speed_kmh": 75.0, "distance_to_obstacle_km": 9.0,
        "environmental_condition": "fog", "weather_alert": False,
        "signal_quality_percent": 72.0, "severity_score": 2,
        "obstruction_type": "environmental_false_positive",
        "alternative_route_available": False,
        "communication_latency_ms": 350, "axle_balance": None,
        "ahead_section_status": "CLEAR", "known_train_schedule": True,
        "distance_from_station_km": 8.0, "sensor_type": "vibration",
        "expected_action": "proceed_with_caution",
    },
    {
        "id": "ev04", "title": "200 km/h, equipment failure ahead, no room",
        # braking at 200km/h clear = (2.0)^2 * 2.0 = 8.0 km; effective
        # ~4.96 km -> CANNOT stop, no alternate -> rung 1 physics
        "train_speed_kmh": 200.0, "distance_to_obstacle_km": 5.0,
        "environmental_condition": "clear", "weather_alert": False,
        "signal_quality_percent": 90.0, "severity_score": 8,
        "obstruction_type": "equipment_failure_ahead",
        "alternative_route_available": False,
        "communication_latency_ms": 800, "axle_balance": None,
        "ahead_section_status": "CLEAR", "known_train_schedule": True,
        "distance_from_station_km": 12.0, "sensor_type": "track_circuit",
        "expected_action": "emergency_stop",
    },
    {
        "id": "ev05", "title": "snow, broken rail detected",
        # braking = (1.1)^2 * 2.0 * 1.9 = 4.598; effective ~7.9 -> can
        # stop; sev 9 -> rung 2 e-stop; broken_rail floor anyway
        "train_speed_kmh": 110.0, "distance_to_obstacle_km": 8.0,
        "environmental_condition": "snow", "weather_alert": True,
        "signal_quality_percent": 65.0, "severity_score": 9,
        "obstruction_type": "broken_rail",
        "alternative_route_available": False,
        "communication_latency_ms": 900, "axle_balance": None,
        "ahead_section_status": "OCCUPIED", "known_train_schedule": True,
        "distance_from_station_km": 10.0, "sensor_type": "accelerometer",
        "expected_action": "emergency_stop",
    },
    {
        "id": "ev06", "title": "landslide, alternate route exists, sev 7",
        # can stop; sev 7 + arb + long-clearing type -> reroute
        "train_speed_kmh": 90.0, "distance_to_obstacle_km": 10.0,
        "environmental_condition": "rain", "weather_alert": True,
        "signal_quality_percent": 70.0, "severity_score": 7,
        "obstruction_type": "landslide_debris",
        "alternative_route_available": True,
        "communication_latency_ms": 600, "axle_balance": None,
        "ahead_section_status": "CLEAR", "known_train_schedule": True,
        "distance_from_station_km": 5.0, "sensor_type": "track_circuit",
        "expected_action": "reroute",
    },
    {
        "id": "ev07", "title": "signal cable theft on the corridor",
        "train_speed_kmh": 80.0, "distance_to_obstacle_km": 12.0,
        "environmental_condition": "clear", "weather_alert": False,
        "signal_quality_percent": 55.0, "severity_score": 5,
        "obstruction_type": "signal_cable_theft",
        "alternative_route_available": False,
        "communication_latency_ms": 250, "axle_balance": None,
        "ahead_section_status": "CLEAR", "known_train_schedule": False,
        "distance_from_station_km": 3.0, "sensor_type": "axle_counter",
        "expected_action": "reduce_speed",
    },
    {
        "id": "ev08", "title": "fog, axle miscount, high speed",
        # can stop (fog braking 1.1x); benign type BUT weather alert set
        # -> not calm -> reduce_speed; axle cap keeps it at reduce
        "train_speed_kmh": 150.0, "distance_to_obstacle_km": 6.5,
        "environmental_condition": "fog", "weather_alert": True,
        "signal_quality_percent": 68.0, "severity_score": 3,
        "obstruction_type": "sensor_miscount",
        "alternative_route_available": False,
        "communication_latency_ms": 700,
        "axle_balance": 1.19,
        "ahead_section_status": "CLEAR", "known_train_schedule": True,
        "distance_from_station_km": 9.0, "sensor_type": "axle_counter",
        "expected_action": "reduce_speed",
    },
    {
        "id": "ev09", "title": "flooding across the track",
        # braking = (0.7)^2*2*1.7 = 1.666; effective ~3.85 -> can stop;
        # sev 6, no arb -> rung 4 reduce_speed
        "train_speed_kmh": 70.0, "distance_to_obstacle_km": 4.0,
        "environmental_condition": "flood", "weather_alert": True,
        "signal_quality_percent": 60.0, "severity_score": 6,
        "obstruction_type": "water_logging",
        "alternative_route_available": False,
        "communication_latency_ms": 500, "axle_balance": None,
        "ahead_section_status": "CLEAR", "known_train_schedule": True,
        "distance_from_station_km": 2.0, "sensor_type": "vibration",
        "expected_action": "reduce_speed",
    },
    {
        "id": "ev10", "title": "unknown obstruction, moderate severity",
        # can stop; sev 7 but unknown_obstruction is NOT long-clearing
        # -> reduce_speed (even with an alternate route)
        "train_speed_kmh": 100.0, "distance_to_obstacle_km": 7.0,
        "environmental_condition": "clear", "weather_alert": False,
        "signal_quality_percent": 78.0, "severity_score": 7,
        "obstruction_type": "unknown_obstruction",
        "alternative_route_available": True,
        "communication_latency_ms": 450, "axle_balance": None,
        "ahead_section_status": "OCCUPIED", "known_train_schedule": False,
        "distance_from_station_km": 7.5, "sensor_type": "accelerometer",
        "expected_action": "reduce_speed",
    },
]

DRAFT_IDS = {s["id"] for s in DRAFT_SCENARIOS}


# =====================================================================
# Feature signatures (v2: None-safe)
# =====================================================================

def _sig(feats: dict) -> tuple:
    """Feature signature for contamination matching.

    v2 fix: axle_balance is LEGITIMATELY None in ~35% of scenarios
    (that nullness is itself a feature -- the missing indicator), so
    the signature must carry None through as None, not round() it.
    Tuple comparison handles None fine: (None,) == (None,) is True,
    None == 1.0 is False. Never assume every feature column is
    numeric -- the contract says otherwise.
    """
    return tuple(
        None if feats[c] is None else round(float(feats[c]), 6)
        for c in FEATURE_COLUMNS
    )


# =====================================================================
# Loading: owner JSON wins, drafts are the fallback
# =====================================================================

def load_scenarios() -> tuple[list[dict], bool]:
    """Returns (scenarios, is_draft). If the owner's
    ml_sensor/eval_scenarios.json exists, it is used and is_draft is
    False. Each scenario MUST carry expected_action; anything else is
    a hard error -- an unlabeled eval scenario is worthless."""
    if EVAL_JSON_PATH.exists():
        raw = json.loads(EVAL_JSON_PATH.read_text())
        if isinstance(raw, dict):        # tolerate {"scenarios": [...]}
            raw = raw.get("scenarios", raw)
        scenarios = []
        for i, entry in enumerate(raw):
            label = entry.pop("expected_action", None) or entry.pop(
                "expected_label", None) or entry.pop("label", None)
            if label is None:
                raise ValueError(
                    f"eval_scenarios.json entry {i} has no "
                    f"expected_action/label -- unlabeled eval rows are "
                    f"refused, not guessed")
            norm = normalize_action(str(label))
            if norm is None:
                raise ValueError(
                    f"eval_scenarios.json entry {i}: unknown expected "
                    f"action {label!r} -- normalize it into the 4-action "
                    f"vocabulary first")
            entry = dict(entry)
            entry["expected_action"] = norm
            entry.setdefault("id", f"ev{i+1:02d}")
            entry.setdefault("title", entry.get("id"))
            scenarios.append(entry)
        print(f"using OWNER scenarios from {EVAL_JSON_PATH} "
              f"({len(scenarios)} rows)")
        return scenarios, False
    print("no eval_scenarios.json found -- using DRAFT stand-ins "
          "(owner: paste your 10 scenarios as JSON to swap)")
    return DRAFT_SCENARIOS, True


# =====================================================================
# Contamination guard
# =====================================================================

def check_contamination(scenarios: list[dict]) -> None:
    """No eval scenario may equal any training row, on the encoded
    feature signature. This is the 'data no generator made' promise,
    enforced mechanically instead of remembered."""
    train = build_dataset(N_TRAIN_ROWS, SEED)
    train_sigs = {_sig(encode_features(sc)) for sc in train}
    for ev in scenarios:
        if _sig(encode_features(ev)) in train_sigs:
            raise AssertionError(
                f"CONTAMINATION: eval scenario {ev.get('id')} is "
                f"identical to a generated training row -- the held-out "
                f"suite must contain data the generator never made")


# =====================================================================
# The run
# =====================================================================

def run_eval(engine: DecisionEngine | None = None,
             scenarios: list[dict] | None = None,
             is_draft: bool | None = None) -> dict:
    if engine is None:
        engine = DecisionEngine()
    if scenarios is None or is_draft is None:
        scenarios, is_draft = load_scenarios()
    check_contamination(scenarios)

    rows: list[dict] = []
    for ev in scenarios:
        incident = {k: ev[k] for k in RAW_FIELD_ORDER}
        decision = engine.decide(incident)
        agree = decision["action"] == ev["expected_action"]
        rows.append({
            "id": ev.get("id"), "title": ev.get("title"),
            "expected_action": ev["expected_action"],
            "engine_action": decision["action"],
            "source": decision["source"],
            "confidence": decision["confidence"],
            "agreed": agree,
            "r1_fired": decision["source"] == "hard_rule",
            "decision_latency_ms": decision["decision_latency_ms"],
            "physics": decision["physics"],
            "reasons": decision["reasons"],
        })

    n = len(rows)
    n_agree = sum(1 for r in rows if r["agreed"])
    disagreements = [r for r in rows if not r["agreed"]]
    report = {
        "is_draft": is_draft,
        "n_scenarios": n,
        "n_agree": n_agree,
        "agreement_rate": round(n_agree / n, 4) if n else 0.0,
        "target": TARGET_AGREEMENT,
        "target_met": n_agree >= TARGET_AGREEMENT,
        "note": ("disagreements are listed for OWNER REVIEW, never "
                 "auto-failed -- a disagreement is either the model or "
                 "the hand label being wrong, and both are findings"),
        "rows": rows,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    return report


def _print_report(report: dict) -> None:
    print("\n=== RailGuard held-out eval (10 hand scenarios) ===")
    print(f"source: {'DRAFT stand-ins (owner JSON not yet pasted)' if report['is_draft'] else 'OWNER scenarios'}")
    print(f"\n{'id':<6}{'expected':<22}{'engine':<22}"
          f"{'source':<15}{'ok'}")
    for r in report["rows"]:
        mark = "YES" if r["agreed"] else "no  <-- review"
        print(f"{r['id']:<6}{r['expected_action']:<22}"
              f"{r['engine_action']:<22}{r['source']:<15}{mark}")
    n, a = report["n_scenarios"], report["n_agree"]
    verdict = "MET" if report["target_met"] else "NOT MET"
    print(f"\nagreement: {a}/{n} (target {report['target']}/10): {verdict}")

    bad = [r for r in report["rows"] if not r["agreed"]]
    if bad:
        print(f"\n--- {len(bad)} disagreement(s) for owner review ---")
        for r in bad:
            print(f"\n{r['id']} ({r['title']}): expected "
                  f"{r['expected_action']}, engine said "
                  f"{r['engine_action']} (source={r['source']}, "
                  f"confidence={r['confidence']})")
            print(f"  physics: {r['physics']}")
            for reason in r["reasons"]:
                print(f"  - {reason}")
    print(f"\nwrote {REPORT_PATH}")


def main() -> None:
    report = run_eval()
    _print_report(report)
    if report["is_draft"]:
        print("\nDRAFT REMINDER: these are stand-ins. Paste your real 10 "
              "scenarios to ml_sensor/eval_scenarios.json and re-run; "
              "this file will prefer yours automatically.")


if __name__ == "__main__":
    main()

