import pandas as pd
import pytest

from backend.ml.config import PREMIUM_FEATURES
from backend.ml.features import build_match_features


def _make_team_features():
    """Minimal team features: 2 matches, 4 team-rows."""
    return pd.DataFrame(
        [
            {
                "division": "E0",
                "match_date": "2024-01-01",
                "team": "Arsenal",
                "opponent": "Chelsea",
                "venue": "home",
                "goals_scored": 2,
                "goals_conceded": 1,
                "ft_result": "H",
                "goals_scored_avg": 1.5,
                "goals_conceded_avg": 0.8,
                "shots_target_avg": 5.0,
                "corners_avg": 6.0,
                "win_rate": 0.6,
                "draw_rate": 0.2,
                "btts_rate": 0.7,
                "over25_rate": 0.5,
                "xg_for_avg": 1.8,
                "xg_against_avg": 0.9,
                "xg_diff_avg": 0.9,
                "xg_overperformance": 0.1,
                "goals_scored_avg_3": 1.6,
                "goals_conceded_avg_3": 0.7,
                "win_rate_3": 0.7,
                "goals_scored_avg_10": 1.4,
                "goals_conceded_avg_10": 0.9,
                "win_rate_10": 0.5,
                "xg_for": 1.8,
                "xg_against": 0.9,
                "shots_target": 6,
                "corners": 5,
                "win": True,
                "draw": False,
                "btts": True,
                "over25": True,
                "rest_days": 7,
                "venue_win_rate": 0.6,
                "venue_goals_avg": 1.5,
                "league_pos": 0.2,
                "h2h_win_rate": 0.6,
                "h2h_avg_goals": 2.8,
                "h2h_matches": 5,
            },
            {
                "division": "E0",
                "match_date": "2024-01-01",
                "team": "Chelsea",
                "opponent": "Arsenal",
                "venue": "away",
                "goals_scored": 1,
                "goals_conceded": 2,
                "ft_result": "H",
                "goals_scored_avg": 1.0,
                "goals_conceded_avg": 1.2,
                "shots_target_avg": 3.0,
                "corners_avg": 4.0,
                "win_rate": 0.4,
                "draw_rate": 0.3,
                "btts_rate": 0.6,
                "over25_rate": 0.4,
                "xg_for_avg": 0.9,
                "xg_against_avg": 1.5,
                "xg_diff_avg": -0.6,
                "xg_overperformance": 0.2,
                "goals_scored_avg_3": 1.1,
                "goals_conceded_avg_3": 1.3,
                "win_rate_3": 0.3,
                "goals_scored_avg_10": 1.0,
                "goals_conceded_avg_10": 1.1,
                "win_rate_10": 0.4,
                "xg_for": 0.9,
                "xg_against": 1.8,
                "shots_target": 3,
                "corners": 3,
                "win": False,
                "draw": False,
                "btts": True,
                "over25": True,
                "rest_days": 4,
                "venue_win_rate": 0.3,
                "venue_goals_avg": 0.8,
                "league_pos": 0.4,
                "h2h_win_rate": 0.4,
                "h2h_avg_goals": 2.8,
                "h2h_matches": 5,
            },
            {
                "division": "E0",
                "match_date": "2024-01-15",
                "team": "Chelsea",
                "opponent": "Arsenal",
                "venue": "home",
                "goals_scored": 0,
                "goals_conceded": 0,
                "ft_result": "D",
                "goals_scored_avg": 0.5,
                "goals_conceded_avg": 1.0,
                "shots_target_avg": 3.5,
                "corners_avg": 3.5,
                "win_rate": 0.3,
                "draw_rate": 0.3,
                "btts_rate": 0.5,
                "over25_rate": 0.3,
                "xg_for_avg": 0.7,
                "xg_against_avg": 1.2,
                "xg_diff_avg": -0.5,
                "xg_overperformance": 0.1,
                "goals_scored_avg_3": 0.6,
                "goals_conceded_avg_3": 1.1,
                "win_rate_3": 0.3,
                "goals_scored_avg_10": 0.5,
                "goals_conceded_avg_10": 1.0,
                "win_rate_10": 0.3,
                "xg_for": 0.6,
                "xg_against": 0.8,
                "shots_target": 4,
                "corners": 4,
                "win": False,
                "draw": True,
                "btts": False,
                "over25": False,
                "rest_days": 14,
                "venue_win_rate": 0.4,
                "venue_goals_avg": 1.0,
                "league_pos": 0.35,
                "h2h_win_rate": 0.35,
                "h2h_avg_goals": 2.5,
                "h2h_matches": 4,
            },
            {
                "division": "E0",
                "match_date": "2024-01-15",
                "team": "Arsenal",
                "opponent": "Chelsea",
                "venue": "away",
                "goals_scored": 0,
                "goals_conceded": 0,
                "ft_result": "D",
                "goals_scored_avg": 1.0,
                "goals_conceded_avg": 0.5,
                "shots_target_avg": 5.5,
                "corners_avg": 5.5,
                "win_rate": 0.5,
                "draw_rate": 0.3,
                "btts_rate": 0.6,
                "over25_rate": 0.4,
                "xg_for_avg": 1.3,
                "xg_against_avg": 1.0,
                "xg_diff_avg": 0.3,
                "xg_overperformance": 0.0,
                "goals_scored_avg_3": 1.1,
                "goals_conceded_avg_3": 0.6,
                "win_rate_3": 0.5,
                "goals_scored_avg_10": 1.0,
                "goals_conceded_avg_10": 0.5,
                "win_rate_10": 0.5,
                "xg_for": 0.8,
                "xg_against": 0.6,
                "shots_target": 5,
                "corners": 6,
                "win": False,
                "draw": True,
                "btts": False,
                "over25": False,
                "rest_days": 14,
                "venue_win_rate": 0.5,
                "venue_goals_avg": 1.2,
                "league_pos": 0.15,
                "h2h_win_rate": 0.65,
                "h2h_avg_goals": 2.5,
                "h2h_matches": 4,
            },
        ]
    )


