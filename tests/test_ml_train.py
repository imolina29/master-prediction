import numpy as np
import pandas as pd

from backend.ml.config import BASE_FEATURES, PREMIUM_FEATURES
from backend.ml.train import train_model


def _make_training_data(n=200, premium=False):
    rng = np.random.RandomState(42)
    features = PREMIUM_FEATURES if premium else BASE_FEATURES
    data = {col: rng.rand(n) for col in features}
    data["target_1x2"] = rng.choice([0, 1, 2], size=n)
    data["target_over25"] = rng.choice([0, 1], size=n)
    data["target_btts"] = rng.choice([0, 1], size=n)
    return pd.DataFrame(data)


def test_train_model_1x2():
    df = _make_training_data()
    model = train_model(df, target="1x2", variant="base", feature_cols=BASE_FEATURES)
    assert model is not None
    proba = model.predict_proba(df[BASE_FEATURES])
    assert proba.shape == (200, 3)
    assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-5)


def test_train_model_binary():
    df = _make_training_data()
    model = train_model(df, target="over25", variant="base", feature_cols=BASE_FEATURES)
    proba = model.predict_proba(df[BASE_FEATURES])
    assert proba.shape == (200, 2)


def test_train_model_premium():
    df = _make_training_data(n=100, premium=True)
    model = train_model(df, target="btts", variant="premium", feature_cols=PREMIUM_FEATURES)
    proba = model.predict_proba(df[PREMIUM_FEATURES])
    assert proba.shape == (100, 2)


def test_train_model_saves_joblib(tmp_path):
    df = _make_training_data(n=100)
    train_model(
        df, target="1x2", variant="base", feature_cols=BASE_FEATURES, models_dir=tmp_path
    )
    path = tmp_path / "base_1x2.joblib"
    assert path.exists()
    assert path.stat().st_size > 0
