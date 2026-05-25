"""Send daily Telegram notifications to free and premium channels."""

import logging
import os
from datetime import date

from backend.betting.tracker import calculate_performance
from backend.db.client import get_supabase
from backend.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    client = get_supabase()

    free_channel_id = os.environ.get("TELEGRAM_FREE_CHANNEL_ID", "")
    premium_channel_id = os.environ.get("TELEGRAM_PREMIUM_CHANNEL_ID", "")
    landing_url = os.environ.get("LANDING_URL", "https://masterprediction.com")

    premium_notifier = TelegramNotifier()
    logger.info("Premium notifier: %d chat(s)", len(premium_notifier.chat_ids))

    active_resp = (
        client.table("value_bets")
        .select("*")
        .is_("result", "null")
        .gte("stake", 1)
        .order("stake", desc=True)
        .execute()
    )
    picks = active_resp.data or []

    resolved_resp = client.table("value_bets").select("*").not_.is_("result", "null").execute()
    resolved = resolved_resp.data or []
    performance = calculate_performance(resolved) if resolved else None

    # Premium channel: full picks (existing behavior)
    if picks:
        if premium_channel_id:
            results = premium_notifier.send_daily_picks(picks, performance)
            ok_count = sum(1 for r in results if r.get("ok"))
            logger.info("Premium picks sent to %d/%d chats", ok_count, len(results))
        else:
            results = premium_notifier.send_daily_picks(picks, performance)
            ok_count = sum(1 for r in results if r.get("ok"))
            logger.info("Picks sent to %d/%d chats (legacy mode)", ok_count, len(results))

    # Free channel: filtered picks
    if picks and free_channel_id:
        free_results = premium_notifier.send_free_picks(
            picks, chat_id=free_channel_id, landing_url=landing_url
        )
        ok_count = sum(1 for r in free_results if r.get("ok"))
        logger.info("Free picks sent to free channel: %d ok", ok_count)

    # Resolved summary: premium only
    today_resolved = [
        p for p in resolved if p.get("resolved_at", "").startswith(date.today().isoformat())
    ]
    if today_resolved:
        results = premium_notifier.send_resolved_summary(today_resolved)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info("Resolved summary sent to %d/%d chats", ok_count, len(results))


if __name__ == "__main__":
    main()
