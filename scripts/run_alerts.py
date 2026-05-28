"""Check for smart alerts and send via Telegram.

Idempotent: uses notification_log table to skip if already sent today.
"""

import logging
import os
from datetime import date

from backend.db.client import get_supabase
from backend.notifications.alerts import send_alerts
from backend.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _already_sent(client, notification_type: str, channel: str) -> bool:
    today = date.today().isoformat()
    resp = (
        client.table("notification_log")
        .select("id")
        .eq("notification_type", notification_type)
        .eq("channel", channel)
        .eq("sent_date", today)
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def _mark_sent(client, notification_type: str, channel: str, picks_count: int = 0):
    client.table("notification_log").insert(
        {
            "notification_type": notification_type,
            "channel": channel,
            "sent_date": date.today().isoformat(),
            "picks_count": picks_count,
        }
    ).execute()


def main() -> None:
    client = get_supabase()
    premium_channel_id = os.environ.get("TELEGRAM_PREMIUM_CHANNEL_ID", "")
    admin_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if premium_channel_id:
        notifier = TelegramNotifier(chat_ids=[premium_channel_id])
    else:
        notifier = TelegramNotifier()

    if _already_sent(client, "smart_alerts", "premium"):
        logger.info("Smart alerts already sent today, skipping")
        return

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

    sent = send_alerts(notifier, active_picks, resolved, admin_chat_id=admin_chat_id)
    logger.info(
        "Alerts sent — premium: %d, streak: %d, weekly: %d",
        sent["premium"],
        sent["streak"],
        sent["weekly"],
    )

    total_sent = sent["premium"] + sent["streak"] + sent["weekly"]
    if total_sent > 0:
        _mark_sent(client, "smart_alerts", "premium", total_sent)

    alerted_ids = [p["id"] for p in active_picks if p.get("stake") == 3 and not p.get("alerted")]
    for pid in alerted_ids:
        client.table("value_bets").update({"alerted": True}).eq("id", pid).execute()
    if alerted_ids:
        logger.info("Marked %d picks as alerted", len(alerted_ids))


if __name__ == "__main__":
    main()
