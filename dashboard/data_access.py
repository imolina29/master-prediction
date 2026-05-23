import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

FEATURES_PATH = _PROJECT_ROOT / "data" / "features" / "team_features.parquet"

_supabase: Client | None = None


def _get_secret(key: str, default: str = "") -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def get_supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            _get_secret("SUPABASE_URL"),
            _get_secret("SUPABASE_SERVICE_KEY") or _get_secret("SUPABASE_KEY"),
        )
    return _supabase


@st.cache_data(ttl=3600)
def load_features(path: str | None = None) -> pd.DataFrame:
    p = Path(path) if path else FEATURES_PATH
    if not p.exists():
        return pd.DataFrame()
    return duckdb.sql(f"SELECT * FROM '{p}'").df()


@st.cache_data(ttl=3600)
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


@st.cache_data(ttl=3600)
def load_xg(division: str | None = None) -> pd.DataFrame:
    features = load_features()
    if features.empty:
        return pd.DataFrame()

    home = features[features["venue"] == "home"].copy()
    has_xg = home["xg_for"].notna()
    xg = home[has_xg]

    if xg.empty:
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "division": xg["division"],
            "match_date": xg["match_date"].astype(str),
            "home_team": xg["team"],
            "away_team": xg["opponent"],
            "home_xg": xg["xg_for"],
            "away_xg": xg["xg_against"],
        }
    )

    if division:
        df = df[df["division"] == division]
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
    teams = sorted(set(df["home_team"].unique()) | set(df["away_team"].unique()))
    return teams


@st.cache_data(ttl=300)
def get_active_picks() -> list[dict]:
    client = get_supabase_client()
    resp = client.table("value_bets").select("*").is_("result", "null").execute()
    return resp.data or []


@st.cache_data(ttl=300)
def get_resolved_picks() -> list[dict]:
    client = get_supabase_client()
    resp = (
        client.table("value_bets")
        .select("*")
        .not_.is_("result", "null")
        .order("match_date", desc=True)
        .execute()
    )
    return resp.data or []


DIVISION_NAMES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "EC": "Champions League",
    "WC": "FIFA World Cup",
}
