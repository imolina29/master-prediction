"""Send daily Telegram notification with recommended picks and resolved results."""

import logging
from datetime import date

from backend.betting.tracker import calculate_performance
from backend.db.client import get_supabase
from backend.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    client = get_supabase()
    notifier = TelegramNotifier()

    logger.info("Sending to %d chat(s)", len(notifier.chat_ids))

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

    if picks:
        results = notifier.send_daily_picks(picks, performance)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info(
            "Daily picks sent to %d/%d chats (%d picks)", ok_count, len(results), len(picks)
        )
    else:
        logger.info("No recommended picks today, skipping notification")

    today_resolved = [
        p for p in resolved if p.get("resolved_at", "").startswith(date.today().isoformat())
    ]
    if today_resolved:
        results = notifier.send_resolved_summary(today_resolved)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info("Resolved summary sent to %d/%d chats", ok_count, len(results))


if __name__ == "__main__":
    main()
