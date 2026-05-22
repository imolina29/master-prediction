from backend.ml.config import (
    BASE_FEATURES,
    BASE_PARAMS,
    MODELS_DIR,
    PREMIUM_FEATURES,
    PREMIUM_LEAGUES,
    SEASON_BOUNDARIES,
    TARGETS,
)


def test_base_features_count():
    assert len(BASE_FEATURES) == 31


def test_premium_features_count():
    assert len(PREMIUM_FEATURES) == 39


def test_premium_includes_base():
    for f in BASE_FEATURES:
        assert f in PREMIUM_FEATURES, f"{f} missing from PREMIUM_FEATURES"


def test_targets():
    assert "1x2" in TARGETS
    assert "over25" in TARGETS
    assert "btts" in TARGETS


def test_season_boundaries_has_5_folds():
    assert len(SEASON_BOUNDARIES) == 5
    for fold in SEASON_BOUNDARIES:
        assert "train_end" in fold
        assert "test_start" in fold
        assert "test_end" in fold
        assert "label" in fold


def test_base_params_has_required_keys():
    assert "max_depth" in BASE_PARAMS
    assert "n_estimators" in BASE_PARAMS
    assert "learning_rate" in BASE_PARAMS
    assert "random_state" in BASE_PARAMS
    assert BASE_PARAMS["random_state"] == 42


def test_premium_leagues():
    assert set(PREMIUM_LEAGUES) == {"E0", "SP1", "D1", "I1", "F1"}


def test_models_dir_is_path():
    assert MODELS_DIR.name == "models"
