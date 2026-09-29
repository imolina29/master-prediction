"""Send daily Telegram notifications to free and premium channels.

Premium: all predictions for today grouped by league.
Free: top 2 predictions + CTA to premium.

Idempotent: uses notification_log table to skip if already sent today.
"""

import logging
import os
from datetime import date, datetime, timedelta, timezone

from backend.db.client import get_supabase
from backend.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONFIDENCE_ORDER = {"alta": 0, "media": 1, "baja": 2}


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


def _get_todays_predictions(client) -> list[dict]:
    """Fetch predictions for today's matches."""
    col_tz = timezone(timedelta(hours=-5))
    today_col = datetime.now(col_tz).date().isoformat()

    resp = client.table("predictions").select("*").eq("match_date", today_col).execute()
    preds = resp.data or []
    preds.sort(key=lambda p: (CONFIDENCE_ORDER.get(p.get("confidence", "baja"), 2), p["home_team"]))
    return preds


def _get_recent_accuracy(client) -> float | None:
    """Get accuracy from the most recent weekly report."""
    resp = (
        client.table("weekly_reports")
        .select("hit_rate")
        .order("week_start", desc=True)
        .limit(1)
        .execute()
    )
    if resp.data and resp.data[0].get("hit_rate"):
        return resp.data[0]["hit_rate"]
    return None


def main() -> None:
    client = get_supabase()

    free_channel_id = os.environ.get("TELEGRAM_FREE_CHANNEL_ID", "")
    premium_channel_id = os.environ.get("TELEGRAM_PREMIUM_CHANNEL_ID", "")
    landing_url = os.environ.get("LANDING_URL", "https://masterprediction.com")

    preds = _get_todays_predictions(client)
    if not preds:
        logger.info("No predictions for today, skipping notifications")
        return

    logger.info("Found %d predictions for today", len(preds))
    accuracy = _get_recent_accuracy(client)

    if premium_channel_id:
        premium_notifier = TelegramNotifier(chat_ids=[premium_channel_id])
    else:
        premium_notifier = TelegramNotifier()

    # Premium channel: all predictions
    if _already_sent(client, "daily_predictions", "premium"):
        logger.info("Premium daily predictions already sent today, skipping")
    else:
        results = premium_notifier.send_daily_predictions(preds, accuracy=accuracy)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info("Premium predictions sent: %d/%d ok", ok_count, len(results))
        _mark_sent(client, "daily_predictions", "premium", len(preds))

    # Free channel: top 2 predictions
    if free_channel_id:
        if _already_sent(client, "daily_predictions", "free"):
            logger.info("Free daily predictions already sent today, skipping")
        else:
            free_notifier = TelegramNotifier(chat_ids=[free_channel_id])
            free_results = free_notifier.send_free_predictions(
                preds,
                chat_id=free_channel_id,
                landing_url=landing_url,
                accuracy=accuracy,
            )
            ok_count = sum(1 for r in free_results if r.get("ok"))
            logger.info("Free predictions sent: %d ok", ok_count)
            _mark_sent(client, "daily_predictions", "free", min(2, len(preds)))


if __name__ == "__main__":
    main()
