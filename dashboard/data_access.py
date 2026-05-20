import os
from pathlib import Path

import duckdb
import pandas as pd
from supabase import Client, create_client

FEATURES_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "features" / "team_features.parquet"
)

_supabase: Client | None = None


def get_supabase_client() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_KEY", "")),
        )
    return _supabase


def load_features(path: Path = FEATURES_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return duckdb.sql(f"SELECT * FROM '{path}'").df()


def _fetch_all(table_name: str, division: str | None = None, page_size: int = 1000) -> list[dict]:
    client = get_supabase_client()
    all_data: list[dict] = []
    offset = 0
    while True:
        query = client.table(table_name).select("*").range(offset, offset + page_size - 1)
        if division:
            query = query.eq("division", division)
        resp = query.execute()
        all_data.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_data


def load_matches(division: str | None = None, season: str | None = None) -> pd.DataFrame:
    data = _fetch_all("matches", division=division)
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["match_date"] = pd.to_datetime(df["match_date"])
    if season:
        start_year = int(season[:4])
        df = df[
            (df["match_date"] >= f"{start_year}-07-01")
            & (df["match_date"] < f"{start_year + 1}-07-01")
        ]
    return df


def load_xg(division: str | None = None) -> pd.DataFrame:
    data = _fetch_all("match_xg", division=division)
    return pd.DataFrame(data)


def get_seasons(division: str) -> list[str]:
    df = load_matches(division)
    if df.empty:
        return []
    df["year"] = df["match_date"].dt.year
    df["month"] = df["match_date"].dt.month
    df["season_start"] = df.apply(lambda r: r["year"] if r["month"] >= 7 else r["year"] - 1, axis=1)
    starts = sorted(df["season_start"].unique(), reverse=True)
    return [f"{y}/{y + 1}" for y in starts]


def get_teams(division: str) -> list[str]:
    df = load_matches(division)
    if df.empty:
        return []
    teams = sorted(set(df["home_team"].unique()) | set(df["away_team"].unique()))
    return teams


DIVISION_NAMES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "EC": "Champions League",
}
