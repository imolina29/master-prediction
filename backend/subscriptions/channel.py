import logging
import os

import httpx

logger = logging.getLogger(__name__)

LANDING_URL = os.environ.get("LANDING_URL", "https://masterprediction.com")


class ChannelManager:
    def __init__(
        self,
        bot_token: str | None = None,
        premium_channel_id: str | None = None,
        admin_chat_id: str | None = None,
    ):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.premium_channel_id = premium_channel_id or os.environ.get(
            "TELEGRAM_PREMIUM_CHANNEL_ID", ""
        )
        self.admin_chat_id = admin_chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def _call(self, method: str, payload: dict) -> dict:
        resp = httpx.post(f"{self.base_url}/{method}", json=payload, timeout=15)
        result = resp.json()
        if not result.get("ok"):
            logger.error("Telegram API %s failed: %s", method, result)
        return result

    def create_invite_link(self) -> str | None:
        result = self._call(
            "createChatInviteLink",
            {"chat_id": self.premium_channel_id, "member_limit": 1},
        )
        if result.get("ok"):
            return result["result"]["invite_link"]
        return None

    def send_invite_to_user(self, telegram_user_id: str) -> bool:
        link = self.create_invite_link()
        if not link:
            logger.error("Failed to create invite link for user %s", telegram_user_id)
            return False

        text = (
            "🎉 <b>Welcome to Master Prediction Premium!</b>\n\n"
            f"Join the premium channel here:\n{link}\n\n"
            "You'll receive all picks with odds, edge, and confidence daily."
        )
        result = self._call(
            "sendMessage",
            {"chat_id": telegram_user_id, "text": text, "parse_mode": "HTML"},
        )
        return result.get("ok", False)

    def revoke_user_access(self, telegram_user_id: str) -> None:
        self._call(
            "banChatMember",
            {"chat_id": self.premium_channel_id, "user_id": int(telegram_user_id)},
        )
        self._call(
            "unbanChatMember",
            {"chat_id": self.premium_channel_id, "user_id": int(telegram_user_id)},
        )

        text = (
            "Your Master Prediction Premium subscription has ended.\n\n"
            f"Renew anytime at {LANDING_URL}"
        )
        self._call(
            "sendMessage",
            {"chat_id": telegram_user_id, "text": text},
        )

    def send_admin_notification(self, text: str) -> None:
        if not self.admin_chat_id:
            return
        self._call(
            "sendMessage",
            {"chat_id": self.admin_chat_id, "text": text, "parse_mode": "HTML"},
        )
