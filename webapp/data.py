"""Data access layer — no Streamlit dependency."""

import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv

from supabase import Client, create_client

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

FEATURES_PATH = _PROJECT_ROOT / "data" / "features" / "team_features.parquet"

DIVISION_NAMES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "EC": "Champions League",
    "WC": "FIFA World Cup",
}

DIVISION_FLAGS = {
    "E0": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "SP1": "🇪🇸",
    "I1": "🇮🇹",
    "D1": "🇩🇪",
    "F1": "🇫🇷",
    "EC": "🏆",
    "WC": "🌍",
}

_supabase: Client | None = None


def get_supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")
        _supabase = create_client(url, key)
    return _supabase


@lru_cache(maxsize=1)
def load_features() -> pd.DataFrame:
    if not FEATURES_PATH.exists():
        return pd.DataFrame()
    return duckdb.sql(f"SELECT * FROM '{FEATURES_PATH}'").df()


def load_matches(division: str | None = None, season: str | None = None) -> pd.DataFrame:
    features = load_features()
    if features.empty:
        return pd.DataFrame()
    home = features[features["venue"] == "home"].copy()
    df = pd.DataFrame(
        {
            "division": home["division"],
            "match_date": pd.to_datetime(home["match_date"]),
            "home_team": home["team"],
            "away_team": home["opponent"],
            "ft_home_goals": home["goals_scored"],
            "ft_away_goals": home["goals_conceded"],
            "ft_result": home["ft_result"],
        }
    )
    if division:
        df = df[df["division"] == division]
    if season:
        start_year = int(season[:4])
        df = df[
            (df["match_date"] >= f"{start_year}-07-01")
            & (df["match_date"] < f"{start_year + 1}-07-01")
        ]
    return df.reset_index(drop=True)


def get_seasons(division: str) -> list[str]:
    df = load_matches(division)
    if df.empty:
        return []
    df["year"] = df["match_date"].dt.year
    df["month"] = df["match_date"].dt.month
    df["season_start"] = df.apply(lambda r: r["year"] if r["month"] >= 7 else r["year"] - 1, axis=1)
    starts = sorted(df["season_start"].unique(), reverse=True)
    return [f"{y}/{y + 1}" for y in starts]


def get_teams(division: str, season: str | None = None) -> list[str]:
    df = load_matches(division, season=season)
    if df.empty:
        return []
    return sorted(set(df["home_team"].unique()) | set(df["away_team"].unique()))


def get_filtered_predictions(
    division: str | None = None,
    confidence: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    client = get_supabase_client()
    query = client.table("predictions").select("*").order("match_date")
    if division:
        query = query.eq("division", division)
    if confidence:
        query = query.eq("confidence", confidence)
    if date_from:
        query = query.gte("match_date", date_from)
    if date_to:
        query = query.lte("match_date", date_to)
    resp = query.limit(200).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


def load_wc_matches() -> list[dict]:
    client = get_supabase_client()
    resp = (
        client.table("matches")
        .select("home_team,away_team,match_date,ft_result,ft_home_goals,ft_away_goals")
        .eq("division", "WC")
        .order("match_date")
        .execute()
    )
    return resp.data or []


def get_upcoming_predictions() -> pd.DataFrame:
    client = get_supabase_client()
    col_tz = timezone(timedelta(hours=-5))
    now_col = datetime.now(col_tz)
    today = now_col.strftime("%Y-%m-%d")
    end = (now_col + timedelta(days=21)).strftime("%Y-%m-%d")
    resp = (
        client.table("predictions")
        .select("*")
        .gte("match_date", today)
        .lte("match_date", end)
        .order("match_date")
        .limit(50)
        .execute()
    )
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


def get_track_record(limit: int = 100) -> pd.DataFrame:
    client = get_supabase_client()
    preds_resp = (
        client.table("predictions").select("*").order("match_date", desc=True).limit(500).execute()
    )
    if not preds_resp.data:
        return pd.DataFrame()

    pred_dates = sorted({p["match_date"] for p in preds_resp.data})

    matches_resp = (
        client.table("matches")
        .select("match_date,home_team,away_team,division,ft_result,ft_home_goals,ft_away_goals")
        .not_.is_("ft_result", "null")
        .gte("match_date", pred_dates[0])
        .order("match_date", desc=True)
        .execute()
    )
    if not matches_resp.data:
        return pd.DataFrame()

    match_map = {}
    for m in matches_resp.data:
        key = (m["match_date"], m["home_team"], m["away_team"])
        match_map[key] = m

    rows = []
    for p in preds_resp.data:
        key = (p["match_date"], p["home_team"], p["away_team"])
        m = match_map.get(key)
        if not m:
            continue
        rows.append(
            {
                **p,
                "ft_result": m["ft_result"],
                "ft_home_goals": m["ft_home_goals"],
                "ft_away_goals": m["ft_away_goals"],
            }
        )

    return pd.DataFrame(rows).head(limit) if rows else pd.DataFrame()
