import json
import logging
import os
import time
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

RESULT_LABELS = {
    "H": "Gana {home}",
    "D": "Empate",
    "A": "Gana {away}",
}

CONFIDENCE_ICON = {
    "alta": "🟢",
    "media": "🟡",
    "baja": "🔴",
}

DIVISION_FLAGS = {
    "E0": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "SP1": "🇪🇸",
    "I1": "🇮🇹",
    "D1": "🇩🇪",
    "F1": "🇫🇷",
    "EC": "🏆",
    "WC": "🌍",
}

DIVISION_NAMES = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
    "EC": "Champions League",
    "WC": "FIFA World Cup",
}

DIVISION_ORDER = ["EC", "E0", "SP1", "I1", "D1", "F1", "WC"]


def _get_chat_ids() -> list[str]:
    authorized = os.environ.get("TELEGRAM_AUTHORIZED_CHATS", "")
    if authorized:
        return [cid.strip() for cid in authorized.split(",") if cid.strip()]
    single = os.environ.get("TELEGRAM_CHAT_ID", "")
    return [single] if single else []


def _format_prediction_line(p: dict) -> str:
    """Format a single prediction into a readable line."""
    home = p["home_team"]
    away = p["away_team"]
    conf_icon = CONFIDENCE_ICON.get(p.get("confidence", "baja"), "🔴")

    result_label = RESULT_LABELS.get(p["predicted_result"], "?")
    result_text = result_label.format(home=home, away=away)

    over25 = p.get("prob_over25", 0) or 0
    goals_text = "Over 2.5 ⬆️" if over25 > 0.5 else "Under 2.5 ⬇️"

    return f"{conf_icon} <b>{home} vs {away}</b>\n   → {result_text} · {goals_text}"


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

    def send_daily_predictions(
        self,
        predictions: list[dict],
        accuracy: float | None = None,
    ) -> list[dict]:
        """Send all predictions for today to premium channel, grouped by league."""
        if not predictions:
            return []

        match_date = predictions[0].get("match_date", "")
        try:
            date_display = datetime.fromisoformat(match_date).strftime("%d %b %Y")
        except (ValueError, TypeError):
            date_display = match_date

        lines = [
            "⚽ <b>Master Prediction</b>",
            f"📅 Predicciones — {date_display}",
            "",
        ]

        by_div = {}
        for p in predictions:
            div = p.get("division", "?")
            by_div.setdefault(div, []).append(p)

        for div in DIVISION_ORDER:
            if div not in by_div:
                continue
            flag = DIVISION_FLAGS.get(div, "")
            name = DIVISION_NAMES.get(div, div)
            lines.append(f"{flag} <b>{name}</b>")
            lines.append("")
            for p in by_div[div]:
                lines.append(_format_prediction_line(p))
            lines.append("")

        for div in sorted(by_div.keys()):
            if div in DIVISION_ORDER:
                continue
            flag = DIVISION_FLAGS.get(div, "")
            name = DIVISION_NAMES.get(div, div)
            lines.append(f"{flag} <b>{name}</b>")
            lines.append("")
            for p in by_div[div]:
                lines.append(_format_prediction_line(p))
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━")
        alta = sum(1 for p in predictions if p.get("confidence") == "alta")
        media = sum(1 for p in predictions if p.get("confidence") == "media")
        baja = sum(1 for p in predictions if p.get("confidence") == "baja")
        lines.append(f"📊 {len(predictions)} predicciones · 🟢 {alta} · 🟡 {media} · 🔴 {baja}")

        if accuracy is not None:
            lines.append(f"📈 Precisión reciente: <b>{accuracy:.0%}</b>")

        lines.append("")
        lines.append("🟢 Alta · 🟡 Media · 🔴 Baja")

        return self.send_to_all("\n".join(lines), reply_markup=self._dashboard_markup())

    def send_free_predictions(
        self,
        predictions: list[dict],
        chat_id: str | None = None,
        landing_url: str = "",
        accuracy: float | None = None,
    ) -> list[dict]:
        """Send top 2 predictions to free channel with CTA."""
        if not predictions:
            return []

        top2 = predictions[:2]

        match_date = top2[0].get("match_date", "")
        try:
            date_display = datetime.fromisoformat(match_date).strftime("%d %b %Y")
        except (ValueError, TypeError):
            date_display = match_date

        lines = [
            "⚽ <b>Master Prediction — Canal Gratuito</b>",
            f"📅 Predicciones — {date_display}",
            "",
        ]

        for p in top2:
            flag = DIVISION_FLAGS.get(p.get("division", ""), "")
            name = DIVISION_NAMES.get(p.get("division", ""), "")
            lines.append(f"{flag} <b>{name}</b>")
            lines.append(_format_prediction_line(p))
            lines.append("")

        if accuracy is not None:
            lines.append(f"📈 Precisión reciente: <b>{accuracy:.0%}</b>")
            lines.append("")

        remaining = max(len(predictions) - 2, 0)
        cta = landing_url or "https://masterprediction.com"
        lines.append(f"🔒 +{remaining} predicciones completas en Premium")
        lines.append(f"👉 {cta}")

        target = chat_id or (self.chat_ids[0] if self.chat_ids else "")
        return [self.send_message("\n".join(lines), chat_id=target)]

    def send_training_summary(self, results: dict) -> list[dict]:
        lines = ["📊 <b>Modelos re-entrenados</b>", ""]
        for model_name, data in results.items():
            acc = data.get("mean_accuracy", 0)
            roi = data.get("mean_roi_pct")
            dd = data.get("mean_max_drawdown")
            line = f"  {model_name}: acc <b>{acc:.1%}</b>"
            if roi is not None:
                line += f" | ROI <b>{roi:+.1f}%</b>"
            if dd is not None:
                line += f" | DD <b>{dd:.1f}u</b>"
            lines.append(line)
        return self.send_to_all("\n".join(lines), reply_markup=self._dashboard_markup())
