import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from backend.betting.value import generate_picks
    from backend.db.client import get_supabase

    client = get_supabase()

    logger.info("Loading predictions...")
    pred_resp = client.table("predictions").select("*").execute()
    predictions = pred_resp.data
    if not predictions:
        logger.info("No predictions found.")
        return

    logger.info("Loading matches with odds (pending results)...")
    matches_resp = (
        client.table("matches")
        .select(
            "match_date, home_team, away_team, division,"
            " odd_home, odd_draw, odd_away, odd_over25, odd_under25"
        )
        .is_("ft_result", "null")
        .not_.is_("odd_home", "null")
        .execute()
    )
    matches_with_odds = matches_resp.data
    if not matches_with_odds:
        logger.info("No matches with odds found.")
        return

    logger.info(
        "Generating picks from %d predictions and %d matches with odds...",
        len(predictions),
        len(matches_with_odds),
    )
    picks = generate_picks(predictions, matches_with_odds)

    if not picks:
        logger.info("No value bets found.")
        return

    logger.info("Uploading %d picks to value_bets...", len(picks))
    for pick in picks:
        client.table("value_bets").upsert(
            pick, on_conflict="match_date,home_team,away_team,market"
        ).execute()

    logger.info("Done! %d value bets uploaded.", len(picks))


if __name__ == "__main__":
    main()
