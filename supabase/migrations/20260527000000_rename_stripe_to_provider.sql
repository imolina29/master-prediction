-- Rename Stripe-specific columns to processor-agnostic names
-- (migration from Stripe to LemonSqueezy)

ALTER TABLE subscriptions RENAME COLUMN stripe_customer_id TO provider_customer_id;
ALTER TABLE subscriptions RENAME COLUMN stripe_subscription_id TO provider_subscription_id;

ALTER TABLE payments RENAME COLUMN stripe_payment_intent_id TO provider_payment_id;
ALTER TABLE payments RENAME COLUMN amount_usd TO amount;

-- Update the unique constraint name
ALTER INDEX subscriptions_stripe_subscription_id_key
    RENAME TO subscriptions_provider_subscription_id_key;

ALTER INDEX payments_stripe_payment_intent_id_key
    RENAME TO payments_provider_payment_id_key;

-- Drop NOT NULL on provider_customer_id (LS may not always have it)
ALTER TABLE subscriptions ALTER COLUMN provider_customer_id DROP NOT NULL;
