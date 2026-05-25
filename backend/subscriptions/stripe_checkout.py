import os

import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

PRICE_IDS = {
    "monthly": os.environ.get("STRIPE_PRICE_MONTHLY", ""),
    "quarterly": os.environ.get("STRIPE_PRICE_QUARTERLY", ""),
}

SUCCESS_URL = os.environ.get("LANDING_URL", "https://masterprediction.com") + "/success.html"
CANCEL_URL = os.environ.get("LANDING_URL", "https://masterprediction.com")


def create_checkout_url(
    telegram_user_id: str,
    telegram_username: str,
    plan: str = "monthly",
    promo_code: str | None = None,
) -> str | None:
    price_id = PRICE_IDS.get(plan)
    if not price_id:
        return None

    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": SUCCESS_URL,
        "cancel_url": CANCEL_URL,
        "client_reference_id": telegram_user_id,
        "metadata": {"telegram_username": telegram_username},
    }

    if promo_code:
        params["discounts"] = [{"promotion_code": promo_code}]

    session = stripe.checkout.Session.create(**params)
    return session.url
