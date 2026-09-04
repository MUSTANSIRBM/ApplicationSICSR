# AIML/ml_sensor/generate_scenarios.py
import random
import pandas as pd
import numpy as np
from pathlib import Path

# Constants
NUM_SAMPLES = 4000
OUTPUT_PATH = Path(__file__).parent / "training_data.csv"
SEED = 42

random.seed(SEED)
np.random.seed(SEED)

# Updated weather friction multipliers
WEATHER_FRICTION = {
    "clear": 1.0,
    "rain": 1.3,
    "heavy_rain": 1.6,
    "fog": 1.2,
    "snow": 1.9,
    "flood": 1.7,
}

# Weather distribution weights
WEATHER_WEIGHTS = {
    "clear": 0.30,
    "rain": 0.20,
    "heavy_rain": 0.12,
    "fog": 0.13,
    "snow": 0.12,
    "flood": 0.13,
}

# Expanded obstruction types (13 total)
OBSTRUCTION_TYPES = [
    "landslide_debris",
    "boulder",
    "track_buckling",
    "fallen_tree",
    "stranded_vehicle",
    "water_logging",
    "cattle_crossing",
    "broken_rail",
    "signal_cable_theft",
    "sensor_miscount",
    "environmental_false_positive",
    "unknown_obstruction",
    "equipment_failure_ahead"
]

# Sensor types
SENSOR_TYPES = ["track_circuit", "axle_counter", "vibration", "accelerometer"]

# Corridors
CORRIDORS = ["DEL-AGRA", "MUM-PUNE", "KOL-HOW", "CHN-BGLR", "HYB-SEC"]


def calculate_physics(train_speed_kmh, distance_to_obstacle_km, environmental_condition, communication_latency_ms):
    """Calculate physics metrics using updated formula."""
    friction = WEATHER_FRICTION.get(environmental_condition, 1.0)
    # Updated formula: ((speed / 100) ** 2) * 2.0 * friction
    braking_distance = ((train_speed_kmh / 100) ** 2) * 2.0 * friction
    latency_impact = (communication_latency_ms / 1000) * (train_speed_kmh / 3.6)
    effective_distance = max(0, distance_to_obstacle_km - latency_impact)
    safe_stopping = effective_distance >= (braking_distance + 0.5)
    return braking_distance, effective_distance, safe_stopping


def generate_ground_truth(row):
    """Generate ground truth label based on physics and hard rules."""
    speed = row['train_speed_kmh']
    distance = row['distance_to_obstacle_km']
    weather = row['environmental_condition']
    latency = row['communication_latency_ms']
    severity = row['severity_score']
    alternative = row['alternative_route_available']
    section_status = row['ahead_section_status']
    weather_alert = row['weather_alert']

    # Calculate physics with updated formula
    friction = WEATHER_FRICTION.get(weather, 1.0)
    braking_distance = ((speed / 100) ** 2) * 2.0 * friction
    latency_impact = (latency / 1000) * (speed / 3.6)
    effective_distance = max(0, distance - latency_impact)
    safe_stopping = effective_distance >= (braking_distance + 0.5)

    # Updated Hard Rule 1: severity >= 9 (not 8)
    if severity >= 9 and not safe_stopping and not alternative:
        return "emergency_stop"

    # Hard Rule 2: Weather alert + poor visibility → reduce_speed
    if weather_alert and weather in ["fog", "heavy_rain", "snow"]:
        return "reduce_speed"

    # Hard Rule 3: Obstruction + occupied section ahead → emergency_stop
    if section_status == "OCCUPIED" and distance < 2.0:
        return "emergency_stop"

    # Rule-based fallback logic
    if severity >= 6 and not safe_stopping:
        if distance < 1.0:
            return "emergency_stop"
        else:
            return "reduce_speed"

    if alternative and severity >= 5:
        return "reroute"

    return "proceed_with_caution"


def generate_scenario():
    """Generate one synthetic scenario with all 16 features."""
    weather = random.choices(
        list(WEATHER_WEIGHTS.keys()),
        weights=list(WEATHER_WEIGHTS.values())
    )[0]

    return {
        'train_speed_kmh': random.randint(45, 200),
        'distance_to_obstacle_km': round(random.uniform(0, 20), 3),
        'environmental_condition': weather,
        'weather_alert': random.random() < (0.3 if weather == "clear" else 0.6),
        'severity_score': random.choices(range(1, 11), weights=[5, 8, 12, 15, 18, 18, 12, 8, 3, 1])[0],
        'obstruction_type': random.choice(OBSTRUCTION_TYPES),
        'alternative_route_available': random.random() < 0.3,
        'communication_latency_ms': random.randint(10, 5000),
        'signal_quality_percent': random.randint(0, 100),
        'sensor_type': random.choice(SENSOR_TYPES),
        'axle_balance': random.choice([None, round(random.uniform(0, 100), 2)]),
        'ahead_section_status': random.choices(["CLEAR", "OCCUPIED"], weights=[0.7, 0.3])[0],
        'known_train_schedule': random.random() < 0.7,
        'distance_from_station_km': round(random.uniform(0, 50), 3),
        'create_repair_defect': random.random() < 0.2,
        'corridor': random.choice(CORRIDORS),
    }


def generate_dataset(n_samples=NUM_SAMPLES):
    """Generate full dataset with ground truth labels."""
    scenarios = []
    labels = []

    for _ in range(n_samples):
        scenario = generate_scenario()
        label = generate_ground_truth(scenario)

        # Add ~4% random label noise
        if random.random() < 0.04:
            possible = ["proceed_with_caution", "reduce_speed", "reroute", "emergency_stop"]
            possible.remove(label)
            label = random.choice(possible)

        scenarios.append(scenario)
        labels.append(label)

    return pd.DataFrame(scenarios), labels


def main():
    """Generate and save training data."""
    print(f"🌱 Generating {NUM_SAMPLES} synthetic training scenarios...")

    df, labels = generate_dataset(NUM_SAMPLES)
    df['action'] = labels

    df['axle_balance'] = df['axle_balance'].fillna(0.0)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"✅ Saved training data to {OUTPUT_PATH}")
    print(f"📊 Shape: {df.shape}")
    print(f"📈 Action distribution:\n{df['action'].value_counts()}")
    print(f"\n📋 Sample:\n{df.head(3).to_string()}")


if __name__ == "__main__":
    main()