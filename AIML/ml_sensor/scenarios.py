"""
ml_sensor/scenarios.py -- the synthetic world for the sensor module.

Step 1 of 7. This file is the SINGLE SOURCE OF TRUTH for:
  - the action vocabulary (exactly 4, locked -- never extend without
    the owner's sign-off)
  - the 13 obstruction types and their severity bands
  - weather braking multipliers (snow 1.9 / heavy_rain 1.6 locked;
    the rest are confirmed defaults)
  - the physics formulas (braking distance, effective distance,
    safe stopping) -- computed for DISPLAY and for LABELLING only,
    never fed back as model features (locked decision 10/12)
  - the rule-engine ladder that labels training data (decision 10:
    physics-based labels + 4% honest noise)
  - the 16-feature contract that train.py, decide.py and the API all
    import -- one definition kills train/serve drift at the root

Layer rules: pure Python + numpy + pandas only. No fastapi, no
sqlmodel. The leakage wall is enforced downstream by a test that
bans column names by name, not by memory.

Run:  python -m ml_sensor.scenarios
      -> ml_sensor/data/scenarios.csv (openable artifact for judges)
      -> prints class balance, type coverage, noise count, and a
         live check of the demo anchor scenario.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# =====================================================================
# 1. VOCABULARY -- single source of truth
# =====================================================================

# Exactly four actions. This tuple is the whole action space (locked).
ACTIONS: tuple[str, ...] = (
    "proceed_with_caution",
    "reduce_speed",
    "reroute",
    "emergency_stop",
)

# Rank = escalation level. Used only for trust-gate caps/floors, never
# for scoring. 0=calm ... 3=most severe.
ACTION_RANK: dict[str, int] = {a: i for i, a in enumerate(ACTIONS)}

# External action labels normalize DOWN into our vocabulary (locked).
# Unknown strings -> None, and the API turns that into a 422. We never
# silently guess an action -- a guessed action is a guessed crash.
ACTION_ALIASES: dict[str, str] = {
    "reduce_speed_to_50kmh": "reduce_speed",
    "reduce_speed_to_30kmh": "reduce_speed",
    "slow_down": "reduce_speed",
    "proceed_slowly": "proceed_with_caution",
    "caution": "proceed_with_caution",
    "divert": "reroute",
    "reroute_train": "reroute",
    # Flag 5 default: the "safe" mapping. In a 4-action vocabulary with
    # no gentle stop, mapping soft->hard is the recoverable error
    # (a false e-stop costs minutes; a missed stop costs the train).
    # Owner may flip this one line at review.
    "stop_and_verify": "emergency_stop",
    "halt": "emergency_stop",
}


def normalize_action(raw: str) -> str | None:
    """Map any external action label into the 4-action vocabulary.
    Returns None for unknown labels (caller decides: API -> 422)."""
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    if key in ACTIONS:
        return key
    return ACTION_ALIASES.get(key)


# Weather braking multipliers. snow/heavy_rain LOCKED; rest confirmed.
# NOTE: fog (1.1) is deliberately below rain (1.3) -- fog blinds
# sensors (that shows up in signal_quality), it does not lengthen
# braking much. Do not "fix" this ordering.
WEATHER_MULTIPLIERS: dict[str, float] = {
    "clear": 1.0,
    "rain": 1.3,
    "fog": 1.1,
    "heavy_rain": 1.6,
    "snow": 1.9,
    "flood": 1.7,
}

# Locked: external systems may say "dry" -- normalize to "clear"
# at the boundary, exactly once, here.
WEATHER_ALIASES: dict[str, str] = {"dry": "clear"}


def normalize_weather(raw: str) -> str | None:
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    if key in WEATHER_MULTIPLIERS:
        return key
    return WEATHER_ALIASES.get(key)


# 13 obstruction types, each with its locked severity band (inclusive).
OBSTRUCTION_TYPES: dict[str, tuple[int, int]] = {
    "landslide_debris": (7, 10),
    "boulder": (6, 9),
    "track_buckling": (7, 10),
    "fallen_tree": (4, 8),
    "stranded_vehicle": (5, 9),
    "water_logging": (3, 7),
    "cattle_crossing": (1, 4),
    "broken_rail": (8, 10),
    "signal_cable_theft": (4, 7),
    "sensor_miscount": (2, 5),
    "environmental_false_positive": (1, 4),
    "unknown_obstruction": (6, 9),
    "equipment_failure_ahead": (5, 9),
}

# Types whose clear-up takes hours (earthwork, drainage, re-railing):
# worth rerouting around IF an alternate exists (rule-engine rung 3).
LONG_CLEARING_TYPES = frozenset(
    {"landslide_debris", "water_logging", "track_buckling",
     "broken_rail", "stranded_vehicle"}
)

# Low-trust types (flag 4, trust gates): their alerts often are the
# sensor's problem, not the track's. Never escalate past reduce_speed.
BENIGN_TYPES = frozenset(
    {"cattle_crossing", "environmental_false_positive", "sensor_miscount"}
)

# High-danger types (flag 4, trust gates): never de-escalate below
# reduce_speed. Safety floor, not a scoring weight.
NEVER_DE_ESCALATE_TYPES = frozenset(
    {"broken_rail", "landslide_debris", "track_buckling"}
)

# Stable integer codes for tree models. Trees split on codes fine; the
# mapping is persisted inside the trained bundle (train.py) so serving
# never rebuilds it from memory.
OBSTRUCTION_CODES: dict[str, int] = {
    name: i for i, name in enumerate(OBSTRUCTION_TYPES)
}

SENSOR_TYPES: tuple[str, ...] = (
    "track_circuit", "axle_counter", "vibration", "accelerometer",
)
SENSOR_CODES: dict[str, int] = {name: i for i, name in enumerate(SENSOR_TYPES)}

AHEAD_SECTION_STATUS: tuple[str, ...] = ("OCCUPIED", "CLEAR")

# Input ranges (shared by generator now, pydantic validation later).
RANGE_TRAIN_SPEED_KMH = (45.0, 200.0)
RANGE_DISTANCE_KM = (0.0, 20.0)
RANGE_API_LATENCY_MS = (10.0, 5000.0)      # what the API accepts
RANGE_GEN_LATENCY_MS = (50.0, 2000.0)      # what the generator produces
RANGE_SIGNAL_QUALITY = (0.0, 100.0)
RANGE_SEVERITY = (1, 10)
RANGE_STATION_KM = (0.0, 25.0)

# =====================================================================
# 2. FEATURE CONTRACT -- the 16 model columns
# =====================================================================
# Count check (flag 1): 14 form fields + time_to_obstacle (computed
# backend-side from speed/distance) = 15 fields; axle_balance splits
# into value + missing-indicator = 16 feature columns. Exactly 16.
#
# Encoded columns are deliberately RENAMED (e.g. obstruction_type ->
# obstruction_type_code) so a leaked raw/computed column can never
# hide under a familiar name.
FEATURE_COLUMNS: tuple[str, ...] = (
    "train_speed_kmh",
    "distance_to_obstacle_km",
    "time_to_obstacle_min",
    "environmental_braking_multiplier",
    "weather_alert",
    "signal_quality_percent",
    "severity_score",
    "obstruction_type_code",
    "alternative_route_available",
    "communication_latency_ms",
    "axle_balance",
    "axle_balance_missing",
    "ahead_section_occupied",
    "known_train_schedule",
    "distance_from_station_km",
    "sensor_type_code",
)

# The leakage wall, as data: any of these names appearing in a feature
# matrix is a test failure. This is the rejected-external-doc problem
# made executable. (braking_ratio / time_buffer were the leaked design.)
BANNED_FEATURE_NAMES = frozenset(
    {"braking_distance_required_km", "safe_stopping_possible",
     "effective_distance_km", "braking_ratio", "time_buffer"}
)


def encode_features(sc: dict) -> dict[str, float | None]:
    """Turn a scenario's RAW fields into the 16 numeric feature columns.

    axle_balance stays None here (imputation is train.py's job, fit on
    the train split ONLY -- fitting on all 4000 rows is a subtle leak).
    Raises ValueError on unknown weather/type/sensor: strict at the
    boundary, never a silent guess.
    """
    weather = normalize_weather(str(sc["environmental_condition"]))
    if weather is None:
        raise ValueError(f"unknown environmental_condition: {sc['environmental_condition']!r}")
    typ = str(sc["obstruction_type"])
    if typ not in OBSTRUCTION_TYPES:
        raise ValueError(f"unknown obstruction_type: {typ!r}")
    sensor = str(sc["sensor_type"])
    if sensor not in SENSOR_TYPES:
        raise ValueError(f"unknown sensor_type: {sensor!r}")

    balance = sc.get("axle_balance")
    balance = float(balance) if balance is not None else None

    return {
        "train_speed_kmh": float(sc["train_speed_kmh"]),
        "distance_to_obstacle_km": float(sc["distance_to_obstacle_km"]),
        "time_to_obstacle_min": time_to_obstacle_min(
            float(sc["train_speed_kmh"]), float(sc["distance_to_obstacle_km"])
        ),
        # Weather enters as its braking multiplier: one ordered numeric
        # column carrying exactly the weather information that matters
        # physically. No 6-way one-hot to drift between train and serve.
        "environmental_braking_multiplier": WEATHER_MULTIPLIERS[weather],
        "weather_alert": 1.0 if sc.get("weather_alert") else 0.0,
        "signal_quality_percent": float(sc["signal_quality_percent"]),
        "severity_score": float(sc["severity_score"]),
        "obstruction_type_code": float(OBSTRUCTION_CODES[typ]),
        "alternative_route_available": 1.0 if sc.get("alternative_route_available") else 0.0,
        "communication_latency_ms": float(sc["communication_latency_ms"]),
        "axle_balance": balance,
        "axle_balance_missing": 1.0 if balance is None else 0.0,
        "ahead_section_occupied": 1.0 if str(sc["ahead_section_status"]).upper() == "OCCUPIED" else 0.0,
        "known_train_schedule": 1.0 if sc.get("known_train_schedule") else 0.0,
        "distance_from_station_km": float(sc["distance_from_station_km"]),
        "sensor_type_code": float(SENSOR_CODES[sensor]),
    }


def assert_leakage_free(feature_names) -> None:
    """Guard used by tests AND by train.py: the feature set must be
    exactly FEATURE_COLUMNS and must contain nothing banned."""
    names = set(feature_names)
    leaked = names & BANNED_FEATURE_NAMES
    if leaked:
        raise AssertionError(f"LEAKAGE: banned features present: {sorted(leaked)}")
    missing = set(FEATURE_COLUMNS) - names
    extra = names - set(FEATURE_COLUMNS)
    if missing or extra:
        raise AssertionError(
            f"feature contract drift: missing={sorted(missing)} extra={sorted(extra)}"
        )

# =====================================================================
# 3. PHYSICS -- display-only + label-source. Never a model feature.
# =====================================================================

BRAKING_FORMULA_K = 2.0      # (speed/100)^2 * 2.0 * weather_mult  (locked)
SAFETY_MARGIN_KM = 0.3       # locked: eff > braking + 0.3 => can stop


def time_to_obstacle_min(speed_kmh: float, distance_km: float) -> float:
    if speed_kmh <= 0:
        return float("inf")
    return distance_km / speed_kmh * 60.0


def braking_distance_required_km(speed_kmh: float, weather: str) -> float:
    w = normalize_weather(weather) if isinstance(weather, str) else None
    if w is None:
        raise ValueError(f"unknown weather for braking calc: {weather!r}")
    return (speed_kmh / 100.0) ** 2 * BRAKING_FORMULA_K * WEATHER_MULTIPLIERS[w]


def effective_distance_km(distance_km: float, speed_kmh: float,
                          latency_ms: float) -> float:
    """distance minus the ground covered during comms+reaction latency.
    Units are the classic trap (flag 2): km/h * (ms/1000/3600) = km.
    Anchor check: 120 km/h, 1200 ms -> 0.04 km, so 8.5 -> 8.46 km."""
    return distance_km - speed_kmh * (latency_ms / 1000.0) / 3600.0


def safe_stopping_possible(distance_km: float, speed_kmh: float,
                           latency_ms: float, weather: str) -> bool:
    eff = effective_distance_km(distance_km, speed_kmh, latency_ms)
    braking = braking_distance_required_km(speed_kmh, weather)
    return eff > braking + SAFETY_MARGIN_KM


def physics_block(sc: dict) -> dict:
    """The DISPLAY block the frontend renders (locked decision 12):
    computed values shown, never sent back as model inputs."""
    speed = float(sc["train_speed_kmh"])
    dist = float(sc["distance_to_obstacle_km"])
    lat = float(sc["communication_latency_ms"])
    weather = normalize_weather(str(sc["environmental_condition"]))
    if weather is None:
        raise ValueError(f"unknown environmental_condition: {sc['environmental_condition']!r}")
    eff = effective_distance_km(dist, speed, lat)
    braking = braking_distance_required_km(speed, weather)
    return {
        "time_to_obstacle_min": round(time_to_obstacle_min(speed, dist), 2),
        "braking_distance_required_km": round(braking, 3),
        "effective_distance_km": round(eff, 3),
        "safe_stopping_possible": bool(eff > braking + SAFETY_MARGIN_KM),
        "weather_braking_multiplier": WEATHER_MULTIPLIERS[weather],
    }

# =====================================================================
# 4. RULE ENGINE -- label source of truth + the R2 fallback answer
# =====================================================================
# The ladder (flag 4, confirmed). Physics owns the black zones;
# severity rungs own the gray. Trust gates cap/floor afterwards.

BENIGN_SIGNAL_QUALITY_MIN = 60.0   # rung 5: caution needs sq >= 60
AXLE_IMBALANCE_THRESHOLD = 0.08    # |balance - 1| > 0.08 => suspect sensor


def _cap(action: str, ceiling: str) -> str:
    return action if ACTION_RANK[action] <= ACTION_RANK[ceiling] else ceiling


def _floor(action: str, floor: str) -> str:
    return action if ACTION_RANK[action] >= ACTION_RANK[floor] else floor


def _apply_trust_gates(action: str, sc: dict) -> str:
    typ = str(sc["obstruction_type"])
    # Caps: low-trust types never escalate past reduce_speed.
    if typ in BENIGN_TYPES:
        action = _cap(action, "reduce_speed")
    # Floors: high-danger types never de-escalate below reduce_speed.
    if typ in NEVER_DE_ESCALATE_TYPES:
        action = _floor(action, "reduce_speed")
    # Axle imbalance on an axle counter + otherwise calm picture: the
    # sensor is the patient, not the track. Cap at reduce_speed.
    balance = sc.get("axle_balance")
    if (str(sc["sensor_type"]) == "axle_counter" and balance is not None
            and abs(float(balance) - 1.0) > AXLE_IMBALANCE_THRESHOLD):
        action = _cap(action, "reduce_speed")
    return action


def rule_engine_action(sc: dict) -> str:
    """Physics rule engine -> one of the 4 actions.

    INTERPRETATION FLAG (review this): rung 1 (can't stop) BYPASSES the
    trust-gate caps. Rationale: "can't stop" is physics, and decision 9
    says physics owns the black zones -- if braking math says this train
    cannot stop, a 'probably a sensor miscount' discount would be the
    unsafe label. Caps/floors apply to severity-driven rungs 2-5 only.
    Flag me if you want the caps to override rung 1 too.
    """
    can_stop = safe_stopping_possible(
        float(sc["distance_to_obstacle_km"]), float(sc["train_speed_kmh"]),
        float(sc["communication_latency_ms"]), str(sc["environmental_condition"]),
    )
    arb = bool(sc.get("alternative_route_available"))
    sev = int(sc["severity_score"])
    typ = str(sc["obstruction_type"])

    # --- rung 1: physics black zone (mirrors R1 territory) ---
    if not can_stop:
        return "reroute" if arb else "emergency_stop"

    # --- rungs 2-5: severity-driven gray zone ---
    if sev >= 9:
        action = "emergency_stop"
    elif sev >= 7:
        action = ("reroute" if (arb and typ in LONG_CLEARING_TYPES)
                  else "reduce_speed")
    elif sev >= 5:
        action = "reduce_speed"
    else:
        calm = (typ in BENIGN_TYPES
                and float(sc["signal_quality_percent"]) >= BENIGN_SIGNAL_QUALITY_MIN
                and not bool(sc.get("weather_alert")))
        action = "proceed_with_caution" if calm else "reduce_speed"

    return _apply_trust_gates(action, sc)

# =====================================================================
# 5. SEEDED GENERATOR -- 4000 honest synthetic scenarios
# =====================================================================

SEED = 42
N_SCENARIOS = 4000
LABEL_NOISE_FRACTION = 0.04
# Separate rng stream for label noise, so re-ordering generation draws
# can never silently shift which rows get noised. Determinism you can
# reason about, not just determinism you can reproduce.
LABEL_NOISE_SEED = 101

# Realistic weather weighting (sums to 1.0): mostly fine, rarely flood.
WEATHER_WEIGHTS: dict[str, float] = {
    "clear": 0.45, "rain": 0.20, "fog": 0.12,
    "heavy_rain": 0.10, "snow": 0.08, "flood": 0.05,
}

# Type weights (sum to 1.0). Benign types are deliberately over-weighted:
# on a real corridor cattle and sensor miscounts are everyday events --
# and this weighting is also what keeps proceed_with_caution above
# ~12% support so macro-F1 does not starve on a 3% minority class.
TYPE_WEIGHTS: dict[str, float] = {
    "landslide_debris": 0.10, "boulder": 0.08, "track_buckling": 0.06,
    "fallen_tree": 0.09, "stranded_vehicle": 0.05, "water_logging": 0.08,
    "cattle_crossing": 0.12, "broken_rail": 0.04, "signal_cable_theft": 0.05,
    "sensor_miscount": 0.10, "environmental_false_positive": 0.10,
    "unknown_obstruction": 0.07, "equipment_failure_ahead": 0.06,
}

SENSOR_WEIGHTS: dict[str, float] = {
    "track_circuit": 0.40, "axle_counter": 0.25,
    "vibration": 0.20, "accelerometer": 0.15,
}

# Weather alert probability: a flood without an alert is rare; a clear
# day with one is noise. Feeds rung 5's "no alert" condition.
ALERT_PROB_BY_WEATHER: dict[str, float] = {
    "clear": 0.05, "rain": 0.25, "fog": 0.15,
    "heavy_rain": 0.60, "snow": 0.50, "flood": 0.80,
}


def generate_scenarios(n: int = N_SCENARIOS, seed: int = SEED) -> list[dict]:
    """Generate n scenarios with CLEAN rule-engine labels.
    Same seed -> byte-identical scenarios. Draw order is fixed and
    documented: arrays first, then per-row severity/alert draws."""
    rng = np.random.default_rng(seed)

    weather_names = list(WEATHER_MULTIPLIERS)
    weathers = rng.choice(weather_names, size=n,
                          p=[WEATHER_WEIGHTS[w] for w in weather_names])
    type_names = list(OBSTRUCTION_TYPES)
    types = rng.choice(type_names, size=n,
                       p=[TYPE_WEIGHTS[t] for t in type_names])
    sensors = rng.choice(list(SENSOR_TYPES), size=n,
                         p=[SENSOR_WEIGHTS[s] for s in SENSOR_TYPES])

    speeds = rng.uniform(*RANGE_TRAIN_SPEED_KMH, n)
    dists = rng.uniform(0.2, RANGE_DISTANCE_KM[1], n)
    latencies = rng.integers(int(RANGE_GEN_LATENCY_MS[0]),
                             int(RANGE_GEN_LATENCY_MS[1]) + 1, n)
    signal_q = rng.uniform(30.0, 100.0, n)     # skew high -> caution survives
    station_km = rng.uniform(0.5, RANGE_STATION_KM[1], n)
    arb = rng.random(n) < 0.45                 # alternate route ~45%
    scheduled = rng.random(n) < 0.75
    occupied = rng.random(n) < 0.30            # ahead section OCCUPIED 30%
    has_balance = rng.random(n) >= 0.35        # axle_balance null 35%
    balances = np.clip(rng.normal(1.0, 0.06, n), 0.70, 1.30)

    scenarios: list[dict] = []
    for i in range(n):
        lo, hi = OBSTRUCTION_TYPES[types[i]]
        severity = int(rng.integers(lo, hi + 1))          # within the band
        alert = bool(rng.random() < ALERT_PROB_BY_WEATHER[weathers[i]])
        sc = {
            "train_speed_kmh": round(float(speeds[i]), 1),
            "distance_to_obstacle_km": round(float(dists[i]), 2),
            "environmental_condition": str(weathers[i]),
            "weather_alert": alert,
            "signal_quality_percent": round(float(signal_q[i]), 1),
            "severity_score": severity,
            "obstruction_type": str(types[i]),
            "alternative_route_available": bool(arb[i]),
            "communication_latency_ms": int(latencies[i]),
            "axle_balance": (round(float(balances[i]), 4)
                             if has_balance[i] else None),
            "ahead_section_status": "OCCUPIED" if occupied[i] else "CLEAR",
            "known_train_schedule": bool(scheduled[i]),
            "distance_from_station_km": round(float(station_km[i]), 2),
            "sensor_type": str(sensors[i]),
        }
        sc["rule_label"] = rule_engine_action(sc)
        scenarios.append(sc)
    return scenarios


def apply_label_noise(scenarios: list[dict],
                      fraction: float = LABEL_NOISE_FRACTION,
                      seed: int = LABEL_NOISE_SEED) -> list[dict]:
    """Flip exactly round(fraction * n) labels to a random OTHER action.
    4% noise = honest ground truth: the model must earn its F1 on
    imperfect data, which is what makes the 7+/10 eval target mean
    something. Exact and deterministic (own rng stream)."""
    rng = np.random.default_rng(seed)
    n = len(scenarios)
    n_noisy = int(round(n * fraction))
    noisy_idx = rng.choice(n, size=n_noisy, replace=False)
    for i in noisy_idx:
        original = scenarios[i]["rule_label"]
        others = [a for a in ACTIONS if a != original]
        scenarios[i]["label"] = str(others[int(rng.integers(0, len(others)))])
        scenarios[i]["label_noised"] = True
    for sc in scenarios:
        sc.setdefault("label", sc["rule_label"])
        sc.setdefault("label_noised", False)
    return scenarios


def build_dataset(n: int = N_SCENARIOS, seed: int = SEED) -> list[dict]:
    """The full pipeline: generate -> label -> 4% noise -> physics.
    Training reads THIS (in-memory), never the CSV -- CSV round-trips
    turn booleans into strings and dates into regrets. The CSV is a
    human/judge artifact only."""
    scenarios = generate_scenarios(n, seed)
    apply_label_noise(scenarios)
    for sc in scenarios:
        sc.update(physics_block(sc))
    return scenarios


RAW_FIELD_ORDER: tuple[str, ...] = (
    "train_speed_kmh", "distance_to_obstacle_km", "environmental_condition",
    "weather_alert", "signal_quality_percent", "severity_score",
    "obstruction_type", "alternative_route_available",
    "communication_latency_ms", "axle_balance", "ahead_section_status",
    "known_train_schedule", "distance_from_station_km", "sensor_type",
)
COMPUTED_ORDER: tuple[str, ...] = (
    "time_to_obstacle_min", "braking_distance_required_km",
    "effective_distance_km", "safe_stopping_possible",
)
LABEL_ORDER: tuple[str, ...] = ("rule_label", "label", "label_noised")


def to_dataframe(scenarios: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        [{k: sc.get(k) for k in RAW_FIELD_ORDER + COMPUTED_ORDER + LABEL_ORDER}
         for sc in scenarios]
    )

# =====================================================================
# 6. THE DEMO ANCHOR (section 5's example scenario)
# =====================================================================
# Spec gave: 120 km/h, 8.5 km, heavy_rain, severity 9, landslide_debris,
# no alternate, 1200 ms, 45% signal quality, track_circuit.
# I filled the unspecified fields (flagged for your review):
# weather_alert=True (heavy rain implies it), axle_balance=None
# (track circuits don't report axle balance), ahead CLEAR, schedule
# known, 6 km from station. Expected: eff 8.46 > braking 4.608 + 0.3
# -> can stop, severity 9 -> rung 2 -> emergency_stop.
DEMO_ANCHOR: dict = {
    "train_speed_kmh": 120.0,
    "distance_to_obstacle_km": 8.5,
    "environmental_condition": "heavy_rain",
    "weather_alert": True,
    "signal_quality_percent": 45.0,
    "severity_score": 9,
    "obstruction_type": "landslide_debris",
    "alternative_route_available": False,
    "communication_latency_ms": 1200,
    "axle_balance": None,
    "ahead_section_status": "CLEAR",
    "known_train_schedule": True,
    "distance_from_station_km": 6.0,
    "sensor_type": "track_circuit",
}

# =====================================================================
# 7. CLI
# =====================================================================

def _print_report(df: pd.DataFrame, n: int) -> bool:
    print(f"\n=== RailGuard sensor scenarios: {n} rows ===")
    print(f"types covered: {df['obstruction_type'].nunique()}/13")
    print(f"weathers covered: {df['environmental_condition'].nunique()}/6")
    n_noisy = int(df["label_noised"].sum())
    print(f"label noise: {n_noisy}/{n} rows "
          f"({100.0 * n_noisy / n:.2f}% -- expected {LABEL_NOISE_FRACTION:.0%})")

    print("\nClass balance (label):")
    ok = True
    counts = df["label"].value_counts()
    for a in ACTIONS:
        c = int(counts.get(a, 0))
        pct = 100.0 * c / n
        bar = "#" * int(pct / 2)
        print(f"  {a:<22} {c:>5}  {pct:5.1f}%  {bar}")
        if pct < 10.0:
            ok = False
            print(f"       !! below 10% -- macro-F1 will starve, revisit TYPE_WEIGHTS")
    print(f"\ncan't-stop fraction (rule rung 1): "
          f"{(~df['safe_stopping_possible']).mean():.1%}")

    print("\nDemo anchor check (DEMO_ANCHOR):")
    print(f"  physics : {physics_block(DEMO_ANCHOR)}")
    print(f"  rule    : {rule_engine_action(DEMO_ANCHOR)} "
          f"(expected emergency_stop)")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate seeded sensor scenarios")
    parser.add_argument("--rows", type=int, default=N_SCENARIOS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out", type=str, default="ml_sensor/data/scenarios.csv")
    args = parser.parse_args()

    scenarios = build_dataset(args.rows, args.seed)
    df = to_dataframe(scenarios)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"wrote {out} ({len(df)} rows, {len(df.columns)} columns)")

    # Leak guard runs at build time too, not only in tests.
    assert_leakage_free(encode_features(scenarios[0]).keys())

    _print_report(df, len(df))
    print("\nDone. CSV is a display artifact; training reads build_dataset() directly.")


if __name__ == "__main__":
    main()
