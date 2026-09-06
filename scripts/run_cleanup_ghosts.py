"""Clean ghost fixtures and orphan predictions from the database.

Three cleanup passes:
1. Ghost matches: unplayed match whose same matchup already has a result (±14 days)
2. Orphan predictions: predictions whose matchup already has a result in matches table
3. Stale predictions: past predictions whose match was never played (keeps track record)
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

    # --- Pass 3: Delete stale predictions WITHOUT a played match ---
    # Keep past predictions that have a corresponding result (track record).
    # Only delete those whose match was never played (cancelled, postponed,
    # or phantom fixtures that slipped through).
    all_past_preds = (
        client.table("predictions")
        .select("id,division,match_date,home_team,away_team")
        .lt("match_date", today.isoformat())
        .execute()
    )
    # Build a broad played set covering all historical prediction dates
    if all_past_preds.data:
        oldest = min(p["match_date"] for p in all_past_preds.data)
        hist_played_resp = (
            client.table("matches")
            .select("match_date,home_team,away_team")
            .not_.is_("ft_result", "null")
            .gte("match_date", oldest)
            .execute()
        )
        hist_played = {
            (r["match_date"], r["home_team"], r["away_team"]) for r in hist_played_resp.data
        }
        stale_ids = []
        for p in all_past_preds.data:
            key = (p["match_date"], p["home_team"], p["away_team"])
            if key not in hist_played:
                stale_ids.append(p["id"])
        for sid in stale_ids:
            client.table("predictions").delete().eq("id", sid).execute()
        stale_count = len(stale_ids)
        if stale_count:
            logger.info(
                "Deleted %d stale preds (no matching result)",
                stale_count,
            )
    else:
        stale_count = 0

    total = len(ghost_match_ids) + len(orphan_ids) + stale_count
    if total == 0:
        logger.info("No ghosts, orphans, or stale predictions found. Database clean.")
    else:
        logger.info(
            "Cleanup: %d ghosts, %d orphan preds, %d stale preds deleted",
            len(ghost_match_ids),
            len(orphan_ids),
            stale_count,
        )


if __name__ == "__main__":
    main()
