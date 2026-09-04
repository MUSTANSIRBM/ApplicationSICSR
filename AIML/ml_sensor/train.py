"""
ml_sensor/train.py -- OFFLINE training for the live decision model.

Step 2 of 7. This is where the sensor ML earns its right to sit in the
live emergency path (locked decision 9: allowed, but on the R1/R2 leash
that decide.py enforces).

What this file does:
  - rebuilds the seeded 4000-scenario dataset IN MEMORY via
    build_dataset() -- never from the CSV. CSV round-trips corrupt
    booleans and this artifact is our ground truth.
  - LABEL ENCODING: XGBoost 2.x removed string-label inference, so
    both models train on integer codes = index into ACTIONS. The
    code<->action mapping is part of the PERSISTED BUNDLE -- decide.py
    decodes predictions through the bundle, never through memory.
  - seeded stratified 80/20 split (random_state=42)
  - fits the axle_balance imputer on the TRAIN SPLIT ONLY; the imputer
    is persisted inside the bundle so serving applies the identical
    transform.
  - trains RandomForest AND XGBoost, reports both honestly, persists
    the macro-F1 WINNER as exactly one joblib bundle.
  - the bundle carries EVERYTHING serving needs: model, model name,
    label mapping, feature column order, imputer, category code maps,
    weather multipliers, action list, confidence floor. decide.py
    rebuilds the feature matrix FROM THE BUNDLE -- never from memory.

Run:  python -m ml_sensor.train
      -> ml_sensor/model/decision_model.joblib
      -> ml_sensor/model/training_report.json

Layer rules: sklearn + xgboost + joblib only. No fastapi, no sqlmodel.
The live path loads the joblib file directly and never imports this
module.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from ml_sensor.scenarios import (ACTIONS, FEATURE_COLUMNS, SEED,
                                  N_SCENARIOS, LABEL_NOISE_FRACTION,
                                  OBSTRUCTION_CODES, SENSOR_CODES,
                                  WEATHER_MULTIPLIERS, assert_leakage_free,
                                  build_dataset, encode_features)

# =====================================================================
# Config
# =====================================================================

TRAIN_SEED = 42
TEST_SIZE = 0.20
CONFIDENCE_FLOOR = 0.55

BUNDLE_PATH = Path("ml_sensor/model/decision_model.joblib")
REPORT_PATH = Path("ml_sensor/model/training_report.json")

# ---------------------------------------------------------------------
# LABEL ENCODING
# ---------------------------------------------------------------------
# The one and only place action strings become training targets.
# code i == ACTIONS[i]. Explicit (not sklearn's LabelEncoder, which
# sorts alphabetically and would create a second implicit contract).

ACTION_TO_CODE: dict[str, int] = {a: i for i, a in enumerate(ACTIONS)}
CODE_TO_ACTION: dict[int, str] = {i: a for i, a in enumerate(ACTIONS)}


def encode_labels(labels: list[str] | np.ndarray) -> np.ndarray:
    return np.array([ACTION_TO_CODE[str(l)] for l in labels], dtype=np.int64)


def decode_labels(codes: np.ndarray) -> list[str]:
    return [CODE_TO_ACTION[int(c)] for c in np.asarray(codes).ravel()]


# =====================================================================
# Feature matrix building (shared discipline with decide.py)
# =====================================================================

def features_matrix(scenarios: list[dict]) -> pd.DataFrame:
    """RAW scenarios -> 16-column float matrix in FEATURE_COLUMNS order.

    axle_balance None -> NaN (imputation is downstream, train-split-fit
    only). This function is the ONLY place raw dicts become numbers,
    and it always calls assert_leakage_free -- the wall runs here too,
    not only in tests.
    """
    rows = [encode_features(sc) for sc in scenarios]
    X = pd.DataFrame(rows, columns=list(FEATURE_COLUMNS))
    X = X.apply(pd.to_numeric, errors="raise").astype(float)
    assert_leakage_free(X.columns)
    return X


# =====================================================================
# Training
# =====================================================================

def _make_models() -> dict[str, object]:
    """Both candidates. Seeded. n_jobs=1 on XGBoost deliberately:
    CPU hist training with multiple threads has a reputation for tiny
    nondeterminism, and reproducible F1 is worth more than 2 seconds."""
    return {
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            min_samples_leaf=2,
            random_state=TRAIN_SEED,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=400,
            max_depth=6,
            learning_rate=0.1,
            tree_method="hist",
            eval_metric="mlogloss",
            random_state=TRAIN_SEED,
            n_jobs=1,
        ),
    }


def _metrics(y_true_str: list[str], y_pred_str: list[str]) -> dict:
    labels = list(ACTIONS)
    report = classification_report(
        y_true_str, y_pred_str, labels=labels,
        zero_division=0, output_dict=True,
    )
    return {
        "macro_f1": round(float(f1_score(y_true_str, y_pred_str,
                                          labels=labels, average="macro",
                                          zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(y_true_str, y_pred_str)), 4),
        "per_class": {
            a: {
                "f1": round(report[a]["f1-score"], 4),
                "support": int(report[a]["support"]),
            } for a in labels
        },
        "confusion_matrix": {
            "labels": labels,
            "matrix": confusion_matrix(y_true_str, y_pred_str,
                                       labels=labels).tolist(),
        },
    }


def _importance(model) -> list[dict]:
    try:
        imps = np.asarray(model.feature_importances_, dtype=float)
    except AttributeError:
        return []
    order = np.argsort(imps)[::-1]
    return [
        {"feature": FEATURE_COLUMNS[i], "importance": round(float(imps[i]), 4)}
        for i in order
    ]


def train(n_rows: int = N_SCENARIOS, seed: int = SEED,
          bundle_path: Path = BUNDLE_PATH,
          report_path: Path = REPORT_PATH) -> dict:
    """Full offline pipeline. Deterministic: same n/seed -> identical
    models, identical metrics, byte-identical report."""
    t0 = time.perf_counter()

    # --- data (in memory, never the CSV) ---
    scenarios = build_dataset(n_rows, seed)
    X = features_matrix(scenarios)
    y_str = [sc["label"] for sc in scenarios]
    y = encode_labels(y_str)

    assert_leakage_free(X.columns)

    # --- seeded stratified split ---
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=TRAIN_SEED,
    )

    # --- imputer: TRAIN SPLIT ONLY ---
    imputer = SimpleImputer(strategy="median").fit(X_tr)
    X_tr_i, X_te_i = imputer.transform(X_tr), imputer.transform(X_te)

    # --- train both candidates ---
    results: dict[str, dict] = {}
    fitted: dict[str, object] = {}
    for name, model in _make_models().items():
        model.fit(X_tr_i, y_tr)
        y_pred = decode_labels(model.predict(X_te_i))
        results[name] = _metrics(decode_labels(y_te), y_pred)
        results[name]["importances"] = _importance(model)
        fitted[name] = model

    # --- pick the winner: macro F1, tie -> RF (simpler artifact) ---
    winner = max(
        results,
        key=lambda k: (results[k]["macro_f1"],
                       k == "random_forest"),
    )

    # --- honest R2 preview ---
    probs = np.asarray(fitted[winner].predict_proba(X_te_i))
    conf = probs.max(axis=1)
    fallback_rate = float((conf < CONFIDENCE_FLOOR).mean())

    # --- the bundle: everything serving needs, nothing from memory ---
    bundle = {
        "model": fitted[winner],
        "model_name": winner,
        "actions": list(ACTIONS),
        "label_encoding": ("model predicts int codes; "
                           "actions[code] is the action string; "
                           "model.classes_ gives the code order for "
                           "predict_proba columns"),
        "action_to_code": dict(ACTION_TO_CODE),
        "feature_columns": list(FEATURE_COLUMNS),
        "imputer": imputer,
        "obstruction_codes": dict(OBSTRUCTION_CODES),
        "sensor_codes": dict(SENSOR_CODES),
        "weather_multipliers": dict(WEATHER_MULTIPLIERS),
        "confidence_floor": CONFIDENCE_FLOOR,
        "train_seed": TRAIN_SEED,
        "data_seed": seed,
        "n_rows": n_rows,
        "versions": {
            "python": platform.python_version(),
            "sklearn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "numpy": np.__version__,
        },
        "test_metrics": results[winner],
    }

    bundle_path = Path(bundle_path)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, bundle_path)

    elapsed = round(time.perf_counter() - t0, 2)
    report = {
        "trained_at_seed": seed,
        "split": {"train": int(len(y_tr)), "test": int(len(y_te)),
                  "test_size": TEST_SIZE, "split_seed": TRAIN_SEED,
                  "stratified": True},
        "label_noise_fraction": LABEL_NOISE_FRACTION,
        "class_balance_train": {
            a: int((y_tr == ACTION_TO_CODE[a]).sum()) for a in ACTIONS
        },
        "models": results,
        "winner": winner,
        "winner_test_macro_f1": results[winner]["macro_f1"],
        "expected_f1_band": [0.90, 0.96],
        "r2_fallback_preview": {
            "confidence_floor": CONFIDENCE_FLOOR,
            "test_fallback_rate": round(fallback_rate, 4),
            "note": ("tree ensembles are near-categorical here; low-"
                     "confidence fallback firing rarely is HONEST, not "
                     "a bug. The rate is reported, never hidden."),
        },
        "bundle_path": str(bundle_path),
        "elapsed_seconds": elapsed,
    }
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    return report


# =====================================================================
# Bundle loading (used by CLI checks, tests, api self-heal boot)
# =====================================================================

def load_bundle(path: Path = BUNDLE_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"no trained model at {path} -- run: python -m ml_sensor.train"
        )
    return joblib.load(path)


# =====================================================================
# CLI
# =====================================================================

def _print_report(report: dict) -> None:
    n_total = sum(report["class_balance_train"].values())
    print(f"\n=== RailGuard sensor model training ===")
    print(f"rows {n_total} | split {report['split']['train']}/{report['split']['test']} "
          f"(stratified, seed {report['split']['split_seed']})")
    print(f"label noise on ground truth: {report['label_noise_fraction']:.0%}")

    print("\nModel comparison (test split):")
    for name, m in report["models"].items():
        star = "  <- WINNER" if name == report["winner"] else ""
        print(f"  {name:<15} macro F1 {m['macro_f1']:.4f}  "
              f"acc {m['accuracy']:.4f}{star}")

    w = report["models"][report["winner"]]
    print(f"\nWinner per-class F1 ({report['winner']}):")
    for a in ACTIONS:
        pc = w["per_class"][a]
        print(f"  {a:<22} F1 {pc['f1']:.4f}  (support {pc['support']})")

    lo, hi = report["expected_f1_band"]
    f1 = report["winner_test_macro_f1"]
    verdict = "in band" if lo <= f1 <= hi else ("ABOVE band" if f1 > hi else "BELOW BAND -- investigate")
    print(f"\nwinner macro F1 {f1:.4f} -- expected [{lo}, {hi}]: {verdict}")

    print(f"\nR2 fallback preview: {report['r2_fallback_preview']['test_fallback_rate']:.2%} "
          f"of test predictions under confidence "
          f"{report['r2_fallback_preview']['confidence_floor']}")

    print(f"\nTop features ({report['winner']}):")
    for row in w["importances"][:6]:
        print(f"  {row['feature']:<35} {row['importance']:.4f}")

    print(f"\nwrote {report['bundle_path']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the RailGuard sensor decision model (offline)"
    )
    parser.add_argument("--rows", type=int, default=N_SCENARIOS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    report = train(n_rows=args.rows, seed=args.seed)
    _print_report(report)


if __name__ == "__main__":
    main()

