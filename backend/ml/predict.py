import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from backend.ml.config import (
    BASE_FEATURES,
    MODELS_DIR,
    PREMIUM_FEATURES,
    PREMIUM_LEAGUES,
)

logger = logging.getLogger(__name__)

_model_cache: dict[str, object] = {}


def _load_model(variant: str, target: str, models_dir: Path | None = None):
    if models_dir is None:
        models_dir = MODELS_DIR
    key = f"{variant}_{target}"
    if key not in _model_cache:
        path = models_dir / f"{key}.joblib"
        _model_cache[key] = joblib.load(path)
    return _model_cache[key]


def select_variant(division: str) -> str:
    return "premium" if division in PREMIUM_LEAGUES else "base"


def classify_confidence(max_prob: float) -> str:
    if max_prob > 0.60:
        return "alta"
    if max_prob > 0.45:
        return "media"
    return "baja"


def predict_match(
    feature_row: pd.DataFrame,
    target: str,
    variant: str,
    models_dir: Path | None = None,
) -> dict:
    model = _load_model(variant, target, models_dir)
    features = PREMIUM_FEATURES if variant == "premium" else BASE_FEATURES
    x = feature_row[features]
    proba = model.predict_proba(x)[0]

    if target == "1x2":
        return {
            "prob_home": round(float(proba[0]), 4),
            "prob_draw": round(float(proba[1]), 4),
            "prob_away": round(float(proba[2]), 4),
        }
    if target == "over25":
        return {"prob_over25": round(float(proba[1]), 4)}
    return {"prob_btts": round(float(proba[1]), 4)}


def predict_upcoming(
    feature_row: pd.DataFrame,
    division: str,
    models_dir: Path | None = None,
) -> dict:
    variant = select_variant(division)
    result = {"model_variant": variant}

    preds_1x2 = predict_match(feature_row, "1x2", variant, models_dir)
    result.update(preds_1x2)

    preds_ou = predict_match(feature_row, "over25", variant, models_dir)
    result.update(preds_ou)

    preds_btts = predict_match(feature_row, "btts", variant, models_dir)
    result.update(preds_btts)

    probs = [preds_1x2["prob_home"], preds_1x2["prob_draw"], preds_1x2["prob_away"]]
    max_prob = max(probs)
    result["predicted_result"] = ["H", "D", "A"][np.argmax(probs)]
    result["confidence"] = classify_confidence(max_prob)

    return result
