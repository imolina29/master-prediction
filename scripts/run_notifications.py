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
        results = premium_notifier.send_daily_picks(picks, performance)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info("Premium picks sent: %d/%d ok", ok_count, len(results))

    # Free channel: filtered picks (no odds, no edge)
    if picks and free_channel_id:
        free_notifier = TelegramNotifier(chat_ids=[free_channel_id])
        free_results = free_notifier.send_free_picks(
            picks, chat_id=free_channel_id, landing_url=landing_url
        )
        ok_count = sum(1 for r in free_results if r.get("ok"))
        logger.info("Free picks sent: %d ok", ok_count)

    # Resolved summary
    today_resolved = [
        p for p in resolved if p.get("resolved_at", "").startswith(date.today().isoformat())
    ]
    if today_resolved:
        results = premium_notifier.send_resolved_summary(today_resolved)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info("Resolved summary (premium) sent: %d/%d ok", ok_count, len(results))

        # Send to free channel too when there's profit
        profit = sum(p.get("profit", 0) for p in today_resolved)
        if profit > 0 and free_channel_id:
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


if __name__ == "__main__":
    main()
