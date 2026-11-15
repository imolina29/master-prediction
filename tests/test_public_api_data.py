from backend.api.public.data import (
    get_accuracy_stats,
    get_h2h,
    get_match_elo,
    get_team_features,
)


def test_get_team_features_known():
    result = get_team_features("Albacete", "SP1")
    assert result is not None
    assert "goals_scored_avg" in result
    assert "xg_for_avg" in result
    assert isinstance(result["goals_scored_avg"], float)


def test_get_team_features_unknown():
    result = get_team_features("Nonexistent FC", "SP1")
    assert result is None


def test_get_accuracy_stats_shape():
    stats = get_accuracy_stats()
    assert "total" in stats
    assert "accuracy" in stats
    assert "by_confidence" in stats
    assert "by_division" in stats
    assert isinstance(stats["total"], int)
    assert isinstance(stats["accuracy"], float)


def test_get_accuracy_stats_confidence_tiers():
    stats = get_accuracy_stats()
    for tier in ["alta", "media", "baja"]:
        assert tier in stats["by_confidence"]
        tier_data = stats["by_confidence"][tier]
        assert "total" in tier_data
        assert "correct" in tier_data
        assert "accuracy" in tier_data


def test_get_match_elo_returns_tuple_or_none():
    result = get_match_elo("2026-11-20", "Bayern Munich", "Koln")
    if result is not None:
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], float)


def test_get_h2h_returns_list():
    result = get_h2h("Real Madrid", "Celta Vigo")
    assert isinstance(result, list)
