import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

MARKET_LABELS = {
    "1x2_home": "Victoria Local",
    "1x2_draw": "Empate",
    "1x2_away": "Victoria Visitante",
    "over25": "Over 2.5",
    "under25": "Under 2.5",
}

STAKE_ICONS = {3: "🟢🟢🟢", 2: "🟢🟢", 1: "🟡"}


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(
        self, text: str, reply_markup: dict | None = None, parse_mode: str = "HTML"
    ) -> dict:
        payload: dict = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        resp = httpx.post(f"{self.base_url}/sendMessage", json=payload, timeout=15)
        result = resp.json()
        if not result.get("ok"):
            logger.error("Telegram send failed: %s", result)
        return result

    def send_daily_picks(self, picks: list[dict], performance: dict | None = None) -> dict | None:
        if not picks:
            logger.info("No picks to notify")
            return None

        lines = ["⚽ <b>Master Prediction</b> · {} Picks\n".format(len(picks))]

        for p in picks:
            icon = STAKE_ICONS.get(p["stake"], "🟡")
            market = MARKET_LABELS.get(p["market"], p["market"])
            lines.append(
                f"{icon} <b>{p['home_team']} vs {p['away_team']}</b>\n"
                f"   {market} · Cuota: {p['odd']:.2f} · Edge: {p['edge']:+.1%}"
            )

        if performance:
            profit = performance.get("profit", 0)
            roi = performance.get("roi", 0)
            emoji = "📈" if profit >= 0 else "📉"
            lines.append(f"\n{emoji} ROI acumulado: <b>{roi:.1f}%</b> ({profit:+.1f}u)")

        lines.append("\n👉 Analisis detallado en el dashboard")

        text = "\n".join(lines)

        dashboard_url = os.environ.get("DASHBOARD_URL", "")
        reply_markup = None
        if dashboard_url:
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📊 Abrir Dashboard", "url": dashboard_url}],
                ]
            }

        return self.send_message(text, reply_markup=reply_markup)

    def send_resolved_summary(self, resolved_today: list[dict]) -> dict | None:
        if not resolved_today:
            return None

        wins = sum(1 for p in resolved_today if p.get("result") == "win")
        losses = len(resolved_today) - wins
        profit = sum(p.get("profit", 0) for p in resolved_today)

        emoji = "🎉" if profit >= 0 else "😔"
        lines = [
            f"{emoji} <b>Resultados del Dia</b> · {wins}✅ {losses}❌\n",
            f"Profit: <b>{profit:+.2f}u</b>",
        ]

        for p in resolved_today:
            icon = "✅" if p.get("result") == "win" else "❌"
            lines.append(f"{icon} {p['home_team']} vs {p['away_team']} · {p['profit']:+.2f}u")

        dashboard_url = os.environ.get("DASHBOARD_URL", "")
        reply_markup = None
        if dashboard_url:
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "📊 Ver Rendimiento", "url": dashboard_url}],
                ]
            }

        return self.send_message("\n".join(lines), reply_markup=reply_markup)
