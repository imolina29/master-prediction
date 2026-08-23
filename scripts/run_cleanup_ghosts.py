"""Clean ghost fixtures and predictions from the database.

A ghost is an unplayed match record whose same matchup (division, home, away)
already has a result within ±7 days — typically caused by the football-data.org
API re-reporting played matches as SCHEDULED with a shifted date.
"""

import logging
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _fetch_all_unplayed(client, start: str, end: str) -> list[dict]:
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("matches")
            .select("id,division,match_date,home_team,away_team")
            .gte("match_date", start)
            .lte("match_date", end)
            .is_("ft_result", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_rows


def main():
    from backend.db.client import get_supabase

    client = get_supabase()

    today = date.today()
    start = (today - timedelta(days=7)).isoformat()
    end = (today + timedelta(days=30)).isoformat()

    unplayed = _fetch_all_unplayed(client, start, end)
    logger.info("Found %d unplayed matches in window %s to %s", len(unplayed), start, end)

    played_resp = (
        client.table("matches")
        .select("division,home_team,away_team")
        .gte("match_date", (today - timedelta(days=14)).isoformat())
        .lte("match_date", end)
        .not_.is_("ft_result", "null")
        .execute()
    )
    played_set = {(r["division"], r["home_team"], r["away_team"]) for r in played_resp.data}
    logger.info("Found %d played matches for ghost detection", len(played_set))

    ghost_ids = []
    for m in unplayed:
        key = (m["division"], m["home_team"], m["away_team"])
        if key in played_set:
            ghost_ids.append(m["id"])
            logger.info(
                "Ghost: %s vs %s (%s) on %s",
                m["home_team"],
                m["away_team"],
                m["division"],
                m["match_date"],
            )

    if not ghost_ids:
        logger.info("No ghost matches found.")
        return

    logger.info("Deleting %d ghost matches...", len(ghost_ids))

    for match_id in ghost_ids:
        client.table("matches").delete().eq("id", match_id).execute()

    ghost_preds_deleted = 0
    for m in unplayed:
        key = (m["division"], m["home_team"], m["away_team"])
        if key not in played_set:
            continue
        resp = (
            client.table("predictions")
            .delete()
            .eq("home_team", m["home_team"])
            .eq("away_team", m["away_team"])
            .eq("match_date", m["match_date"])
            .execute()
        )
        ghost_preds_deleted += len(resp.data) if resp.data else 0

    logger.info(
        "Cleanup complete: %d ghost matches deleted, %d ghost predictions deleted",
        len(ghost_ids),
        ghost_preds_deleted,
    )


if __name__ == "__main__":
    main()
