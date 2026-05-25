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

DIVISION_FLAGS = {
    "E0": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "SP1": "🇪🇸",
    "I1": "🇮🇹",
    "D1": "🇩🇪",
    "F1": "🇫🇷",
    "EC": "🏆",
    "WC": "🌍",
}


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

        sorted_picks = sorted(picks, key=lambda p: (-p["stake"], -p["edge"]))
        top5 = sorted_picks[:5]

        lines = [
            "⚽ <b>Master Prediction</b>",
            f"📅 Top {len(top5)} Picks del Dia",
            "",
        ]

        for i, p in enumerate(top5, 1):
            icon = STAKE_ICONS.get(p["stake"], "🟡")
            market = MARKET_LABELS.get(p["market"], p["market"])
            flag = DIVISION_FLAGS.get(p.get("division", ""), "")
            conf_bar = "█" * p["stake"] + "░" * (3 - p["stake"])

            lines.append(f"<b>{i}.</b> {flag} <b>{p['home_team']} vs {p['away_team']}</b>")
            lines.append(
                f"   {icon} {market} · Cuota: <b>{p['odd']:.2f}</b> · Edge: <b>{p['edge']:+.1%}</b>"
            )
            lines.append(f"   Confianza: [{conf_bar}] {p['stake']}u")
            lines.append("")

        if len(sorted_picks) > 5:
            lines.append(f"📋 +{len(sorted_picks) - 5} picks mas en el dashboard")
            lines.append("")

        if performance:
            profit = performance.get("profit", 0)
            roi = performance.get("roi", 0)
            wins = performance.get("wins", 0)
            total = performance.get("total_picks", 0)
            hit_rate = performance.get("hit_rate", 0)
            emoji = "📈" if profit >= 0 else "📉"
            lines.append("━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"{emoji} <b>Rendimiento Acumulado</b>")
            lines.append(f"   Profit: <b>{profit:+.1f}u</b> · ROI: <b>{roi:.1f}%</b>")
            lines.append(f"   Record: {wins}/{total} ({hit_rate:.0%} acierto)")

        return self.send_to_all("\n".join(lines), reply_markup=self._dashboard_markup())

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

    def send_resolved_summary(self, resolved_today: list[dict]) -> list[dict]:
        if not resolved_today:
            return []

        wins = sum(1 for p in resolved_today if p.get("result") == "win")
        losses = len(resolved_today) - wins
        profit = sum(p.get("profit", 0) for p in resolved_today)

        emoji = "🎉" if profit >= 0 else "😔"
        lines = [
            f"{emoji} <b>Resultados del Dia</b>",
            f"✅ {wins} ganados · ❌ {losses} perdidos · Profit: <b>{profit:+.2f}u</b>",
            "",
        ]

        for p in resolved_today:
            icon = "✅" if p.get("result") == "win" else "❌"
            lines.append(
                f"{icon} {p['home_team']} vs {p['away_team']} · <b>{p['profit']:+.2f}u</b>"
            )

        return self.send_to_all("\n".join(lines), reply_markup=self._dashboard_markup())

    def send_free_picks(
        self, picks: list[dict], chat_id: str | None = None, landing_url: str = ""
    ) -> list[dict]:
        free = build_free_picks(picks)
        if not free:
            return []

        lines = [
            "⚽ <b>Master Prediction — Free Pick</b>",
            "",
        ]
        for p in free:
            flag = DIVISION_FLAGS.get(p.get("division", ""), "")
            market = MARKET_LABELS.get(p["market"], p["market"])
            lines.append(f"{flag} <b>{p['home_team']} vs {p['away_team']}</b>")
            lines.append(f"📊 {market}")
            lines.append("")

        cta = landing_url or "https://masterprediction.com"
        lines.append(f"🔒 All picks + odds + edge → {cta}")

        target = chat_id or (self.chat_ids[0] if self.chat_ids else "")
        return [self.send_message("\n".join(lines), chat_id=target)]


FREE_DIVISIONS = {"E0", "WC"}


def build_free_picks(picks: list[dict]) -> list[dict]:
    filtered = [
        p
        for p in picks
        if p.get("market", "").startswith("1x2") and p.get("division") in FREE_DIVISIONS
    ]
    filtered.sort(key=lambda p: (-p.get("stake", 0), -p.get("edge", 0)))
    return filtered[:2]
