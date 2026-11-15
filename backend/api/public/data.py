"""Data access functions for the public API."""

from webapp.data import get_supabase_client, get_track_record, load_features

_FEATURE_COLS = [
    "goals_scored_avg",
    "goals_conceded_avg",
    "goals_scored_avg_3",
    "goals_conceded_avg_3",
    "goals_scored_avg_10",
    "goals_conceded_avg_10",
    "xg_for_avg",
    "xg_against_avg",
    "xg_diff_avg",
    "xg_overperformance",
    "win_rate",
    "win_rate_3",
    "win_rate_10",
    "draw_rate",
    "btts_rate",
    "over25_rate",
    "shots_target_avg",
    "venue_win_rate",
    "venue_goals_avg",
    "league_pos",
    "h2h_win_rate",
    "h2h_avg_goals",
    "h2h_matches",
    "rest_days",
]


def get_team_features(team: str, division: str, venue: str = "home") -> dict | None:
    features = load_features()
    if features.empty:
        return None
    mask = (
        (features["team"] == team)
        & (features["division"] == division)
        & (features["venue"] == venue)
    )
    subset = features[mask].sort_values("match_date")
    if subset.empty:
        return None
    row = subset.iloc[-1]
    result = {}
    for col in _FEATURE_COLS:
        if col in row.index:
            val = row[col]
            result[col] = float(val) if val is not None and str(val) != "nan" else None
    return result


def get_match_elo(date: str, home_team: str, away_team: str) -> tuple[float, float] | None:
    client = get_supabase_client()
    resp = (
        client.table("matches")
        .select("home_elo,away_elo")
        .eq("match_date", date)
        .eq("home_team", home_team)
        .eq("away_team", away_team)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    m = resp.data[0]
    if m["home_elo"] is None or m["away_elo"] is None:
        return None
    return (float(m["home_elo"]), float(m["away_elo"]))


def get_accuracy_stats() -> dict:
    tr = get_track_record(limit=5000)
    if tr.empty:
        return {
            "total": 0,
            "accuracy": 0.0,
            "by_confidence": {},
            "by_division": {},
        }
    total = len(tr)
    correct = (tr["predicted_result"] == tr["ft_result"]).sum()

    by_confidence = {}
    for conf in ["alta", "media", "baja"]:
        sub = tr[tr["confidence"] == conf]
        if len(sub) > 0:
            hits = (sub["predicted_result"] == sub["ft_result"]).sum()
            by_confidence[conf] = {
                "total": int(len(sub)),
                "correct": int(hits),
                "accuracy": round(float(hits / len(sub)), 4),
            }

    by_division = {}
    for div in tr["division"].unique():
        sub = tr[tr["division"] == div]
        hits = (sub["predicted_result"] == sub["ft_result"]).sum()
        by_division[div] = {
            "total": int(len(sub)),
            "correct": int(hits),
            "accuracy": round(float(hits / len(sub)), 4),
        }

    return {
        "total": int(total),
        "accuracy": round(float(correct / total), 4),
        "by_confidence": by_confidence,
        "by_division": by_division,
    }


def get_h2h(home_team: str, away_team: str, limit: int = 10) -> list[dict]:
    client = get_supabase_client()
    resp1 = (
        client.table("matches")
        .select("match_date,home_team,away_team,ft_home_goals,ft_away_goals,ft_result")
        .eq("home_team", home_team)
        .eq("away_team", away_team)
        .not_.is_("ft_result", "null")
        .order("match_date", desc=True)
        .limit(limit)
        .execute()
    )
    resp2 = (
        client.table("matches")
        .select("match_date,home_team,away_team,ft_home_goals,ft_away_goals,ft_result")
        .eq("home_team", away_team)
        .eq("away_team", home_team)
        .not_.is_("ft_result", "null")
        .order("match_date", desc=True)
        .limit(limit)
        .execute()
    )
    all_matches = (resp1.data or []) + (resp2.data or [])
    all_matches.sort(key=lambda m: m["match_date"], reverse=True)
    return all_matches[:limit]
