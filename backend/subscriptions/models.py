from dataclasses import dataclass


@dataclass
class Subscription:
    telegram_user_id: str
    stripe_customer_id: str
    stripe_subscription_id: str
    plan: str
    status: str = "active"
    telegram_username: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    id: str | None = None


@dataclass
class Payment:
    subscription_id: str
    stripe_payment_intent_id: str
    amount_usd: float
    status: str
    id: str | None = None
    paid_at: str | None = None
