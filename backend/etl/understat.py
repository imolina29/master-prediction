import logging
import time
from typing import Any

import httpx

from backend.db.client import get_supabase
from backend.services.teams import TeamNormalizer

logger = logging.getLogger(__name__)

LEAGUE_MAP = {
    "EPL": "E0",
    "La_Liga": "SP1",
    "Bundesliga": "D1",
    "Serie_A": "I1",
    "Ligue_1": "F1",
}

UNDERSTAT_BASE = "https://understat.com"
REQUEST_DELAY = 1.5


def fetch_league_season(league: str, season: int) -> dict[str, Any]:
    url = f"{UNDERSTAT_BASE}/getLeagueData/{league}/{season}"
    response = httpx.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Referer": f"{UNDERSTAT_BASE}/league/{league}/{season}",
            "X-Requested-With": "XMLHttpRequest",
        },
        follow_redirects=True,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def parse_matches(dates: list[dict], division: str) -> list[dict]:
    rows = []
    for match in dates:
        if not match.get("isResult"):
            continue
        dt = match["datetime"][:10]
        rows.append(
            {
                "division": division,
                "match_date": dt,
                "home_team": match["h"]["title"],
                "away_team": match["a"]["title"],
                "home_xg": float(match["xG"]["h"]),
                "away_xg": float(match["xG"]["a"]),
                "home_goals": int(match["goals"]["h"]),
                "away_goals": int(match["goals"]["a"]),
                "source": "understat",
            }
        )
    return rows


def load_xg_records(records: list[dict], normalize: callable, batch_size: int = 500) -> int:
    client = get_supabase()
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        for r in batch:
            r["home_team"] = normalize(r["home_team"])
            r["away_team"] = normalize(r["away_team"])
        client.table("match_xg").upsert(
            batch,
            on_conflict="division,match_date,home_team,away_team",
        ).execute()
        total += len(batch)
        logger.info("Loaded xG batch %d-%d (%d total)", i, i + len(batch), total)
    return total


def scrape_all(
    start_season: int = 2014,
    end_season: int = 2024,
) -> dict:
    normalizer = TeamNormalizer()
    all_records: list[dict] = []

    for league, division in LEAGUE_MAP.items():
        for season in range(start_season, end_season + 1):
            logger.info("Fetching %s %d/%d", league, season, season + 1)
            try:
                data = fetch_league_season(league, season)
                matches = parse_matches(data["dates"], division)
                all_records.extend(matches)
                logger.info("  Got %d matches", len(matches))
            except Exception:
                logger.exception("  Failed %s %d", league, season)
            time.sleep(REQUEST_DELAY)

    loaded = load_xg_records(all_records, normalizer.normalize)
    return {"scraped": len(all_records), "loaded": loaded}
