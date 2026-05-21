import numpy as np
import pandas as pd

from backend.ml.config import BASE_FEATURES, PREMIUM_FEATURES
from backend.ml.predict import classify_confidence, predict_match, select_variant
from backend.ml.train import train_model


def _train_and_save(tmp_path, variant="base", target="1x2"):
    rng = np.random.RandomState(42)
    features = PREMIUM_FEATURES if variant == "premium" else BASE_FEATURES
    data = {col: rng.rand(200) for col in features}
    data[f"target_{target}"] = rng.choice([0, 1, 2] if target == "1x2" else [0, 1], size=200)
    df = pd.DataFrame(data)
    train_model(df, target, variant, features, models_dir=tmp_path)
    return df


def test_predict_match_1x2(tmp_path):
    df = _train_and_save(tmp_path, "base", "1x2")
    row = df[BASE_FEATURES].iloc[[0]]
    result = predict_match(row, "1x2", "base", models_dir=tmp_path)
    assert "prob_home" in result
    assert "prob_draw" in result
    assert "prob_away" in result
    total = result["prob_home"] + result["prob_draw"] + result["prob_away"]
    assert abs(total - 1.0) < 0.01


def test_predict_match_binary(tmp_path):
    rng = np.random.RandomState(42)
    data = {col: rng.rand(200) for col in BASE_FEATURES}
    data["target_over25"] = rng.choice([0, 1], size=200)
    df = pd.DataFrame(data)
    train_model(df, "over25", "base", BASE_FEATURES, models_dir=tmp_path)
    row = df[BASE_FEATURES].iloc[[0]]
    result = predict_match(row, "over25", "base", models_dir=tmp_path)
    assert "prob_over25" in result
    assert 0 <= result["prob_over25"] <= 1


def test_select_variant():
    assert select_variant("E0") == "premium"
    assert select_variant("SP1") == "premium"
    assert select_variant("E1") == "base"
    assert select_variant("EC") == "base"


def test_classify_confidence():
    assert classify_confidence(0.65) == "alta"
    assert classify_confidence(0.50) == "media"
    assert classify_confidence(0.40) == "baja"
    assert classify_confidence(0.60) == "media"
    assert classify_confidence(0.61) == "alta"
