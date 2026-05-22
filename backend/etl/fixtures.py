import csv
import io
import json
import logging
import os
import time
from pathlib import Path

import httpx

from backend.services.teams import TeamNormalizer

logger = logging.getLogger(__name__)

API_BASE = "https://api.football-data.org/v4"

COMPETITION_MAP = {
    "PL": "E0",
    "ELC": "E1",
    "PD": "SP1",
    "BL1": "D1",
    "SA": "I1",
    "FL1": "F1",
    "CL": "EC",
    "WC": "WC",
}

NATIONAL_FEATURES_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "features"
    / "national_team_features.json"
)

INTL_RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)

DATASET_TO_CANONICAL = {
    "Bosnia and Herzegovina": "Bosnia Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "DR Congo": "Congo DR",
    "Curaçao": "Curacao",
    "Czech Republic": "Czechia",
    "Korea Republic": "South Korea",
}

RATE_LIMIT_DELAY = 6.5


def _get_token() -> str:
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "")
    if not token:
        raise RuntimeError("FOOTBALL_DATA_TOKEN environment variable not set")
    return token


def _api_get(path: str, token: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    headers = {"X-Auth-Token": token}
    resp = httpx.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _current_season_year() -> int:
    from datetime import date

    today = date.today()
    return today.year if today.month >= 7 else today.year - 1


def fetch_finished_matches(
    competition_code: str, token: str, season: int | None = None
) -> list[dict]:
    season = season or _current_season_year()
    data = _api_get(
        f"/competitions/{competition_code}/matches",
        token,
        params={"status": "FINISHED", "season": season},
    )
    matches = data.get("matches", [])
    logger.info(
        "Fetched %d finished matches for %s (season %d)", len(matches), competition_code, season
    )
    return matches


def parse_finished_match(raw: dict, division: str, normalizer: TeamNormalizer) -> dict | None:
    home_raw = raw["homeTeam"].get("name")
    away_raw = raw["awayTeam"].get("name")
    if not home_raw or not away_raw:
        return None

    score = raw.get("score", {}).get("fullTime", {})
    home_goals = score.get("home")
    away_goals = score.get("away")
    if home_goals is None or away_goals is None:
        return None

    if home_goals > away_goals:
        result = "H"
    elif away_goals > home_goals:
        result = "A"
    else:
        result = "D"

    return {
        "division": division,
        "match_date": raw["utcDate"][:10],
        "home_team": normalizer.normalize(home_raw),
        "away_team": normalizer.normalize(away_raw),
        "ft_home_goals": home_goals,
        "ft_away_goals": away_goals,
        "ft_result": result,
    }


def fetch_fixtures(competition_code: str, token: str) -> list[dict]:
    data = _api_get(
        f"/competitions/{competition_code}/matches",
        token,
        params={"status": "SCHEDULED"},
    )
    matches = data.get("matches", [])
    logger.info("Fetched %d scheduled fixtures for %s", len(matches), competition_code)
    return matches


def parse_fixture(raw: dict, division: str, normalizer: TeamNormalizer) -> dict | None:
    home_raw = raw["homeTeam"].get("name")
    away_raw = raw["awayTeam"].get("name")
    if not home_raw or not away_raw:
        return None

    return {
        "division": division,
        "match_date": raw["utcDate"][:10],
        "home_team": normalizer.normalize(home_raw),
        "away_team": normalizer.normalize(away_raw),
        "ft_home_goals": None,
        "ft_away_goals": None,
        "ft_result": None,
    }


def load_fixtures(records: list[dict], batch_size: int = 500) -> int:
    if not records:
        return 0

    from backend.db.client import get_supabase

    client = get_supabase()
    total = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table("matches").upsert(
            batch,
            on_conflict="division,match_date,home_team,away_team",
        ).execute()
        total += len(batch)
        logger.info("Loaded fixtures batch %d-%d (%d total)", i, i + len(batch), total)

    return total


def _download_international_results() -> list[dict]:
    logger.info("Downloading international results from %s", INTL_RESULTS_URL)
    resp = httpx.get(INTL_RESULTS_URL, timeout=60)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def _normalize_dataset_name(name: str) -> str:
    return DATASET_TO_CANONICAL.get(name, name)


def build_national_features_from_dataset(
    team_names: set[str], min_date: str = "2022-01-01"
) -> dict[str, dict]:
    rows = _download_international_results()

    canonical_to_dataset: dict[str, str] = {v: k for k, v in DATASET_TO_CANONICAL.items()}

    team_matches: dict[str, list[dict]] = {name: [] for name in team_names}

    for row in rows:
        if row["date"] < min_date:
            continue
        if row["home_score"] == "NA" or row["away_score"] == "NA":
            continue

        home_canonical = _normalize_dataset_name(row["home_team"])
        away_canonical = _normalize_dataset_name(row["away_team"])

        home_goals = int(row["home_score"])
        away_goals = int(row["away_score"])

        if home_canonical in team_matches:
            team_matches[home_canonical].append(
                {"gf": home_goals, "ga": away_goals, "date": row["date"]}
            )
        elif row["home_team"] in canonical_to_dataset.values():
            pass
        else:
            dataset_name = row["home_team"]
            if dataset_name in team_matches:
                team_matches[dataset_name].append(
                    {"gf": home_goals, "ga": away_goals, "date": row["date"]}
                )

        if away_canonical in team_matches:
            team_matches[away_canonical].append(
                {"gf": away_goals, "ga": home_goals, "date": row["date"]}
            )
        elif row["away_team"] in canonical_to_dataset.values():
            pass
        else:
            dataset_name = row["away_team"]
            if dataset_name in team_matches:
                team_matches[dataset_name].append(
                    {"gf": away_goals, "ga": home_goals, "date": row["date"]}
                )

    features: dict[str, dict] = {}
    for name, matches in team_matches.items():
        if len(matches) < 5:
            logger.warning(
                "Only %d matches for %s since %s, skipping", len(matches), name, min_date
            )
            continue

        matches.sort(key=lambda m: m["date"])
        recent = matches[-20:]
        n = len(recent)

        wins = sum(1 for m in recent if m["gf"] > m["ga"])
        draws = sum(1 for m in recent if m["gf"] == m["ga"])
        btts = sum(1 for m in recent if m["gf"] > 0 and m["ga"] > 0)
        over25 = sum(1 for m in recent if m["gf"] + m["ga"] > 2)

        features[name] = {
            "goals_scored_avg": round(sum(m["gf"] for m in recent) / n, 3),
            "goals_conceded_avg": round(sum(m["ga"] for m in recent) / n, 3),
            "shots_target_avg": None,
            "corners_avg": None,
            "win_rate": round(wins / n, 3),
            "draw_rate": round(draws / n, 3),
            "btts_rate": round(btts / n, 3),
            "over25_rate": round(over25 / n, 3),
            "matches_used": n,
        }
        logger.info("Built features for %s: %d matches", name, n)

    return features


def save_national_features(features: dict[str, dict], path: Path | None = None) -> None:
    if path is None:
        path = NATIONAL_FEATURES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(features, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved national team features for %d teams to %s", len(features), path)


def load_national_features(path: Path | None = None) -> dict[str, dict]:
    if path is None:
        path = NATIONAL_FEATURES_PATH
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_fixtures_sync() -> dict:
    token = _get_token()
    normalizer = TeamNormalizer()

    total_fixtures = 0
    wc_team_names: set[str] = set()

    for api_code, division in COMPETITION_MAP.items():
        try:
            raw_fixtures = fetch_fixtures(api_code, token)
        except httpx.HTTPStatusError as e:
            logger.warning("Failed to fetch %s: %s", api_code, e)
            time.sleep(RATE_LIMIT_DELAY)
            continue

        records = [
            r for f in raw_fixtures if (r := parse_fixture(f, division, normalizer)) is not None
        ]

        if api_code == "WC":
            for r in records:
                wc_team_names.add(r["home_team"])
                wc_team_names.add(r["away_team"])

        loaded = load_fixtures(records)
        total_fixtures += loaded
        logger.info("%s → %s: %d fixtures loaded", api_code, division, loaded)
        time.sleep(RATE_LIMIT_DELAY)

    national_features = {}
    if wc_team_names:
        logger.info("Building national team features for %d WC teams", len(wc_team_names))
        national_features = build_national_features_from_dataset(wc_team_names)
        save_national_features(national_features)

    return {
        "total_fixtures": total_fixtures,
        "national_teams_with_features": len(national_features),
    }


def run_current_season_sync() -> dict:
    token = _get_token()
    normalizer = TeamNormalizer()
    season = _current_season_year()

    total_loaded = 0
    for api_code, division in COMPETITION_MAP.items():
        try:
            raw = fetch_finished_matches(api_code, token, season)
        except httpx.HTTPStatusError as e:
            logger.warning("Failed to fetch finished for %s: %s", api_code, e)
            time.sleep(RATE_LIMIT_DELAY)
            continue

        records = [
            r for m in raw if (r := parse_finished_match(m, division, normalizer)) is not None
        ]

        loaded = load_fixtures(records)
        total_loaded += loaded
        logger.info("%s → %s: %d results loaded (season %d)", api_code, division, loaded, season)
        time.sleep(RATE_LIMIT_DELAY)

    return {"season": season, "total_results": total_loaded}
