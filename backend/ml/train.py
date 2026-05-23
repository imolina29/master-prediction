import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split
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

TUNING_GRID = [
    {"max_depth": 4, "n_estimators": 200, "learning_rate": 0.03, "min_child_weight": 10},
    {"max_depth": 5, "n_estimators": 300, "learning_rate": 0.05, "min_child_weight": 7},
    {"max_depth": 6, "n_estimators": 300, "learning_rate": 0.05, "min_child_weight": 5},
    {"max_depth": 6, "n_estimators": 400, "learning_rate": 0.03, "min_child_weight": 5},
    {"max_depth": 7, "n_estimators": 200, "learning_rate": 0.08, "min_child_weight": 10},
]


def _tune_hyperparams(x: pd.DataFrame, y: pd.Series, target_cfg: dict, n_folds: int = 3) -> dict:
    best_score = float("inf")
    best_params = {}

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    for candidate in TUNING_GRID:
        params = {
            **BASE_PARAMS,
            **target_cfg,
            **candidate,
        }
        fold_scores = []

        for train_idx, val_idx in skf.split(x, y):
            x_tr, x_val = x.iloc[train_idx], x.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

            model = XGBClassifier(**params, early_stopping_rounds=EARLY_STOPPING_ROUNDS)
            model.fit(x_tr, y_tr, eval_set=[(x_val, y_val)], verbose=False)

            score = model.best_score
            fold_scores.append(score)

        mean_score = float(np.mean(fold_scores))
        if mean_score < best_score:
            best_score = mean_score
            best_params = candidate

    logger.info("Best params (score=%.4f): %s", best_score, best_params)
    return best_params


def train_model(
    df: pd.DataFrame,
    target: str,
    variant: str,
    feature_cols: list[str],
    models_dir: Path | None = None,
    tune: bool = True,
) -> XGBClassifier:
    if models_dir is None:
        models_dir = MODELS_DIR
    models_dir.mkdir(parents=True, exist_ok=True)

    target_cfg = TARGETS[target]

    x = df[feature_cols].copy()
    y = df[f"target_{target}"].copy()
    valid = y.notna() & x.notna().all(axis=1)
    x = x[valid]
    y = y[valid].astype(int)

    if tune and len(x) >= 500:
        logger.info("Tuning %s_%s with %d samples...", variant, target, len(x))
        tuned = _tune_hyperparams(x, y, target_cfg)
        params = {**BASE_PARAMS, **target_cfg, **tuned}
    else:
        params = {**BASE_PARAMS, **target_cfg}

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
