import json
import logging
import os
import time

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


def _get_chat_ids() -> list[str]:
    authorized = os.environ.get("TELEGRAM_AUTHORIZED_CHATS", "")
    if authorized:
        return [cid.strip() for cid in authorized.split(",") if cid.strip()]
    single = os.environ.get("TELEGRAM_CHAT_ID", "")
    return [single] if single else []


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_ids: list[str] | None = None):
        self.token = token or os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_ids = chat_ids or _get_chat_ids()
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        reply_markup: dict | None = None,
        parse_mode: str = "HTML",
    ) -> dict:
        target = chat_id or (self.chat_ids[0] if self.chat_ids else "")
        payload: dict = {
            "chat_id": target,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        resp = httpx.post(f"{self.base_url}/sendMessage", json=payload, timeout=15)
        result = resp.json()
        if not result.get("ok"):
            logger.error("Telegram send failed (chat %s): %s", target, result)
        return result

    def send_to_all(self, text: str, reply_markup: dict | None = None) -> list[dict]:
        results = []
        for cid in self.chat_ids:
            result = self.send_message(text, chat_id=cid, reply_markup=reply_markup)
            results.append(result)
            time.sleep(0.1)
        return results

    def _dashboard_markup(self) -> dict | None:
        dashboard_url = os.environ.get("DASHBOARD_URL", "")
        if not dashboard_url:
            return None
        return {
            "inline_keyboard": [
                [{"text": "📊 Abrir Dashboard", "url": dashboard_url}],
            ]
        }

    def send_daily_picks(self, picks: list[dict], performance: dict | None = None) -> list[dict]:
        if not picks:
            logger.info("No picks to notify")
            return []

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

        return self.send_to_all("\n".join(lines), reply_markup=self._dashboard_markup())

    def send_resolved_summary(self, resolved_today: list[dict]) -> list[dict]:
        if not resolved_today:
            return []

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

        return self.send_to_all("\n".join(lines), reply_markup=self._dashboard_markup())