def _make_matches_df():
    """Match data with elo and odds (what comes from Supabase)."""
    return pd.DataFrame(
        [
            {
                "division": "E0",
                "match_date": "2024-01-01",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "ft_home_goals": 2,
                "ft_away_goals": 1,
                "ft_result": "H",
                "home_elo": 1800.0,
                "away_elo": 1750.0,
                "odd_home": 1.8,
                "odd_draw": 3.5,
                "odd_away": 4.0,
                "odd_over25": 1.9,
                "odd_under25": 1.9,
            },
            {
                "division": "E0",
                "match_date": "2024-01-15",
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "ft_home_goals": 0,
                "ft_away_goals": 0,
                "ft_result": "D",
                "home_elo": 1750.0,
                "away_elo": 1800.0,
                "odd_home": 2.5,
                "odd_draw": 3.2,
                "odd_away": 2.8,
                "odd_over25": 2.1,
                "odd_under25": 1.7,
            },
        ]
    )


def test_build_match_features_shape():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    assert len(result) == 2


def test_build_match_features_has_all_premium_columns():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    for col in PREMIUM_FEATURES:
        assert col in result.columns, f"Missing column: {col}"


def test_build_match_features_has_targets():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    assert "target_1x2" in result.columns
    assert "target_over25" in result.columns
    assert "target_btts" in result.columns


def test_target_encoding():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    row_h = result[result["home_team"] == "Arsenal"].iloc[0]
    assert row_h["target_1x2"] == 0  # H=0
    assert row_h["target_over25"] == 1  # 2+1=3 > 2.5
    assert row_h["target_btts"] == 1  # both scored

    row_d = result[result["home_team"] == "Chelsea"].iloc[0]
    assert row_d["target_1x2"] == 1  # D=1
    assert row_d["target_over25"] == 0  # 0+0=0 <= 2.5
    assert row_d["target_btts"] == 0  # neither scored


def test_elo_diff():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    row = result[result["home_team"] == "Arsenal"].iloc[0]
    assert row["elo_diff"] == pytest.approx(50.0)


def test_home_away_prefix():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    row = result[result["home_team"] == "Arsenal"].iloc[0]
    assert row["home_goals_scored_avg"] == pytest.approx(1.5)
    assert row["away_goals_scored_avg"] == pytest.approx(1.0)


def test_odds_columns_present():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    assert "odd_home" in result.columns
    assert "odd_draw" in result.columns
    assert "odd_away" in result.columns
    assert "odd_over25" in result.columns
    assert "odd_under25" in result.columns


def test_build_match_features_has_new_features():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    new_cols = [
        "home_rest_days",
        "away_rest_days",
        "home_league_pos",
        "away_league_pos",
        "league_pos_diff",
        "home_h2h_win_rate",
        "home_h2h_avg_goals",
        "home_h2h_matches",
        "away_h2h_win_rate",
        "away_h2h_avg_goals",
        "away_h2h_matches",
        "home_venue_win_rate",
        "home_venue_goals_avg",
        "away_venue_win_rate",
        "away_venue_goals_avg",
    ]
    for col in new_cols:
        assert col in result.columns, f"Missing column: {col}"


def test_league_pos_diff():
    team_feat = _make_team_features()
    matches = _make_matches_df()
    result = build_match_features(team_feat, matches)
    row = result.iloc[0]
    expected = row["home_league_pos"] - row["away_league_pos"]
    assert row["league_pos_diff"] == pytest.approx(expected)
