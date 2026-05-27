import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, supabase_client):
        self.client = supabase_client

    def create_subscription(
        self,
        telegram_user_id: str,
        telegram_username: str | None,
        provider_customer_id: str,
        provider_subscription_id: str,
        plan: str,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> dict:
        row = {
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "provider_customer_id": provider_customer_id,
            "provider_subscription_id": provider_subscription_id,
            "plan": plan,
            "status": "active",
            "current_period_start": period_start,
            "current_period_end": period_end,
        }
        resp = self.client.table("subscriptions").insert(row).execute()
        logger.info("Created subscription for telegram_user_id=%s", telegram_user_id)
        return resp.data[0]

    def get_active_subscription(self, telegram_user_id: str) -> dict | None:
        resp = (
            self.client.table("subscriptions")
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .eq("status", "active")
            .execute()
        )
        return resp.data[0] if resp.data else None

    def get_subscription_by_provider_id(self, provider_subscription_id: str) -> dict | None:
        resp = (
            self.client.table("subscriptions")
            .select("*")
            .eq("provider_subscription_id", provider_subscription_id)
            .execute()
        )
        return resp.data[0] if resp.data else None

    def update_subscription_status(self, provider_subscription_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.client.table("subscriptions").update({"status": status, "updated_at": now}).eq(
            "provider_subscription_id", provider_subscription_id
        ).execute()
        logger.info("Updated subscription %s to status=%s", provider_subscription_id, status)

    def update_subscription_period(
        self, provider_subscription_id: str, period_start: str, period_end: str
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.client.table("subscriptions").update(
            {
                "current_period_start": period_start,
                "current_period_end": period_end,
                "updated_at": now,
            }
        ).eq("provider_subscription_id", provider_subscription_id).execute()

    def cancel_subscription(self, provider_subscription_id: str) -> None:
        self.update_subscription_status(provider_subscription_id, "cancelled")

    def record_payment(
        self,
        subscription_id: str,
        provider_payment_id: str,
        amount: float,
        status: str,
    ) -> dict:
        row = {
            "subscription_id": subscription_id,
            "provider_payment_id": provider_payment_id,
            "amount": amount,
            "status": status,
        }
        resp = self.client.table("payments").insert(row).execute()
        logger.info(
            "Recorded payment %s for subscription %s",
            provider_payment_id,
            subscription_id,
        )
        return resp.data[0]

    def get_all_subscriptions(self) -> list[dict]:
        resp = (
            self.client.table("subscriptions").select("*").order("created_at", desc=True).execute()
        )
        return resp.data or []

    def get_all_payments(self) -> list[dict]:
        resp = self.client.table("payments").select("*").order("paid_at", desc=True).execute()
        return resp.data or []
