import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from backend.ml.config import (
    BASE_FEATURES,
    BASE_PARAMS,
    MODELS_DIR,
    PREMIUM_FEATURES,
    TARGETS,
)

logger = logging.getLogger(__name__)

EARLY_STOPPING_ROUNDS = 20
VAL_SIZE = 0.1


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

    x_train, x_val, y_train, y_val = train_test_split(
        x, y, test_size=VAL_SIZE, random_state=42, stratify=y
    )

    model = XGBClassifier(**params, early_stopping_rounds=EARLY_STOPPING_ROUNDS)
    model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)

    importance = sorted(
        zip(feature_cols, model.feature_importances_), key=lambda t: t[1], reverse=True
    )
    top5 = ", ".join(f"{name}={val:.3f}" for name, val in importance[:5])
    logger.info("Top features %s_%s: %s", variant, target, top5)

    path = models_dir / f"{variant}_{target}.joblib"
    joblib.dump(model, path)
    logger.info(
        "Saved %s (train=%d val=%d trees=%d) → %s",
        f"{variant}_{target}",
        len(x_train),
        len(x_val),
        model.best_iteration + 1,
        path,
    )
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
