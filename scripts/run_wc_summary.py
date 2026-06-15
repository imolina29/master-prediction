"""Send daily WC prediction summary to admin Telegram chat."""

import logging
import os
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

COL_TZ = timezone(timedelta(hours=-5))
RESULT_LABELS = {"H": "Local", "D": "Empate", "A": "Visitante"}


def main():
    from backend.notifications.telegram import TelegramNotifier
    from supabase import create_client

    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    admin_chat = os.environ["TELEGRAM_CHAT_ID"]

    today_col = datetime.now(COL_TZ).strftime("%Y-%m-%d")

    matches_resp = (
        client.table("matches")
        .select("*")
        .eq("division", "WC")
        .eq("match_date", today_col)
        .not_.is_("ft_result", "null")
        .order("match_date")
        .execute()
    )
    today_matches = matches_resp.data or []

    if not today_matches:
        logger.info("No WC results for %s, skipping summary.", today_col)
        return

    preds_resp = client.table("predictions").select("*").eq("division", "WC").execute()
    pred_map = {}
    for p in preds_resp.data or []:
        pred_map[(p["match_date"], p["home_team"], p["away_team"])] = p

    all_matches = (
        client.table("matches")
        .select("match_date,home_team,away_team,ft_result")
        .eq("division", "WC")
        .not_.is_("ft_result", "null")
        .order("match_date")
        .execute()
    )

    total_hits = 0
    total_resolved = 0
    for m in all_matches.data or []:
        p = pred_map.get((m["match_date"], m["home_team"], m["away_team"]))
        if not p:
            continue
        total_resolved += 1
        if p["predicted_result"] == m["ft_result"]:
            total_hits += 1

    day_hits = 0
    day_total = 0
    match_lines = []

    for m in today_matches:
        key = (m["match_date"], m["home_team"], m["away_team"])
        p = pred_map.get(key)
        if not p:
            continue
        day_total += 1
        hit = p["predicted_result"] == m["ft_result"]
        if hit:
            day_hits += 1

        icon = "✅" if hit else "❌"
        score = f"{m['ft_home_goals']}-{m['ft_away_goals']}"
        pred_label = RESULT_LABELS.get(p["predicted_result"], "?")
        conf = p.get("confidence", "?")

        prob_d = p.get("prob_draw") or 0
        alert = " ⚠️" if prob_d > 0.25 else ""

        match_lines.append(
            f"{icon} {m['home_team']} {score} {m['away_team']}\n"
            f"    Pred: {pred_label} ({conf}){alert}"
        )

    if not match_lines:
        logger.info("No predictions matched for today's WC results.")
        return

    if total_resolved:
        pct = total_hits / total_resolved
        global_rate = f"{total_hits}/{total_resolved} ({pct:.0%})"
    else:
        global_rate = "—"

    emoji = "🎉" if day_hits > day_total / 2 else "📊"
    lines = [
        f"{emoji} <b>Resumen Mundial — {today_col}</b>",
        "",
        f"<b>Hoy: {day_hits}/{day_total}</b>",
        "",
    ]
    lines.extend(match_lines)
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🏆 <b>Acumulado: {global_rate}</b>")

    draws_today = sum(1 for m in today_matches if m["ft_result"] == "D")
    if draws_today:
        lines.append(f"🤝 Empates hoy: {draws_today}/{day_total}")

    text = "\n".join(lines)

    notifier = TelegramNotifier()
    result = notifier.send_message(text, chat_id=admin_chat)
    if result.get("ok"):
        logger.info("WC summary sent to admin chat.")
    else:
        logger.error("Failed to send WC summary: %s", result)


if __name__ == "__main__":
    main()
