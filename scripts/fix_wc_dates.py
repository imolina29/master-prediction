"""One-shot script to fix WC match dates from UTC to Colombia time (UTC-5).

Queries football-data.org API for the full WC schedule, computes the
Colombia-time date for each match, and updates Supabase rows (matches +
predictions) where the stored date differs.

Usage:
    PYTHONPATH=. python scripts/fix_wc_dates.py

Requires: FOOTBALL_DATA_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_KEY
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COL_TZ = timezone(timedelta(hours=-5))


def main():
    import httpx

    from supabase import create_client

    token = os.environ["FOOTBALL_DATA_TOKEN"]
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    from backend.services.teams import TeamNormalizer

    normalizer = TeamNormalizer()

    headers = {"X-Auth-Token": token}
    resp = httpx.get(
        "https://api.football-data.org/v4/competitions/WC/matches",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    api_matches = resp.json().get("matches", [])
    logger.info("Fetched %d WC matches from API", len(api_matches))

    fixed_matches = 0
    fixed_preds = 0

    for m in api_matches:
        home_raw = m["homeTeam"].get("name")
        away_raw = m["awayTeam"].get("name")
        if not home_raw or not away_raw:
            continue

        home = normalizer.normalize(home_raw)
        away = normalizer.normalize(away_raw)

        utc_str = m["utcDate"]
        utc_date = utc_str[:10]
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        col_date = dt.astimezone(COL_TZ).strftime("%Y-%m-%d")

        if utc_date == col_date:
            continue

        logger.info("%s vs %s: UTC=%s -> COL=%s (shift needed)", home, away, utc_date, col_date)

        for table in ["matches", "predictions"]:
            resp = (
                client.table(table)
                .update({"match_date": col_date})
                .eq("match_date", utc_date)
                .eq("home_team", home)
                .eq("away_team", away)
                .execute()
            )
            count = len(resp.data)
            if table == "matches":
                fixed_matches += count
            else:
                fixed_preds += count
            if count:
                logger.info("  %s: %d rows updated", table, count)

    logger.info("Done. Fixed %d match rows, %d prediction rows.", fixed_matches, fixed_preds)


if __name__ == "__main__":
    main()
