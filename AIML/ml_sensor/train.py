# AIML/ml_sensor/train.py
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
import warnings

warnings.filterwarnings('ignore')

DATA_PATH = Path(__file__).parent / "training_data.csv"
MODEL_PATH = Path(__file__).parent / "decision_model.joblib"
SEED = 42


def load_data():
    """Load and prepare training data."""
    df = pd.read_csv(DATA_PATH)

    # IMPORTANT: REMOVED 'create_repair_defect' and 'corridor' to prevent label leakage
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
        'distance_from_station_km'
    ]

    X = df[feature_columns].copy()
    y = df['action'].copy()

    X = encode_features(X)

    # Encode labels to integers for XGBoost
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # Store label mapping for later use
    label_mapping = dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))
    print(f"📋 Label mapping: {label_mapping}")

    return X, y_encoded, label_encoder


def encode_features(X):
    """Encode categorical features for ML training."""
    # environmental_condition
    env_mapping = {"clear": 0, "rain": 1, "heavy_rain": 2, "fog": 3, "snow": 4, "flood": 5}
    X['environmental_condition'] = X['environmental_condition'].map(env_mapping)

    # obstruction_type - expanded to 13 types mapped 0-12
    obs_mapping = {
        "landslide_debris": 0,
        "boulder": 1,
        "track_buckling": 2,
        "fallen_tree": 3,
        "stranded_vehicle": 4,
        "water_logging": 5,
        "cattle_crossing": 6,
        "broken_rail": 7,
        "signal_cable_theft": 8,
        "sensor_miscount": 9,
        "environmental_false_positive": 10,
        "unknown_obstruction": 11,
        "equipment_failure_ahead": 12
    }
    X['obstruction_type'] = X['obstruction_type'].map(obs_mapping)

    # sensor_type
    sensor_mapping = {"track_circuit": 0, "axle_counter": 1, "vibration": 2, "accelerometer": 3}
    X['sensor_type'] = X['sensor_type'].map(sensor_mapping)

    # ahead_section_status
    X['ahead_section_status'] = X['ahead_section_status'].map({"CLEAR": 0, "OCCUPIED": 1})

    # Boolean columns
    X['weather_alert'] = X['weather_alert'].astype(int)
    X['alternative_route_available'] = X['alternative_route_available'].astype(int)
    X['known_train_schedule'] = X['known_train_schedule'].astype(int)

    return X


def train_models(X_train, X_test, y_train, y_test, label_encoder):
    """Train RandomForest and XGBoost, compare performance."""
    results = {}

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

    print("\n📂 Loading training data...")
    X, y, label_encoder = load_data()
    print(f"   Data shape: {X.shape}")
    print(f"   Classes (encoded): {sorted(set(y))}")
    print(f"   Class distribution:\n{pd.Series(y).value_counts().sort_index()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    print(f"\n📊 Train size: {len(X_train)}, Test size: {len(X_test)}")

    results, winner = train_models(X_train, X_test, y_train, y_test, label_encoder)

    print(f"\n💾 Saving winning model to {MODEL_PATH}...")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save both the model and the label encoder
    joblib.dump({
        'model': results[winner]['model'],
        'label_encoder': label_encoder,
        'feature_names': X.columns.tolist()
    }, MODEL_PATH)
    print("✅ Model saved!")

    # Decode predictions for report
    y_test_decoded = label_encoder.inverse_transform(y_test)
    pred_decoded = label_encoder.inverse_transform(results[winner]['predictions'])

    print("\n📋 Classification Report (Winner):")
    print(classification_report(
        y_test_decoded,
        pred_decoded,
        target_names=label_encoder.classes_
    ))

    print(f"\n✅ Training complete! Model saved to: {MODEL_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()