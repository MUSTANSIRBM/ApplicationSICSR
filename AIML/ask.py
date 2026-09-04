"""
ask.py -- one-command incident testing for RailGuard (v2).

Prints reasons AND the evidence panel (why the model chose this,
as numbers). The script OWNS both the request and the display, so
the display can never drift from the request.

Usage:
    python ask.py 'JSON_BODY'
    python ask.py --preset anchor|wall|caution
    python ask.py --preset anchor --defect --corridor ET-NGP
"""

from __future__ import annotations

import argparse
import json
import urllib.request

API = "http://localhost:8000/api/incident"

PRESETS = {
    "anchor": {
        "title": "THE ANCHOR (120 km/h, landslide, heavy rain, sev 9)",
        "body": {
            "train_speed_kmh": 120, "distance_to_obstacle_km": 8.5,
            "environmental_condition": "heavy_rain", "weather_alert": True,
            "signal_quality_percent": 45, "severity_score": 9,
            "obstruction_type": "landslide_debris",
            "alternative_route_available": False,
            "communication_latency_ms": 1200, "axle_balance": None,
            "ahead_section_status": "CLEAR", "known_train_schedule": True,
            "distance_from_station_km": 6.0, "sensor_type": "track_circuit",
        },
    },
    "wall": {
        "title": "THE WALL (180 km/h, snow, 3 km, sev 9 -- R1 territory)",
        "body": {
            "train_speed_kmh": 180, "distance_to_obstacle_km": 3.0,
            "environmental_condition": "snow", "weather_alert": True,
            "signal_quality_percent": 80, "severity_score": 9,
            "obstruction_type": "landslide_debris",
            "alternative_route_available": False,
            "communication_latency_ms": 300, "axle_balance": None,
            "ahead_section_status": "CLEAR", "known_train_schedule": True,
            "distance_from_station_km": 5.0, "sensor_type": "track_circuit",
        },
    },
    "caution": {
        "title": "CALM (60 km/h, cattle, clear, sev 3)",
        "body": {
            "train_speed_kmh": 60, "distance_to_obstacle_km": 12.0,
            "environmental_condition": "clear", "weather_alert": False,
            "signal_quality_percent": 98, "severity_score": 3,
            "obstruction_type": "cattle_crossing",
            "alternative_route_available": False,
            "communication_latency_ms": 150, "axle_balance": None,
            "ahead_section_status": "CLEAR", "known_train_schedule": False,
            "distance_from_station_km": 4.0, "sensor_type": "axle_counter",
        },
    },
}


def post(body: dict) -> dict:
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def show(title: str, body: dict, data: dict) -> None:
    speed = body["train_speed_kmh"]

    print("=" * 60)
    print(f"RAILGUARD  |  {title}")
    print(f"input     : {speed} km/h, {body['obstruction_type']}, "
          f"sev {body['severity_score']}, "
          f"{body['environmental_condition']}")
    print("=" * 60)
    print(f"ACTION     : {data['action']}")
    print(f"CONFIDENCE : {data['confidence']}")
    print(f"SOURCE     : {data['source']}")
    print(f"LATENCY    : {data['decision_latency_ms']} ms (budget 100)")
    print("-" * 60)
    print("WHY (reasons):")
    for r in data["reasons"]:
        print(f"  - {r}")

    ev = data.get("evidence")
    if ev:
        print("-" * 60)
        print("WHY (evidence -- input vs training patterns):")
        print(f"  {ev['summary']}")
        for e in ev["features"]:
            print(f"  - {e['reads']}")
    else:
        print("  (no numeric evidence -- rule decided, not the model)")

    p = data["physics"]
    print("-" * 60)
    print("PHYSICS:")
    print(f"  Time to obstacle   : {p['time_to_obstacle_min']} min")
    print(f"  Braking distance   : {p['braking_distance_required_km']} km")
    print(f"  Effective distance : {p['effective_distance_km']} km")
    print(f"  Safe to stop       : {p['safe_stopping_possible']}")
    if "speed_advisory" in p:
        adv = p["speed_advisory"]
        v = adv["recommended_speed_kmh"]
        print("  SPEED ADVISORY     : "
              + (f"{speed} km/h -> {v} km/h (reduce by {speed - v})"
                 if v is not None else adv["basis"]))

    print("-" * 60)
    print("PROBABILITIES:")
    for action, prob in (data["probabilities"] or {}).items():
        bar = "#" * int((prob or 0) * 40)
        print(f"  {action:22} {prob * 100:5.1f}% {bar}")
    if data["probabilities"] is None:
        print("  (none -- the model was never consulted)")
    if data.get("repair_defect"):
        rd = data["repair_defect"]
        print("-" * 60)
        print(f"BRIDGE     : {rd['source_ref']} -> {rd['department']}, "
              f"sev {rd['severity']}/5, safety={rd['safety_flag']}, "
              f"{rd['base_duration_min']} min")
    print("=" * 60)


def main() -> None:
    ap = argparse.ArgumentParser(description="Test RailGuard /api/incident")
    ap.add_argument("json", nargs="?", help="inline JSON body")
    ap.add_argument("-f", "--file", help="JSON body from file")
    ap.add_argument("--preset", choices=sorted(PRESETS))
    ap.add_argument("--title", default="custom incident")
    ap.add_argument("--defect", action="store_true")
    ap.add_argument("--corridor", default="ET-NGP")
    args = ap.parse_args()

    if args.preset:
        title, body = PRESETS[args.preset]["title"], dict(PRESETS[args.preset]["body"])
    elif args.file:
        body = json.loads(open(args.file).read())
        title = args.title
    elif args.json:
        body = json.loads(args.json)
        title = args.title
    else:
        ap.error("give a JSON body, -f file, or --preset")

    if args.defect:
        body["create_repair_defect"] = True
        body["corridor"] = args.corridor

    data = post(body)
    show(title, body, data)


if __name__ == "__main__":
    main()
