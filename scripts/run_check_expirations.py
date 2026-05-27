"""Check for expired subscriptions and revoke channel access."""

import logging
import os
from datetime import datetime, timezone

from backend.db.client import get_supabase
from backend.subscriptions.channel import ChannelManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    client = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    resp = (
        client.table("subscriptions")
        .select("*")
        .eq("status", "active")
        .not_.is_("current_period_end", "null")
        .lt("current_period_end", now)
        .execute()
    )
    expired = resp.data or []

    if not expired:
        logger.info("No expired subscriptions")
        return

    channel_mgr = ChannelManager()

    for sub in expired:
        client.table("subscriptions").update(
            {"status": "expired", "updated_at": now}
        ).eq("id", sub["id"]).execute()

        try:
            channel_mgr.revoke_user_access(sub["telegram_user_id"])
        except Exception as e:
            logger.error("Failed to revoke for %s: %s", sub["telegram_user_id"], e)

        logger.info("Expired: %s (@%s)", sub["telegram_user_id"], sub.get("telegram_username", ""))

    logger.info("Processed %d expired subscriptions", len(expired))


if __name__ == "__main__":
    main()
