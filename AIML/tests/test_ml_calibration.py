"""
ML corner tests: the pipeline runs end-to-end, output is valid, the
integration point works, and safety NEVER appears as a weight.
"""
import json

import pytest


@pytest.fixture(name="trained", scope="module")
def trained_fixture():
    from ml_calibration.gen_history import generate
    from ml_calibration.train import train
    generate(verbose=False)
    return train(verbose=False)


def test_weights_file_shape(trained):
    from ml_calibration.train import WEIGHTS_FILE, WEIGHT_KEYS
    assert WEIGHTS_FILE.exists()
    data = json.loads(WEIGHTS_FILE.read_text())
    assert set(data) == set(WEIGHT_KEYS)
    assert all(isinstance(v, (int, float)) for v in data.values())
    assert "safety" not in json.dumps(data).lower(), \
        "locked decision 1: safety is a tier, never a weight"


def test_multipliers_are_bounded(trained):
    # ML can re-balance, never blow up: 0.5x - 2.0x around defaults.
    from core.scoring import DEFAULT_WEIGHTS
    from ml_calibration.train import WEIGHT_KEYS
    for k in WEIGHT_KEYS:
        ratio = trained[k] / DEFAULT_WEIGHTS[k]
        assert 0.49 <= ratio <= 2.01, f"{k} escaped its clamp: {ratio}"


def test_load_weights_picks_up_calibration(trained):
    from core.scoring import DEFAULT_WEIGHTS, load_weights
    loaded = load_weights()
    assert loaded == trained or loaded == dict(DEFAULT_WEIGHTS)
    # the file exists, so it MUST be the calibrated set:
    assert loaded == trained


def test_scoring_still_pure_with_weights(trained):
    # the live path gained numbers, not an ML dependency.
    import ast
    import inspect
    import core.scoring as scoring
    tree = ast.parse(inspect.getsource(scoring))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"sklearn", "xgboost", "fastapi", "sqlmodel"}


def test_data_check_after_generation():
    from ml_calibration.data_check import check
    stats = check(verbose=False)
    assert stats["weekly_solves"] >= 4
    assert stats["trainable"] is True

