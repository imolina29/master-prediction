import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

FEATURES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "features"


def _expand_to_team_rows(df: pd.DataFrame) -> pd.DataFrame:
    home = df.rename(
        columns={
            "home_team": "team",
            "away_team": "opponent",
            "ft_home_goals": "goals_scored",
            "ft_away_goals": "goals_conceded",
            "home_shots_target": "shots_target",
            "away_shots_target": "opp_shots_target",
            "home_corners": "corners",
            "away_corners": "opp_corners",
            "home_xg": "xg_for",
            "away_xg": "xg_against",
        }
    ).assign(venue="home")

    away = df.rename(
        columns={
            "away_team": "team",
            "home_team": "opponent",
            "ft_away_goals": "goals_scored",
            "ft_home_goals": "goals_conceded",
            "away_shots_target": "shots_target",
            "home_shots_target": "opp_shots_target",
            "away_corners": "corners",
            "home_corners": "opp_corners",
            "away_xg": "xg_for",
            "home_xg": "xg_against",
        }
    ).assign(venue="away")

    cols = [
        "division",
        "match_date",
        "team",
        "opponent",
        "venue",
        "goals_scored",
        "goals_conceded",
        "shots_target",
        "corners",
        "xg_for",
        "xg_against",
        "ft_result",
    ]
    home_out = home[[c for c in cols if c in home.columns]]
    away_out = away[[c for c in cols if c in away.columns]]

    combined = pd.concat([home_out, away_out], ignore_index=True)
    combined["match_date"] = pd.to_datetime(combined["match_date"])
    combined.sort_values(["team", "match_date"], inplace=True)

    combined["win"] = ((combined["venue"] == "home") & (combined["ft_result"] == "H")) | (
        (combined["venue"] == "away") & (combined["ft_result"] == "A")
    )
    combined["draw"] = combined["ft_result"] == "D"
    combined["btts"] = (combined["goals_scored"] > 0) & (combined["goals_conceded"] > 0)
    combined["over25"] = (combined["goals_scored"] + combined["goals_conceded"]) > 2.5

    return combined


def _compute_league_position(expanded: pd.DataFrame) -> pd.Series:
    df = expanded.copy()
    df["match_date"] = pd.to_datetime(df["match_date"])
    df["season"] = df["match_date"].apply(lambda d: d.year if d.month >= 7 else d.year - 1)
    df["points"] = df["win"].astype(int) * 3 + df["draw"].astype(int)

    df["cum_points"] = df.groupby(["division", "season", "team"])["points"].cumsum()
    df["cum_points_prior"] = df.groupby(["division", "season", "team"])["cum_points"].shift(1)
    df["cum_points_prior"] = df["cum_points_prior"].fillna(0)

    def _rank_in_group(group):
        ranked = group["cum_points_prior"].rank(ascending=False, method="min")
        n_teams = group.groupby("team").ngroups
        if n_teams <= 1:
            return pd.Series(0.5, index=group.index)
        return ((ranked - 1) / (n_teams - 1)).round(4)

    result = df.groupby(["division", "season", "match_date"], group_keys=False).apply(
        _rank_in_group
    )
    return result.reindex(expanded.index, fill_value=0.5)


def _compute_h2h_features(expanded: pd.DataFrame) -> pd.DataFrame:
    df = expanded.copy()
    df["match_date"] = pd.to_datetime(df["match_date"])

    h2h_win_rate = []
    h2h_avg_goals = []
    h2h_matches_count = []

    global_avg_goals = (df["goals_scored"] + df["goals_conceded"]).mean() / 2
    if pd.isna(global_avg_goals):
        global_avg_goals = 2.5

    for _, row in df.iterrows():
        team = row["team"]
        opponent = row["opponent"]
        date = row["match_date"]

        prior = df[(df["team"] == team) & (df["opponent"] == opponent) & (df["match_date"] < date)]

        if prior.empty:
            h2h_win_rate.append(0.5)
            h2h_avg_goals.append(round(global_avg_goals, 2))
            h2h_matches_count.append(0)
        else:
            wins = prior["win"].sum()
            total = len(prior)
            h2h_win_rate.append(round(wins / total, 4))
            avg_g = (prior["goals_scored"] + prior["goals_conceded"]).mean()
            h2h_avg_goals.append(round(float(avg_g), 2))
            h2h_matches_count.append(min(total, 10))

    return pd.DataFrame(
        {
            "h2h_win_rate": h2h_win_rate,
            "h2h_avg_goals": h2h_avg_goals,
            "h2h_matches": h2h_matches_count,
        },
        index=expanded.index,
    )


