"""Send daily Telegram notification with recommended picks and resolved results."""

import logging

from backend.betting.tracker import calculate_performance
from backend.db.client import get_supabase
from backend.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    client = get_supabase()
    notifier = TelegramNotifier()

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
        result = notifier.send_daily_picks(picks, performance)
        if result and result.get("ok"):
            logger.info("Daily picks notification sent (%d picks)", len(picks))
        else:
            logger.warning("Failed to send picks notification: %s", result)
    else:
        logger.info("No recommended picks today, skipping notification")

    today_resolved = [
        p
        for p in resolved
        if p.get("resolved_at", "").startswith(__import__("datetime").date.today().isoformat())
    ]
    if today_resolved:
        result = notifier.send_resolved_summary(today_resolved)
        if result and result.get("ok"):
            logger.info("Resolved summary sent (%d picks)", len(today_resolved))


if __name__ == "__main__":
    main()
