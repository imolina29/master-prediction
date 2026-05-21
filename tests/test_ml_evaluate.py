import json

import numpy as np
import pandas as pd

from backend.ml.config import BASE_FEATURES
from backend.ml.evaluate import evaluate_fold, simulate_roi, walk_forward_backtest


def _make_multiyear_data(n_per_year=100):
    rng = np.random.RandomState(42)
    rows = []
    for year in range(2017, 2025):
        for i in range(n_per_year):
            month = rng.randint(8, 13) if i < n_per_year // 2 else rng.randint(1, 7)
            day = rng.randint(1, 28)
            row = {col: rng.rand() for col in BASE_FEATURES}
            row["match_date"] = pd.Timestamp(year, month, day)
            row["target_1x2"] = rng.choice([0, 1, 2])
            row["target_over25"] = rng.choice([0, 1])
            row["target_btts"] = rng.choice([0, 1])
            row["odd_home"] = round(rng.uniform(1.2, 5.0), 2)
            row["odd_draw"] = round(rng.uniform(2.5, 5.0), 2)
            row["odd_away"] = round(rng.uniform(1.5, 8.0), 2)
            row["division"] = "E0"
            row["home_team"] = f"Team_{i % 10}"
            row["away_team"] = f"Team_{(i + 5) % 10}"
            rows.append(row)
    return pd.DataFrame(rows)


def test_evaluate_fold_returns_metrics():
    df = _make_multiyear_data()
    train = df[df["match_date"] < "2023-07-01"]
    test = df[(df["match_date"] >= "2023-07-01") & (df["match_date"] < "2024-07-01")]
    metrics = evaluate_fold(train, test, "1x2", BASE_FEATURES)
    assert "accuracy" in metrics
    assert "log_loss" in metrics
    assert 0 <= metrics["accuracy"] <= 1
    assert metrics["log_loss"] > 0
    assert metrics["n_test"] == len(test)


def test_evaluate_fold_binary():
    df = _make_multiyear_data()
    train = df[df["match_date"] < "2023-07-01"]
    test = df[(df["match_date"] >= "2023-07-01") & (df["match_date"] < "2024-07-01")]
    metrics = evaluate_fold(train, test, "over25", BASE_FEATURES)
    assert "accuracy" in metrics
    assert "brier_score" in metrics


def test_simulate_roi():
    probs = np.array([[0.60, 0.20, 0.20], [0.30, 0.30, 0.40], [0.20, 0.50, 0.30]])
    actuals = np.array([0, 2, 1])
    odds = pd.DataFrame(
        {"odd_home": [2.0, 3.0, 5.0], "odd_draw": [3.5, 3.2, 2.0], "odd_away": [4.0, 2.5, 3.5]}
    )
    result = simulate_roi(probs, actuals, odds, threshold=0.05)
    assert "roi_pct" in result
    assert "n_bets" in result
    assert isinstance(result["roi_pct"], float)


def test_walk_forward_backtest_returns_all_folds(tmp_path):
    df = _make_multiyear_data()
    results = walk_forward_backtest(
        df, "1x2", "base", BASE_FEATURES, output_path=tmp_path / "bt.json"
    )
    assert "folds" in results
    assert len(results["folds"]) > 0
    assert "mean_accuracy" in results
    assert (tmp_path / "bt.json").exists()
    with open(tmp_path / "bt.json") as f:
        saved = json.load(f)
    assert "base_1x2" in saved
