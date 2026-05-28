"""Send daily Telegram notifications to free and premium channels.

Idempotent: uses notification_log table to skip if already sent today.
"""

import logging
import os
from datetime import date

from backend.betting.tracker import calculate_performance
from backend.db.client import get_supabase
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

    free_channel_id = os.environ.get("TELEGRAM_FREE_CHANNEL_ID", "")
    premium_channel_id = os.environ.get("TELEGRAM_PREMIUM_CHANNEL_ID", "")
    landing_url = os.environ.get("LANDING_URL", "https://masterprediction.com")

    if premium_channel_id:
        premium_notifier = TelegramNotifier(chat_ids=[premium_channel_id])
    else:
        premium_notifier = TelegramNotifier()
    logger.info("Premium notifier target: %s", premium_notifier.chat_ids)

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

    # Premium channel: full picks
    if picks:
        if _already_sent(client, "daily_picks", "premium"):
            logger.info("Premium daily picks already sent today, skipping")
        else:
            results = premium_notifier.send_daily_picks(picks, performance)
            ok_count = sum(1 for r in results if r.get("ok"))
            logger.info("Premium picks sent: %d/%d ok", ok_count, len(results))
            _mark_sent(client, "daily_picks", "premium", len(picks))

    # Free channel: filtered picks (no odds, no edge)
    if picks and free_channel_id:
        if _already_sent(client, "daily_picks", "free"):
            logger.info("Free daily picks already sent today, skipping")
        else:
            free_notifier = TelegramNotifier(chat_ids=[free_channel_id])
            free_results = free_notifier.send_free_picks(
                picks, chat_id=free_channel_id, landing_url=landing_url
            )
            ok_count = sum(1 for r in free_results if r.get("ok"))
            logger.info("Free picks sent: %d ok", ok_count)
            _mark_sent(client, "daily_picks", "free", len(picks))

    # Resolved summary
    today_resolved = [
        p for p in resolved if p.get("resolved_at", "").startswith(date.today().isoformat())
    ]
    if today_resolved:
        if _already_sent(client, "resolved_summary", "premium"):
            logger.info("Premium resolved summary already sent today, skipping")
        else:
            results = premium_notifier.send_resolved_summary(today_resolved)
            ok_count = sum(1 for r in results if r.get("ok"))
            logger.info("Resolved summary (premium) sent: %d/%d ok", ok_count, len(results))
            _mark_sent(client, "resolved_summary", "premium", len(today_resolved))

        # Send to free channel too when there's profit
        profit = sum(p.get("profit", 0) for p in today_resolved)
        if profit > 0 and free_channel_id:
            if _already_sent(client, "resolved_summary", "free"):
                logger.info("Free resolved summary already sent today, skipping")
            else:
                free_notifier = TelegramNotifier(chat_ids=[free_channel_id])
                wins = sum(1 for p in today_resolved if p.get("result") == "win")
                losses = len(today_resolved) - wins
                lines = [
                    "📈 <b>Resultados del Dia — Master Prediction</b>",
                    f"✅ {wins} ganados · ❌ {losses} perdidos · Profit: <b>{profit:+.2f}u</b>",
                    "",
                    f"🔒 Accede a todos los picks → {landing_url}",
                ]
                free_notifier.send_message("\n".join(lines), chat_id=free_channel_id)
                logger.info("Resolved summary (free) sent")
                _mark_sent(client, "resolved_summary", "free", len(today_resolved))


if __name__ == "__main__":
    main()
