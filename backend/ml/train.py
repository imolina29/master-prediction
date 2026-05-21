import logging
from pathlib import Path

import joblib
import pandas as pd
from xgboost import XGBClassifier

from backend.ml.config import (
    BASE_FEATURES,
    BASE_PARAMS,
    MODELS_DIR,
    PREMIUM_FEATURES,
    TARGETS,
)

logger = logging.getLogger(__name__)


def train_model(
    df: pd.DataFrame,
    target: str,
    variant: str,
    feature_cols: list[str],
    models_dir: Path | None = None,
) -> XGBClassifier:
    if models_dir is None:
        models_dir = MODELS_DIR
    models_dir.mkdir(parents=True, exist_ok=True)

    target_cfg = TARGETS[target]
    params = {**BASE_PARAMS, **target_cfg}

    x = df[feature_cols].copy()
    y = df[f"target_{target}"].copy()
    valid = y.notna() & x.notna().all(axis=1)
    x = x[valid]
    y = y[valid].astype(int)

    model = XGBClassifier(**params)
    model.fit(x, y)

    path = models_dir / f"{variant}_{target}.joblib"
    joblib.dump(model, path)
    logger.info("Saved %s (%d samples) → %s", f"{variant}_{target}", len(x), path)
    return model


def train_all(
    base_df: pd.DataFrame,
    premium_df: pd.DataFrame,
    models_dir: Path | None = None,
) -> dict[str, XGBClassifier]:
    models = {}
    for target in TARGETS:
        models[f"base_{target}"] = train_model(base_df, target, "base", BASE_FEATURES, models_dir)
        models[f"premium_{target}"] = train_model(
            premium_df, target, "premium", PREMIUM_FEATURES, models_dir
        )
    return models
