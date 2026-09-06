"""Clean ghost fixtures and orphan predictions from the database.

Three cleanup passes:
1. Ghost matches: unplayed match whose same matchup already has a result (±14 days)
2. Orphan predictions: predictions whose matchup already has a result in matches table
3. Stale predictions: predictions for dates that already passed (yesterday or older)
"""

import logging
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _fetch_all(client, table: str, select: str, filters: dict) -> list[dict]:
    """Paginated fetch from Supabase."""
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        q = client.table(table).select(select)
        for method, args in filters.items():
            q = getattr(q, method)(*args)
        resp = q.range(offset, offset + page_size - 1).execute()
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_rows


def main():
    from backend.db.client import get_supabase

    client = get_supabase()

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    window_start = (today - timedelta(days=14)).isoformat()
    window_end = (today + timedelta(days=30)).isoformat()

    # --- Build played set: all matches with results in the window ---
    played_resp = (
        client.table("matches")
        .select("division,home_team,away_team")
        .gte("match_date", window_start)
        .lte("match_date", window_end)
        .not_.is_("ft_result", "null")
        .execute()
    )
    played_set = {(r["division"], r["home_team"], r["away_team"]) for r in played_resp.data}
    logger.info("Found %d played matches for ghost detection", len(played_set))

    # --- Pass 1: Delete ghost MATCHES ---
    unplayed_resp = (
        client.table("matches")
        .select("id,division,match_date,home_team,away_team")
        .gte("match_date", window_start)
        .lte("match_date", window_end)
        .is_("ft_result", "null")
        .execute()
    )
    ghost_match_ids = []
    for m in unplayed_resp.data:
        if (m["division"], m["home_team"], m["away_team"]) in played_set:
            ghost_match_ids.append(m["id"])
            logger.info(
                "Ghost match: %s vs %s (%s) on %s",
                m["home_team"],
                m["away_team"],
                m["division"],
                m["match_date"],
            )

    for mid in ghost_match_ids:
        client.table("matches").delete().eq("id", mid).execute()
    if ghost_match_ids:
        logger.info("Deleted %d ghost matches", len(ghost_match_ids))

    # --- Pass 2: Delete orphan PREDICTIONS (matchup already played) ---
    upcoming_preds = (
        client.table("predictions")
        .select("id,division,match_date,home_team,away_team")
        .gte("match_date", today.isoformat())
        .execute()
    )
    orphan_ids = []
    for p in upcoming_preds.data:
        if (p["division"], p["home_team"], p["away_team"]) in played_set:
            orphan_ids.append(p["id"])
            logger.info(
                "Orphan prediction: %s vs %s (%s) on %s",
                p["home_team"],
                p["away_team"],
                p["division"],
                p["match_date"],
            )

    for pid in orphan_ids:
        client.table("predictions").delete().eq("id", pid).execute()
    if orphan_ids:
        logger.info("Deleted %d orphan predictions", len(orphan_ids))

    # --- Pass 3: Delete stale predictions (date already passed) ---
    stale_resp = (
        client.table("predictions")
        .select("id", count="exact")
        .lt("match_date", today.isoformat())
        .execute()
    )
    stale_count = stale_resp.count or 0
    if stale_count > 0:
        # Delete in batches
        while True:
            batch = (
                client.table("predictions")
                .select("id")
                .lt("match_date", today.isoformat())
                .limit(500)
                .execute()
            )
            if not batch.data:
                break
            for row in batch.data:
                client.table("predictions").delete().eq("id", row["id"]).execute()
        logger.info("Deleted %d stale predictions (past dates)", stale_count)

    total = len(ghost_match_ids) + len(orphan_ids) + stale_count
    if total == 0:
        logger.info("No ghosts, orphans, or stale predictions found. Database clean.")
    else:
        logger.info(
            "Cleanup complete: %d ghost matches, %d orphan predictions, %d stale predictions deleted",
            len(ghost_match_ids),
            len(orphan_ids),
            stale_count,
        )


if __name__ == "__main__":
    main()
