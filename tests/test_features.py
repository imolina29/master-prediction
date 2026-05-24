import pandas as pd
import pytest

from backend.services.features import compute_h2h_features, compute_team_features


def _make_matches_df():
    """10 matches for 2 teams across 5 matchdays."""
    data = [
        {
            "division": "E0",
            "match_date": "2024-01-01",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "ft_home_goals": 2,
            "ft_away_goals": 1,
            "ft_result": "H",
            "home_shots_target": 6,
            "away_shots_target": 3,
            "home_corners": 5,
            "away_corners": 3,
            "home_xg": 1.8,
            "away_xg": 0.9,
        },
        {
            "division": "E0",
            "match_date": "2024-01-15",
            "home_team": "Chelsea",
            "away_team": "Arsenal",
            "ft_home_goals": 0,
            "ft_away_goals": 0,
            "ft_result": "D",
            "home_shots_target": 4,
            "away_shots_target": 5,
            "home_corners": 4,
            "away_corners": 6,
            "home_xg": 0.6,
            "away_xg": 0.8,
        },
        {
            "division": "E0",
            "match_date": "2024-02-01",
            "home_team": "Arsenal",
            "away_team": "Liverpool",
            "ft_home_goals": 3,
            "ft_away_goals": 1,
            "ft_result": "H",
            "home_shots_target": 8,
            "away_shots_target": 4,
            "home_corners": 7,
            "away_corners": 2,
            "home_xg": 2.5,
            "away_xg": 1.1,
        },
        {
            "division": "E0",
            "match_date": "2024-02-15",
            "home_team": "Liverpool",
            "away_team": "Chelsea",
            "ft_home_goals": 2,
            "ft_away_goals": 2,
            "ft_result": "D",
            "home_shots_target": 5,
            "away_shots_target": 5,
            "home_corners": 4,
            "away_corners": 4,
            "home_xg": 1.5,
            "away_xg": 1.5,
        },
        {
            "division": "E0",
            "match_date": "2024-03-01",
            "home_team": "Chelsea",
            "away_team": "Liverpool",
            "ft_home_goals": 1,
            "ft_away_goals": 0,
            "ft_result": "H",
            "home_shots_target": 3,
            "away_shots_target": 2,
            "home_corners": 3,
            "away_corners": 5,
            "home_xg": 0.9,
            "away_xg": 0.4,
        },
        {
            "division": "E0",
            "match_date": "2024-03-15",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "ft_home_goals": 1,
            "ft_away_goals": 1,
            "ft_result": "D",
            "home_shots_target": 5,
            "away_shots_target": 4,
            "home_corners": 6,
            "away_corners": 3,
            "home_xg": 1.2,
            "away_xg": 1.0,
        },
    ]
    return pd.DataFrame(data)


def test_compute_team_features_shape():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    assert "team" in result.columns
    assert "match_date" in result.columns
    assert "goals_scored_avg" in result.columns
    assert "goals_conceded_avg" in result.columns
    assert "xg_for_avg" in result.columns
    assert "win_rate" in result.columns
    assert "btts_rate" in result.columns
    assert "over25_rate" in result.columns
    # Each match produces 2 rows (one per team)
    assert len(result) == len(df) * 2


def test_no_data_leakage():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    arsenal = result[result["team"] == "Arsenal"].sort_values("match_date")
    first_row = arsenal.iloc[0]
    # First match for Arsenal: no prior data, so features should be NaN
    assert pd.isna(first_row["goals_scored_avg"])


def test_rolling_values_correct():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    arsenal = result[result["team"] == "Arsenal"].sort_values("match_date")

    # Arsenal's 3rd match (2024-02-01): prior matches are Jan-01 (scored 2) and Jan-15 (scored 0)
    third_match = arsenal.iloc[2]
    assert third_match["goals_scored_avg"] == pytest.approx(1.0)  # (2 + 0) / 2


def test_compute_h2h_features():
    df = _make_matches_df()
    h2h = compute_h2h_features(df, "Arsenal", "Chelsea")
    assert h2h["total_matches"] >= 2
    assert "arsenal_wins" in h2h
    assert "chelsea_wins" in h2h
    assert "draws" in h2h
    assert "avg_total_goals" in h2h


def test_rest_days_computed():
    df = _make_matches_df()
    result = compute_team_features(df, window=3)
    assert "rest_days" in result.columns
    arsenal = result[result["team"] == "Arsenal"].sort_values("match_date")
    # First match: default 7
    assert arsenal.iloc[0]["rest_days"] == 7
    # Second match (Jan 15): 14 days after Jan 01
    assert arsenal.iloc[1]["rest_days"] == 14
    # Third match (Feb 01): 17 days after Jan 15
    assert arsenal.iloc[2]["rest_days"] == 17
