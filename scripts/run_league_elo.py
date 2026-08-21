"""Compute ELO ratings for league teams and update upcoming matches in Supabase."""

import logging
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

LEAGUE_DIVISIONS = {"E0", "SP1", "D1", "I1", "F1", "EC"}


def _fetch_all(client, division: str) -> list[dict]:
    """Fetch all finished matches for a division, paginating past the 1000-row limit."""
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("matches")
            .select("home_team,away_team,ft_result,match_date")
            .eq("division", division)
            .not_.is_("ft_result", "null")
            .order("match_date")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = resp.data
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return all_rows


def main():
    from backend.db.client import get_supabase
    from backend.ml.elo import compute_league_elo, get_team_elo

    client = get_supabase()

    for division in sorted(LEAGUE_DIVISIONS):
        logger.info("Computing ELO for %s...", division)

        finished = _fetch_all(client, division)
        if not finished:
            logger.warning("No finished matches for %s", division)
            continue

        elo_ratings = compute_league_elo(finished)

        top_10 = sorted(elo_ratings.items(), key=lambda x: -x[1])[:10]
        logger.info(
            "%s: %d teams rated from %d matches. Top 10:",
            division,
            len(elo_ratings),
            len(finished),
        )
        for team, rating in top_10:
            logger.info("  %s: %.0f", team, rating)

        upcoming_resp = (
            client.table("matches")
            .select("id,home_team,away_team")
            .eq("division", division)
            .is_("ft_result", "null")
            .execute()
        )
        upcoming = upcoming_resp.data

        for m in upcoming:
            home_elo = get_team_elo(elo_ratings, m["home_team"])
            away_elo = get_team_elo(elo_ratings, m["away_team"])
            client.table("matches").update({"home_elo": home_elo, "away_elo": away_elo}).eq(
                "id", m["id"]
            ).execute()

        logger.info("%s: updated ELO for %d upcoming matches", division, len(upcoming))

    logger.info("Done!")


if __name__ == "__main__":
    main()
