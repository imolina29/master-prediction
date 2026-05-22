import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from xgboost import XGBClassifier

from backend.ml.config import BASE_PARAMS, SEASON_BOUNDARIES, TARGETS

logger = logging.getLogger(__name__)


def evaluate_fold(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target: str,
    feature_cols: list[str],
) -> dict:
    target_cfg = TARGETS[target]
    params = {**BASE_PARAMS, **target_cfg}

    x_train = train_df[feature_cols].copy()
    y_train = train_df[f"target_{target}"].copy()
    valid_train = y_train.notna() & x_train.notna().all(axis=1)
    x_train = x_train[valid_train]
    y_train = y_train[valid_train].astype(int)

    x_test = test_df[feature_cols].copy()
    y_test = test_df[f"target_{target}"].copy()
    valid_test = y_test.notna() & x_test.notna().all(axis=1)
    x_test = x_test[valid_test]
    y_test = y_test[valid_test].astype(int)

    model = XGBClassifier(**params, early_stopping_rounds=20)
    model.fit(x_train, y_train, eval_set=[(x_test, y_test)], verbose=False)

    y_pred = model.predict(x_test)
    y_proba = model.predict_proba(x_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "log_loss": float(log_loss(y_test, y_proba)),
        "n_test": int(len(y_test)),
        "n_train": int(len(y_train)),
    }

    if target != "1x2":
        metrics["brier_score"] = float(brier_score_loss(y_test, y_proba[:, 1]))

    if target == "1x2" and "odd_home" in test_df.columns:
        odds_df = test_df.loc[valid_test, ["odd_home", "odd_draw", "odd_away"]].reset_index(
            drop=True
        )
        roi = simulate_roi(y_proba, y_test.values, odds_df)
        metrics.update(roi)

    return metrics


def simulate_roi(
    probs: np.ndarray,
    actuals: np.ndarray,
    odds: pd.DataFrame,
    threshold: float = 0.05,
) -> dict:
    total_bets = 0
    total_profit = 0.0

    odd_cols = ["odd_home", "odd_draw", "odd_away"]
    for i in range(len(actuals)):
        for cls_idx, odd_col in enumerate(odd_cols):
            odd_val = odds.iloc[i][odd_col]
            if pd.isna(odd_val) or odd_val <= 1.0:
                continue
            implied_prob = 1.0 / odd_val
            model_prob = probs[i][cls_idx]
            edge = model_prob - implied_prob
            if edge > threshold:
                total_bets += 1
                if actuals[i] == cls_idx:
                    total_profit += odd_val - 1.0
                else:
                    total_profit -= 1.0

    roi_pct = (total_profit / total_bets * 100) if total_bets > 0 else 0.0
    return {"roi_pct": round(roi_pct, 2), "n_bets": total_bets}


def walk_forward_backtest(
    df: pd.DataFrame,
    target: str,
    variant: str,
    feature_cols: list[str],
    output_path: Path | None = None,
) -> dict:
    df = df.copy()
    df["match_date"] = pd.to_datetime(df["match_date"])

    folds_results = []
    for i, boundary in enumerate(SEASON_BOUNDARIES, 1):
        train = df[df["match_date"] < boundary["train_end"]]
        test = df[
            (df["match_date"] >= boundary["test_start"]) & (df["match_date"] < boundary["test_end"])
        ]
        if len(train) < 50 or len(test) < 10:
            logger.warning("Fold %d skipped: train=%d, test=%d", i, len(train), len(test))
            continue

        fold_metrics = evaluate_fold(train, test, target, feature_cols)
        fold_metrics["fold"] = i
        fold_metrics["train_end"] = boundary["train_end"]
        fold_metrics["test_season"] = boundary["label"]
        folds_results.append(fold_metrics)
        logger.info("Fold %d (%s): accuracy=%.3f", i, boundary["label"], fold_metrics["accuracy"])

    result = {"folds": folds_results}
    if folds_results:
        result["mean_accuracy"] = round(float(np.mean([f["accuracy"] for f in folds_results])), 4)
        result["mean_log_loss"] = round(float(np.mean([f["log_loss"] for f in folds_results])), 4)
        if all("roi_pct" in f for f in folds_results):
            result["mean_roi_pct"] = round(float(np.mean([f["roi_pct"] for f in folds_results])), 2)

    if output_path:
        existing = {}
        if output_path.exists():
            with open(output_path) as f:
                existing = json.load(f)
        existing[f"{variant}_{target}"] = result
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(existing, f, indent=2)

    return result