def compute_team_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    expanded = _expand_to_team_rows(df)

    grouped = expanded.groupby("team")
    expanded["goals_scored_avg"] = grouped["goals_scored"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["goals_conceded_avg"] = grouped["goals_conceded"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["xg_for_avg"] = grouped["xg_for"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["xg_against_avg"] = grouped["xg_against"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["shots_target_avg"] = grouped["shots_target"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["corners_avg"] = grouped["corners"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )
    expanded["win_rate"] = grouped["win"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["draw_rate"] = grouped["draw"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["btts_rate"] = grouped["btts"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["over25_rate"] = grouped["over25"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["xg_diff_avg"] = expanded["xg_for_avg"] - expanded["xg_against_avg"]
    expanded["xg_overperformance"] = grouped.apply(
        lambda g: (
            g["goals_scored"].shift(1).rolling(10, min_periods=1).mean()
            - g["xg_for"].shift(1).rolling(10, min_periods=1).mean()
        ),
        include_groups=False,
    ).reset_index(level=0, drop=True)

    for w in (3, 10):
        s = f"_{w}"
        expanded[f"goals_scored_avg{s}"] = grouped["goals_scored"].transform(
            lambda col: col.shift(1).rolling(w, min_periods=1).mean()
        )
        expanded[f"goals_conceded_avg{s}"] = grouped["goals_conceded"].transform(
            lambda col: col.shift(1).rolling(w, min_periods=1).mean()
        )
        expanded[f"win_rate{s}"] = grouped["win"].transform(
            lambda col: col.shift(1).astype(float).rolling(w, min_periods=1).mean()
        )

    expanded["rest_days"] = grouped["match_date"].transform(
        lambda s: s.diff().dt.days.fillna(7).astype(int)
    )

    venue_grouped = expanded.groupby(["team", "venue"])
    expanded["venue_win_rate"] = venue_grouped["win"].transform(
        lambda s: s.shift(1).astype(float).rolling(window, min_periods=1).mean()
    )
    expanded["venue_goals_avg"] = venue_grouped["goals_scored"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )

    expanded["league_pos"] = _compute_league_position(expanded)

    h2h = _compute_h2h_features(expanded)
    expanded["h2h_win_rate"] = h2h["h2h_win_rate"]
    expanded["h2h_avg_goals"] = h2h["h2h_avg_goals"]
    expanded["h2h_matches"] = h2h["h2h_matches"]

    logger.info("Computed features for %d team-match rows", len(expanded))
    return expanded


def compute_h2h_features(df: pd.DataFrame, team_a: str, team_b: str) -> dict:
    mask = ((df["home_team"] == team_a) & (df["away_team"] == team_b)) | (
        (df["home_team"] == team_b) & (df["away_team"] == team_a)
    )
    h2h = df[mask].copy()
    if h2h.empty:
        return {
            "total_matches": 0,
            f"{team_a.lower().replace(' ', '_')}_wins": 0,
            f"{team_b.lower().replace(' ', '_')}_wins": 0,
            "draws": 0,
            "avg_total_goals": 0.0,
        }

    a_wins = len(
        h2h[
            ((h2h["home_team"] == team_a) & (h2h["ft_result"] == "H"))
            | ((h2h["away_team"] == team_a) & (h2h["ft_result"] == "A"))
        ]
    )
    b_wins = len(
        h2h[
            ((h2h["home_team"] == team_b) & (h2h["ft_result"] == "H"))
            | ((h2h["away_team"] == team_b) & (h2h["ft_result"] == "A"))
        ]
    )
    draws = len(h2h[h2h["ft_result"] == "D"])
    total_goals = (h2h["ft_home_goals"] + h2h["ft_away_goals"]).mean()

    return {
        "total_matches": len(h2h),
        f"{team_a.lower().replace(' ', '_')}_wins": a_wins,
        f"{team_b.lower().replace(' ', '_')}_wins": b_wins,
        "draws": draws,
        "avg_total_goals": round(float(total_goals), 2),
    }


def save_features(features_df: pd.DataFrame, path: Path | None = None) -> Path:
    if path is None:
        path = FEATURES_DIR / "team_features.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_parquet(path, index=False)
    logger.info("Saved %d rows to %s", len(features_df), path)
    return path
