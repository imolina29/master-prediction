from dataclasses import dataclass


@dataclass
class Subscription:
    telegram_user_id: str
    provider_customer_id: str
    provider_subscription_id: str
    plan: str
    status: str = "active"
    telegram_username: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    id: str | None = None


@dataclass
class Payment:
    subscription_id: str
    provider_payment_id: str
    amount: float
    status: str
    id: str | None = None
    paid_at: str | None = None
