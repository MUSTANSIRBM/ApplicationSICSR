# AIML/ml_sensor/eval_handcrafted.py
"""
Hand-crafted evaluation scenarios for testing edge cases.
Runs 10 specific scenarios through the DecisionEngine and prints results.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

# Now imports work
from app.core.incident_models import IncidentRequest
from app.core.decision_engine import DecisionEngine


def run_test_case(name: str, request_data: dict, expected_action: str = None):
    """Run a single test case through the DecisionEngine."""
    print(f"\n{'=' * 60}")
    print(f"🧪 Test: {name}")
    print(f"{'=' * 60}")

    try:
        request = IncidentRequest(**request_data)
        engine = DecisionEngine()
        response = engine.evaluate(request)

        print(f"📊 Input Summary:")
        print(f"   Speed: {request.train_speed_kmh} km/h")
        print(f"   Distance: {request.distance_to_obstacle_km} km")
        print(f"   Weather: {request.environmental_condition}")
        print(f"   Severity: {request.severity_score}/10")
        print(f"   Obstruction: {request.obstruction_type}")

        print(f"\n📈 Physics:")
        print(f"   Braking Distance: {response.physics.braking_distance_required_km} km")
        print(f"   Safe Stopping: {response.physics.safe_stopping_possible}")

        print(f"\n🤖 Decision:")
        print(f"   Action: {response.decision.action}")
        print(f"   Confidence: {response.decision.confidence:.2f}")
        print(f"   Source: {response.decision.source}")
        print(f"   Reasons: {', '.join(response.decision.reasons)}")

        if response.repair_defect_id:
            print(f"   🔗 Defect ID: {response.repair_defect_id}")

        if expected_action:
            status = "✅ PASS" if response.decision.action == expected_action else "❌ FAIL"
            print(f"\n   Expected: {expected_action} → {status}")

        return response

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all 10 hand-crafted test scenarios."""
    print("\n" + "=" * 60)
    print("🚀 HAND-CRAFTED EVALUATION SCENARIOS")
    print("=" * 60)

    # Test 1: Emergency Stop via Hard Rule
    run_test_case(
        "1. High Speed + Heavy Rain + Severity 9 + No Alternate → Emergency Stop",
        {
            "train_speed_kmh": 180,
            "distance_to_obstacle_km": 1.5,
            "environmental_condition": "heavy_rain",
            "weather_alert": True,
            "severity_score": 9,
            "obstruction_type": "landslide_debris",
            "alternative_route_available": False,
            "communication_latency_ms": 100,
            "signal_quality_percent": 85,
            "sensor_type": "track_circuit",
            "axle_balance": None,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": True,
            "distance_from_station_km": 5.0,
            "create_repair_defect": True,
            "corridor": "DEL-AGRA"
        },
        expected_action="emergency_stop"
    )

    # Test 2: Proceed with Caution
    run_test_case(
        "2. Low Speed + Clear + Severity 2 + Cattle Crossing → Proceed with Caution",
        {
            "train_speed_kmh": 50,
            "distance_to_obstacle_km": 15.0,
            "environmental_condition": "clear",
            "weather_alert": False,
            "severity_score": 2,
            "obstruction_type": "cattle_crossing",
            "alternative_route_available": True,
            "communication_latency_ms": 50,
            "signal_quality_percent": 95,
            "sensor_type": "vibration",
            "axle_balance": 50.0,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": True,
            "distance_from_station_km": 15.0,
            "create_repair_defect": False,
            "corridor": "MUM-PUNE"
        },
        expected_action="proceed_with_caution"
    )

    # Test 3: Reroute
    run_test_case(
        "3. Medium Speed + Fog + Severity 6 + Alternate Route → Reroute",
        {
            "train_speed_kmh": 100,
            "distance_to_obstacle_km": 8.0,
            "environmental_condition": "fog",
            "weather_alert": True,
            "severity_score": 6,
            "obstruction_type": "fallen_tree",
            "alternative_route_available": True,
            "communication_latency_ms": 150,
            "signal_quality_percent": 70,
            "sensor_type": "track_circuit",
            "axle_balance": None,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": False,
            "distance_from_station_km": 8.0,
            "create_repair_defect": False,
            "corridor": "KOL-HOW"
        },
        expected_action="reroute"
    )

    # Test 4: Reduce Speed
    run_test_case(
        "4. High Speed + Snow + Severity 8 + Safe Stopping → Reduce Speed",
        {
            "train_speed_kmh": 150,
            "distance_to_obstacle_km": 10.0,
            "environmental_condition": "snow",
            "weather_alert": True,
            "severity_score": 8,
            "obstruction_type": "track_buckling",
            "alternative_route_available": False,
            "communication_latency_ms": 200,
            "signal_quality_percent": 60,
            "sensor_type": "accelerometer",
            "axle_balance": 45.0,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": True,
            "distance_from_station_km": 3.0,
            "create_repair_defect": True,
            "corridor": "HYB-SEC"
        },
        expected_action="reduce_speed"
    )

    # Test 5: "dry" → "clear" normalization
    run_test_case(
        "5. 'dry' Environmental Condition → Normalizes to 'clear'",
        {
            "train_speed_kmh": 80,
            "distance_to_obstacle_km": 12.0,
            "environmental_condition": "dry",  # Should normalize to clear
            "weather_alert": False,
            "severity_score": 3,
            "obstruction_type": "boulder",
            "alternative_route_available": True,
            "communication_latency_ms": 100,
            "signal_quality_percent": 90,
            "sensor_type": "vibration",
            "axle_balance": None,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": True,
            "distance_from_station_km": 10.0,
            "create_repair_defect": False,
            "corridor": "CHN-BGLR"
        },
        expected_action="proceed_with_caution"
    )

    # Test 6: High Latency → Emergency Stop
    run_test_case(
        "6. High Latency (4000ms) + Close Distance → Emergency Stop",
        {
            "train_speed_kmh": 120,
            "distance_to_obstacle_km": 2.0,
            "environmental_condition": "clear",
            "weather_alert": False,
            "severity_score": 7,
            "obstruction_type": "broken_rail",
            "alternative_route_available": False,
            "communication_latency_ms": 4000,
            "signal_quality_percent": 50,
            "sensor_type": "track_circuit",
            "axle_balance": None,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": True,
            "distance_from_station_km": 1.0,
            "create_repair_defect": True,
            "corridor": "DEL-AGRA"
        },
        expected_action="emergency_stop"
    )

    # Test 7: Occupied Section Ahead → Emergency Stop
    run_test_case(
        "7. Occupied Section Ahead + Distance < 2km → Emergency Stop",
        {
            "train_speed_kmh": 100,
            "distance_to_obstacle_km": 1.5,
            "environmental_condition": "clear",
            "weather_alert": False,
            "severity_score": 5,
            "obstruction_type": "stranded_vehicle",
            "alternative_route_available": False,
            "communication_latency_ms": 50,
            "signal_quality_percent": 95,
            "sensor_type": "axle_counter",
            "axle_balance": 60.0,
            "ahead_section_status": "OCCUPIED",
            "known_train_schedule": False,
            "distance_from_station_km": 2.0,
            "create_repair_defect": False,
            "corridor": "MUM-PUNE"
        },
        expected_action="emergency_stop"
    )

    # Test 8: Severity 10 + Safe + Alternate → Not Forced Emergency
    run_test_case(
        "8. Severity 10 + Safe Stopping + Alternate Route → Reroute or Reduce Speed",
        {
            "train_speed_kmh": 60,
            "distance_to_obstacle_km": 15.0,
            "environmental_condition": "clear",
            "weather_alert": False,
            "severity_score": 10,
            "obstruction_type": "signal_cable_theft",
            "alternative_route_available": True,
            "communication_latency_ms": 50,
            "signal_quality_percent": 90,
            "sensor_type": "track_circuit",
            "axle_balance": None,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": True,
            "distance_from_station_km": 10.0,
            "create_repair_defect": True,
            "corridor": "KOL-HOW"
        }
    )

    # Test 9: Sensor Miscount + Unknown Schedule → Proceed with Caution
    run_test_case(
        "9. Sensor Miscount + Unknown Schedule → Proceed with Caution",
        {
            "train_speed_kmh": 80,
            "distance_to_obstacle_km": 12.0,
            "environmental_condition": "clear",
            "weather_alert": False,
            "severity_score": 3,
            "obstruction_type": "sensor_miscount",
            "alternative_route_available": True,
            "communication_latency_ms": 100,
            "signal_quality_percent": 60,
            "sensor_type": "vibration",
            "axle_balance": 30.0,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": False,
            "distance_from_station_km": 8.0,
            "create_repair_defect": False,
            "corridor": "HYB-SEC"
        },
        expected_action="proceed_with_caution"
    )

    # Test 10: Flood + Severity 7 + Very Close → Emergency Stop
    run_test_case(
        "3. Medium Speed + Fog + Severity 6 + Alternate Route → Hard Rule (Reduce Speed)",
        {
            "train_speed_kmh": 100,
            "distance_to_obstacle_km": 8.0,
            "environmental_condition": "fog",
            "weather_alert": True,
            "severity_score": 6,
            "obstruction_type": "fallen_tree",
            "alternative_route_available": True,
            "communication_latency_ms": 150,
            "signal_quality_percent": 70,
            "sensor_type": "track_circuit",
            "axle_balance": None,
            "ahead_section_status": "CLEAR",
            "known_train_schedule": False,
            "distance_from_station_km": 8.0,
            "create_repair_defect": False,
            "corridor": "KOL-HOW"
        },
        expected_action="reduce_speed"  # Hard rule overrides reroute
    )

    print("\n" + "=" * 60)
    print("✅ All test cases completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()