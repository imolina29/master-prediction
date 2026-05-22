import sys
from pathlib import Path


def _find_project_root() -> Path:
    file_based = Path(__file__).resolve().parent.parent.parent
    if (file_based / "pyproject.toml").exists():
        return file_based
    for p in sys.path:
        candidate = Path(p)
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


PROJECT_ROOT = _find_project_root()
MODELS_DIR = PROJECT_ROOT / "models"
FEATURES_PATH = PROJECT_ROOT / "data" / "features" / "team_features.parquet"
BACKTEST_RESULTS_PATH = PROJECT_ROOT / "data" / "backtest_results.json"

PREMIUM_LEAGUES = ["E0", "SP1", "D1", "I1", "F1"]

TARGETS = {
    "1x2": {"objective": "multi:softprob", "num_class": 3, "eval_metric": "mlogloss"},
    "over25": {"objective": "binary:logistic", "eval_metric": "logloss"},
    "btts": {"objective": "binary:logistic", "eval_metric": "logloss"},
}

BASE_PARAMS = {
    "max_depth": 6,
    "n_estimators": 300,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "random_state": 42,
}

_HOME_BASE = [
    "home_goals_scored_avg",
    "home_goals_conceded_avg",
    "home_shots_target_avg",
    "home_corners_avg",
    "home_win_rate",
    "home_draw_rate",
    "home_btts_rate",
    "home_over25_rate",
]

_HOME_MULTI_WINDOW = [
    "home_goals_scored_avg_3",
    "home_goals_conceded_avg_3",
    "home_win_rate_3",
    "home_goals_scored_avg_10",
    "home_goals_conceded_avg_10",
    "home_win_rate_10",
]

_AWAY_BASE = [c.replace("home_", "away_") for c in _HOME_BASE]
_AWAY_MULTI_WINDOW = [c.replace("home_", "away_") for c in _HOME_MULTI_WINDOW]

_CONTEXT = ["home_elo", "away_elo", "elo_diff"]

BASE_FEATURES = _HOME_BASE + _HOME_MULTI_WINDOW + _AWAY_BASE + _AWAY_MULTI_WINDOW + _CONTEXT

_HOME_XG = [
    "home_xg_for_avg",
    "home_xg_against_avg",
    "home_xg_diff_avg",
    "home_xg_overperformance",
]
_AWAY_XG = [c.replace("home_", "away_") for c in _HOME_XG]

PREMIUM_FEATURES = (
    _HOME_BASE
    + _HOME_MULTI_WINDOW
    + _HOME_XG
    + _AWAY_BASE
    + _AWAY_MULTI_WINDOW
    + _AWAY_XG
    + _CONTEXT
)

SEASON_BOUNDARIES = [
    {
        "train_end": "2019-07-01",
        "test_start": "2019-07-01",
        "test_end": "2020-07-01",
        "label": "2019/20",
    },
    {
        "train_end": "2020-07-01",
        "test_start": "2020-07-01",
        "test_end": "2021-07-01",
        "label": "2020/21",
    },
    {
        "train_end": "2021-07-01",
        "test_start": "2021-07-01",
        "test_end": "2022-07-01",
        "label": "2021/22",
    },
    {
        "train_end": "2022-07-01",
        "test_start": "2022-07-01",
        "test_end": "2023-07-01",
        "label": "2022/23",
    },
    {
        "train_end": "2023-07-01",
        "test_start": "2023-07-01",
        "test_end": "2024-07-01",
        "label": "2023/24",
    },
]
