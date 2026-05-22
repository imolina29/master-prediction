import logging

import pandas as pd

logger = logging.getLogger(__name__)

RESULT_MAP = {"H": 0, "D": 1, "A": 2}

_TEAM_ROLLING_COLS = [
    "goals_scored_avg",
    "goals_conceded_avg",
    "shots_target_avg",
    "corners_avg",
    "win_rate",
    "draw_rate",
    "btts_rate",
    "over25_rate",
    "xg_for_avg",
    "xg_against_avg",
    "xg_diff_avg",
    "xg_overperformance",
    "goals_scored_avg_3",
    "goals_conceded_avg_3",
    "win_rate_3",
    "goals_scored_avg_10",
    "goals_conceded_avg_10",
    "win_rate_10",
]

_MATCH_MERGE_COLS = [
    "home_elo",
    "away_elo",
    "odd_home",
    "odd_draw",
    "odd_away",
    "odd_over25",
    "odd_under25",
    "ft_home_goals",
    "ft_away_goals",
    "ft_result",
]


def build_match_features(team_features: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Join home+away team-level rows into a single match row, then merge Elo and odds.

    Args:
        team_features: DataFrame with two rows per match (one home, one away).
        matches: DataFrame with match-level data from Supabase (Elo, odds, results).

    Returns:
        DataFrame with one row per match containing prefixed home/away rolling
        features, Elo columns, odds columns, elo_diff, and target columns.
    """
    team_features = team_features.copy()
    matches = matches.copy()

    team_features["match_date"] = pd.to_datetime(team_features["match_date"])
    matches["match_date"] = pd.to_datetime(matches["match_date"])

    home = team_features[team_features["venue"] == "home"].copy()
    away = team_features[team_features["venue"] == "away"].copy()

    home_rename = {col: f"home_{col}" for col in _TEAM_ROLLING_COLS}
    away_rename = {col: f"away_{col}" for col in _TEAM_ROLLING_COLS}
    home = home.rename(columns=home_rename)
    away = away.rename(columns=away_rename)

    home_cols = ["division", "match_date", "team", "opponent"] + list(home_rename.values())
    away_cols = ["division", "match_date", "team", "opponent"] + list(away_rename.values())
    home = home[[c for c in home_cols if c in home.columns]]
    away = away[[c for c in away_cols if c in away.columns]]

    # Join: home.team == away.opponent AND home.opponent == away.team
    # (same division + match_date)
    merged = home.merge(
        away,
        left_on=["division", "match_date", "team", "opponent"],
        right_on=["division", "match_date", "opponent", "team"],
        suffixes=("", "_drop"),
    )

    # Drop duplicate key columns introduced by the merge
    drop_cols = [c for c in merged.columns if c.endswith("_drop")]
    merged = merged.drop(columns=drop_cols, errors="ignore")

    merged = merged.rename(columns={"team": "home_team", "opponent": "away_team"})

    # Merge match-level data (Elo, odds, goals, result) from the matches DataFrame
    available_match_cols = ["division", "match_date", "home_team", "away_team"] + [
        c for c in _MATCH_MERGE_COLS if c in matches.columns
    ]
    merged = merged.merge(
        matches[available_match_cols],
        on=["division", "match_date", "home_team", "away_team"],
        how="left",
    )

    merged["elo_diff"] = merged["home_elo"] - merged["away_elo"]

    merged["target_1x2"] = merged["ft_result"].map(RESULT_MAP)
    merged["target_over25"] = ((merged["ft_home_goals"] + merged["ft_away_goals"]) > 2.5).astype(
        int
    )
    merged["target_btts"] = ((merged["ft_home_goals"] > 0) & (merged["ft_away_goals"] > 0)).astype(
        int
    )

    logger.info("Built %d match-level feature rows", len(merged))
    return merged
