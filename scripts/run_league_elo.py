"""Compute ELO ratings for league teams and update upcoming matches in Supabase.

For Champions League (EC division), uses each team's domestic league ELO
adjusted by a league strength bonus, instead of the contaminated EC ELO
(which mixes English Conference data with real CL matches).
"""

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

# Domestic leagues computed first; EC handled specially after
DOMESTIC_DIVISIONS = {"E0", "SP1", "D1", "I1", "F1"}
LEAGUE_DIVISIONS = DOMESTIC_DIVISIONS | {"EC"}

# Additive ELO bonus per league for cross-league (CL) matchups.
# Based on UEFA club coefficient rankings — reflects that a 1700-ELO
# Premier League team is stronger than a 1700-ELO Ligue 1 team.
LEAGUE_STRENGTH_BONUS = {
    "E0": 80,  # Premier League — strongest coefficient
    "SP1": 60,  # La Liga
    "I1": 50,  # Serie A
    "D1": 40,  # Bundesliga
    "F1": 20,  # Ligue 1
}

# Default ELO for teams from leagues we don't track domestically
# (e.g. Eredivisie, Liga Portugal, Süper Lig, etc.)
CL_UNKNOWN_DEFAULT_ELO = 1500.0


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


def _lookup_domestic_elo(
    team: str,
    domestic_elos: dict[str, dict[str, float]],
) -> tuple[float, str | None]:
    """Find a team's ELO from domestic leagues.

    Returns (adjusted_elo, domestic_division) or (default, None).
    """
    for division, elo_table in domestic_elos.items():
        if team in elo_table:
            raw_elo = elo_table[team]
            bonus = LEAGUE_STRENGTH_BONUS.get(division, 0)
            return round(raw_elo + bonus, 1), division
    return CL_UNKNOWN_DEFAULT_ELO, None


def main():
    from backend.db.client import get_supabase
    from backend.ml.elo import compute_league_elo, get_team_elo

    client = get_supabase()

    # --- Phase 1: compute domestic league ELOs ---
    domestic_elos: dict[str, dict[str, float]] = {}

    for division in sorted(DOMESTIC_DIVISIONS):
        logger.info("Computing ELO for %s...", division)

        finished = _fetch_all(client, division)
        if not finished:
            logger.warning("No finished matches for %s", division)
            continue

        elo_ratings = compute_league_elo(finished)
        domestic_elos[division] = elo_ratings

        top_10 = sorted(elo_ratings.items(), key=lambda x: -x[1])[:10]
        logger.info(
            "%s: %d teams rated from %d matches. Top 10:",
            division,
            len(elo_ratings),
            len(finished),
        )
        for team, rating in top_10:
            logger.info("  %s: %.0f", team, rating)

        # Update upcoming domestic matches with their league ELO
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

    # --- Phase 2: EC (Champions League) — use domestic ELO + league strength ---
    logger.info("Computing adjusted ELO for EC (Champions League)...")

    ec_upcoming_resp = (
        client.table("matches")
        .select("id,home_team,away_team")
        .eq("division", "EC")
        .is_("ft_result", "null")
        .execute()
    )
    ec_upcoming = ec_upcoming_resp.data

    if not ec_upcoming:
        logger.info("EC: no upcoming matches to update")
    else:
        found_domestic = 0
        used_default = 0

        for m in ec_upcoming:
            home_elo, home_div = _lookup_domestic_elo(m["home_team"], domestic_elos)
            away_elo, away_div = _lookup_domestic_elo(m["away_team"], domestic_elos)

            if home_div:
                found_domestic += 1
            else:
                used_default += 1
                logger.debug(
                    "  %s: no domestic ELO, using default %.0f",
                    m["home_team"],
                    home_elo,
                )
            if away_div:
                found_domestic += 1
            else:
                used_default += 1
                logger.debug(
                    "  %s: no domestic ELO, using default %.0f",
                    m["away_team"],
                    away_elo,
                )

            client.table("matches").update({"home_elo": home_elo, "away_elo": away_elo}).eq(
                "id", m["id"]
            ).execute()

        logger.info(
            "EC: updated %d matches (%d teams from domestic leagues, %d using default ELO)",
            len(ec_upcoming),
            found_domestic,
            used_default,
        )

        # Log the adjusted ELOs for visibility
        for m in ec_upcoming[:10]:
            h_elo, h_div = _lookup_domestic_elo(m["home_team"], domestic_elos)
            a_elo, a_div = _lookup_domestic_elo(m["away_team"], domestic_elos)
            logger.info(
                "  %s (%s→%.0f) vs %s (%s→%.0f) → diff %.0f",
                m["home_team"],
                h_div or "?",
                h_elo,
                m["away_team"],
                a_div or "?",
                a_elo,
                h_elo - a_elo,
            )

    logger.info("Done!")


if __name__ == "__main__":
    main()
