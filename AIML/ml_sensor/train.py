# AIML/ml_sensor/train.py
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score
from xgboost import XGBClassifier
import warnings

warnings.filterwarnings('ignore')

# Paths
DATA_PATH = Path(__file__).parent / "training_data.csv"
MODEL_PATH = Path(__file__).parent / "decision_model.joblib"
SEED = 42


def load_data():
    """Load and prepare training data."""
    df = pd.read_csv(DATA_PATH)

    # Separate features and labels
    feature_columns = [
        'train_speed_kmh',
        'distance_to_obstacle_km',
        'environmental_condition',
        'weather_alert',
        'severity_score',
        'obstruction_type',
        'alternative_route_available',
        'communication_latency_ms',
        'signal_quality_percent',
        'sensor_type',
        'axle_balance',
        'ahead_section_status',
        'known_train_schedule',
        'distance_from_station_km',
        'create_repair_defect',
        'corridor'
    ]

    X = df[feature_columns].copy()
    y = df['action'].copy()

    # Encode categorical features
    X = encode_features(X)

    return X, y


def encode_features(X):
    """Encode categorical features for ML training."""
    # environmental_condition
    env_mapping = {"clear": 0, "rain": 1, "heavy_rain": 2, "fog": 3, "snow": 4, "flood": 5}
    X['environmental_condition'] = X['environmental_condition'].map(env_mapping)

    # obstruction_type
    obs_mapping = {
        "landslide_debris": 0, "boulder": 1, "track_buckling": 2,
        "fallen_tree": 3, "stranded_vehicle": 4, "water_logging": 5, "cattle_crossing": 6
    }
    X['obstruction_type'] = X['obstruction_type'].map(obs_mapping)

    # sensor_type
    sensor_mapping = {"track_circuit": 0, "axle_counter": 1, "vibration": 2, "accelerometer": 3}
    X['sensor_type'] = X['sensor_type'].map(sensor_mapping)

    # ahead_section_status
    X['ahead_section_status'] = X['ahead_section_status'].map({"CLEAR": 0, "OCCUPIED": 1})

    # corridor (hash-based encoding)
    corridors = ['DEL-AGRA', 'MUM-PUNE', 'KOL-HOW', 'CHN-BGLR', 'HYB-SEC']
    corridor_mapping = {c: i for i, c in enumerate(corridors)}
    X['corridor'] = X['corridor'].map(corridor_mapping)

    # Boolean columns
    X['weather_alert'] = X['weather_alert'].astype(int)
    X['alternative_route_available'] = X['alternative_route_available'].astype(int)
    X['known_train_schedule'] = X['known_train_schedule'].astype(int)
    X['create_repair_defect'] = X['create_repair_defect'].astype(int)

    return X


def train_models(X_train, X_test, y_train, y_test):
    """Train RandomForest and XGBoost, compare performance."""
    results = {}

    # 1. RandomForest
    print("🌲 Training RandomForest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=SEED,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_f1 = f1_score(y_test, rf_pred, average='macro')
    results['RandomForest'] = {
        'model': rf,
        'f1_score': rf_f1,
        'predictions': rf_pred
    }
    print(f"   ✅ RandomForest F1 (macro): {rf_f1:.4f}")

    # 2. XGBoost
    print("🚀 Training XGBoost...")
    xgb = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=SEED,
        use_label_encoder=False,
        eval_metric='mlogloss'
    )
    xgb.fit(X_train, y_train)
    xgb_pred = xgb.predict(X_test)
    xgb_f1 = f1_score(y_test, xgb_pred, average='macro')
    results['XGBoost'] = {
        'model': xgb,
        'f1_score': xgb_f1,
        'predictions': xgb_pred
    }
    print(f"   ✅ XGBoost F1 (macro): {xgb_f1:.4f}")

    # Determine winner
    if rf_f1 >= xgb_f1:
        winner = 'RandomForest'
    else:
        winner = 'XGBoost'

    print(f"\n🏆 Winner: {winner} (F1: {max(rf_f1, xgb_f1):.4f})")

    return results, winner


def main():
    """Main training pipeline."""
    print("=" * 60)
    print("🧠 ML Sensor Decision Model Training")
    print("=" * 60)

    # 1. Load data
    print("\n📂 Loading training data...")
    X, y = load_data()
    print(f"   Data shape: {X.shape}")
    print(f"   Classes: {y.unique().tolist()}")
    print(f"   Class distribution:\n{y.value_counts()}")

    # 2. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    print(f"\n📊 Train size: {len(X_train)}, Test size: {len(X_test)}")

    # 3. Train models
    results, winner = train_models(X_train, X_test, y_train, y_test)

    # 4. Save winner model
    print(f"\n💾 Saving winning model to {MODEL_PATH}...")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(results[winner]['model'], MODEL_PATH)
    print("✅ Model saved!")

    # 5. Print full evaluation
    print("\n📋 Classification Report (Winner):")
    print(classification_report(
        y_test,
        results[winner]['predictions'],
        target_names=["proceed_with_caution", "reduce_speed", "reroute", "emergency_stop"]
    ))

    print(f"\n✅ Training complete! Model saved to: {MODEL_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()