import logging
import os
import time

import httpx

from backend.services.teams import TeamNormalizer

logger = logging.getLogger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

SPORT_KEY_MAP = {
    "soccer_epl": "E0",
    "soccer_spain_la_liga": "SP1",
    "soccer_germany_bundesliga": "D1",
    "soccer_italy_serie_a": "I1",
    "soccer_france_ligue_one": "F1",
    "soccer_uefa_champs_league": "EC",
    "soccer_fifa_world_cup": "WC",
}


def _get_token() -> str:
    token = os.environ.get("ODDS_API_KEY", "")
    if not token:
        raise RuntimeError("ODDS_API_KEY environment variable not set")
    return token


def fetch_odds(sport_key: str, token: str) -> list[dict]:
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": token,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    events = resp.json()
    logger.info("Fetched %d events for %s", len(events), sport_key)
    return events


def _best_odds_for_market(bookmakers: list[dict], market_key: str) -> tuple[dict, str]:
    best: dict = {}
    best_bookmaker = ""

    pinnacle_found = False
    for bk in bookmakers:
        if bk["key"] == "pinnacle":
            for mkt in bk.get("markets", []):
                if mkt["key"] == market_key:
                    pinnacle_found = True
                    best_bookmaker = "pinnacle"
                    for outcome in mkt["outcomes"]:
                        best[outcome["name"]] = outcome["price"]
                        if "point" in outcome:
                            best[f"{outcome['name']}_point"] = outcome["point"]
                    break
            break

    if not pinnacle_found:
        per_outcome: dict[str, tuple[float, str]] = {}
        for bk in bookmakers:
            for mkt in bk.get("markets", []):
                if mkt["key"] == market_key:
                    for outcome in mkt["outcomes"]:
                        name = outcome["name"]
                        price = outcome["price"]
                        if name not in per_outcome or price > per_outcome[name][0]:
                            per_outcome[name] = (price, bk["key"])
                            if "point" in outcome:
                                best[f"{name}_point"] = outcome["point"]
        if per_outcome:
            best_bookmaker = max(
                set(bk for _, bk in per_outcome.values()),
                key=lambda b: sum(1 for _, bk in per_outcome.values() if bk == b),
            )
            for name, (price, _) in per_outcome.items():
                best[name] = price

    return best, best_bookmaker


def parse_odds(events: list[dict], division: str, normalizer: TeamNormalizer) -> list[dict]:
    records = []
    for event in events:
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        home_raw = event["home_team"]
        away_raw = event["away_team"]
        match_date = event["commence_time"][:10]

        h2h, h2h_bk = _best_odds_for_market(bookmakers, "h2h")
        if not h2h:
            continue

        totals, totals_bk = _best_odds_for_market(bookmakers, "totals")

        records.append({
            "match_date": match_date,
            "home_team": normalizer.normalize(home_raw),
            "away_team": normalizer.normalize(away_raw),
            "division": division,
            "odd_home": h2h.get(home_raw),
            "odd_draw": h2h.get("Draw"),
            "odd_away": h2h.get(away_raw),
            "odd_over25": totals.get("Over") if totals else None,
            "odd_under25": totals.get("Under") if totals else None,
            "bookmaker_h2h": h2h_bk,
            "bookmaker_totals": totals_bk if totals else None,
        })

    return records


def update_match_odds(records: list[dict]) -> int:
    if not records:
        return 0

    from backend.db.client import get_supabase

    client = get_supabase()
    updated = 0

    for r in records:
        update_data = {
            "odd_home": r["odd_home"],
            "odd_draw": r["odd_draw"],
            "odd_away": r["odd_away"],
            "odd_over25": r["odd_over25"],
            "odd_under25": r["odd_under25"],
        }
        resp = (
            client.table("matches")
            .update(update_data)
            .eq("division", r["division"])
            .eq("match_date", r["match_date"])
            .eq("home_team", r["home_team"])
            .eq("away_team", r["away_team"])
            .is_("ft_result", "null")
            .execute()
        )
        if resp.data:
            updated += 1

    logger.info("Updated odds for %d matches", updated)
    return updated


def run_odds_sync() -> dict:
    token = _get_token()
    normalizer = TeamNormalizer()

    from backend.db.client import get_supabase

    client = get_supabase()

    total_updated = 0
    total_events = 0

    for sport_key, division in SPORT_KEY_MAP.items():
        pending = (
            client.table("matches")
            .select("id", count="exact")
            .eq("division", division)
            .is_("ft_result", "null")
            .execute()
        )
        if not pending.count:
            logger.info("No pending fixtures for %s (%s), skipping", division, sport_key)
            continue

        try:
            events = fetch_odds(sport_key, token)
        except httpx.HTTPStatusError as e:
            logger.warning("Failed to fetch odds for %s: %s", sport_key, e)
            time.sleep(1)
            continue

        records = parse_odds(events, division, normalizer)
        updated = update_match_odds(records)
        total_events += len(events)
        total_updated += updated
        logger.info("%s: %d events, %d matches updated", division, len(events), updated)
        time.sleep(1)

    return {"total_events": total_events, "total_updated": total_updated}
