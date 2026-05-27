"""Check for smart alerts and send via Telegram."""

import logging
import os

from backend.db.client import get_supabase
from backend.notifications.alerts import send_alerts
from backend.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    client = get_supabase()
    premium_channel_id = os.environ.get("TELEGRAM_PREMIUM_CHANNEL_ID", "")
    if premium_channel_id:
        notifier = TelegramNotifier(chat_ids=[premium_channel_id])
    else:
        notifier = TelegramNotifier()

    active_resp = (
        client.table("value_bets").select("*").is_("result", "null").eq("alerted", False).execute()
    )
    active_picks = active_resp.data or []

    resolved_resp = (
        client.table("value_bets")
        .select("*")
        .not_.is_("result", "null")
        .order("resolved_at", desc=True)
        .limit(50)
        .execute()
    )
    resolved = resolved_resp.data or []

    sent = send_alerts(notifier, active_picks, resolved)
    logger.info(
        "Alerts sent — premium: %d, streak: %d, weekly: %d",
        sent["premium"],
        sent["streak"],
        sent["weekly"],
    )

    alerted_ids = [p["id"] for p in active_picks if p.get("stake") == 3 and not p.get("alerted")]
    for pid in alerted_ids:
        client.table("value_bets").update({"alerted": True}).eq("id", pid).execute()
    if alerted_ids:
        logger.info("Marked %d picks as alerted", len(alerted_ids))


if __name__ == "__main__":
    main()
