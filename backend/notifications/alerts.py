import logging
from datetime import date, timedelta

from backend.notifications.telegram import MARKET_LABELS, TelegramNotifier

logger = logging.getLogger(__name__)

WIN_STREAK_THRESHOLD = 5
LOSS_STREAK_THRESHOLD = 3


def check_high_confidence_picks(picks: list[dict]) -> list[dict]:
    return [p for p in picks if p.get("stake") == 3 and not p.get("alerted")]


def check_streaks(resolved: list[dict]) -> dict | None:
    if not resolved:
        return None

    sorted_picks = sorted(resolved, key=lambda p: p.get("resolved_at", ""), reverse=True)

    streak_type = sorted_picks[0].get("result")
    if streak_type not in ("win", "loss"):
        return None

    streak_picks = []
    for p in sorted_picks:
        if p.get("result") == streak_type:
            streak_picks.append(p)
        else:
            break

    count = len(streak_picks)
    threshold = WIN_STREAK_THRESHOLD if streak_type == "win" else LOSS_STREAK_THRESHOLD

    if count >= threshold:
        return {"type": streak_type, "count": count, "picks": streak_picks}
    return None


def build_weekly_summary(resolved: list[dict], start_date: date, end_date: date) -> dict | None:
    week_picks = [
        p
        for p in resolved
        if start_date.isoformat() <= p.get("match_date", "") <= end_date.isoformat()
    ]
    if not week_picks:
        return None

    wins = sum(1 for p in week_picks if p["result"] == "win")
    losses = len(week_picks) - wins
    profit = sum(p["profit"] for p in week_picks)
    total_stake = sum(p["stake"] for p in week_picks)
    roi = (profit / total_stake * 100) if total_stake else 0

    by_league: dict[str, float] = {}
    by_market: dict[str, float] = {}
    for p in week_picks:
        by_league[p["division"]] = by_league.get(p["division"], 0) + p["profit"]
        mkt = "1x2" if p["market"].startswith("1x2") else "Over/Under"
        by_market[mkt] = by_market.get(mkt, 0) + p["profit"]

    best_league = max(by_league, key=by_league.get) if by_league else ""
    best_market = max(by_market, key=by_market.get) if by_market else ""

    return {
        "total": len(week_picks),
        "wins": wins,
        "losses": losses,
        "profit": round(profit, 2),
        "roi": round(roi, 1),
        "best_league": best_league,
        "best_league_profit": round(by_league.get(best_league, 0), 1),
        "best_market": best_market,
        "best_market_profit": round(by_market.get(best_market, 0), 1),
    }


def _format_premium_pick(pick: dict) -> str:
    market = MARKET_LABELS.get(pick["market"], pick["market"])
    return (
        "🔥 <b>PICK PREMIUM</b>\n\n"
        f"🟢🟢🟢 <b>{pick['home_team']} vs {pick['away_team']}</b>\n"
        f"{market} · Cuota: {pick['odd']:.2f} · Edge: {pick['edge']:+.1%}\n\n"
        "👉 Analisis detallado en el dashboard"
    )


def _format_streak(streak: dict) -> str:
    if streak["type"] == "win":
        profit = sum(p["profit"] for p in streak["picks"])
        lines = [
            f"🔥 <b>Racha de {streak['count']} aciertos!</b>\n",
            f"Profit en racha: <b>{profit:+.1f}u</b>\n",
        ]
        for p in streak["picks"][:5]:
            lines.append(f"✅ {p['home_team']} vs {p['away_team']} {p['profit']:+.2f}u")
    else:
        lines = [
            f"⚠️ <b>Racha de {streak['count']} fallos</b>\n",
            "Precaucion: considera reducir stakes temporalmente.",
        ]
    return "\n".join(lines)


def _format_weekly_summary(summary: dict, week_num: int) -> str:
    return (
        f"📊 <b>Master Prediction — Semana {week_num}</b>\n\n"
        f"Picks: {summary['total']} | ✅ {summary['wins']} | ❌ {summary['losses']}\n"
        f"Profit: <b>{summary['profit']:+.1f}u</b> | ROI: {summary['roi']}%\n\n"
        f"Mejor liga: {summary['best_league']} ({summary['best_league_profit']:+.1f}u)\n"
        f"Mejor mercado: {summary['best_market']} ({summary['best_market_profit']:+.1f}u)"
    )


def send_alerts(
    notifier: TelegramNotifier,
    active_picks: list[dict],
    resolved: list[dict],
    today: date | None = None,
) -> dict:
    today = today or date.today()
    sent = {"premium": 0, "streak": 0, "weekly": 0}

    markup = notifier._dashboard_markup()

    premium = check_high_confidence_picks(active_picks)
    for pick in premium:
        text = _format_premium_pick(pick)
        notifier.send_to_all(text, reply_markup=markup)
        sent["premium"] += 1

    streak = check_streaks(resolved)
    if streak:
        text = _format_streak(streak)
        notifier.send_to_all(text, reply_markup=markup)
        sent["streak"] = 1

    if today.weekday() == 6:
        start = today - timedelta(days=6)
        week_num = today.isocalendar()[1]
        summary = build_weekly_summary(resolved, start, today)
        if summary:
            text = _format_weekly_summary(summary, week_num)
            notifier.send_to_all(text, reply_markup=markup)
            sent["weekly"] = 1

    return sent
