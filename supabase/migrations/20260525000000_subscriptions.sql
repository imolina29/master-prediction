-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_user_id TEXT NOT NULL,
    telegram_username TEXT,
    stripe_customer_id TEXT NOT NULL,
    stripe_subscription_id TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL CHECK (plan IN ('monthly', 'quarterly')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'cancelled', 'past_due', 'expired')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subscription_id UUID REFERENCES subscriptions(id),
    stripe_payment_intent_id TEXT UNIQUE,
    amount_usd NUMERIC(10, 2) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed', 'refunded')),
    paid_at TIMESTAMPTZ DEFAULT now()
);

-- Index for quick lookups by telegram user
CREATE INDEX IF NOT EXISTS idx_subscriptions_telegram_user
    ON subscriptions(telegram_user_id);

-- Index for active subscription checks
CREATE INDEX IF NOT EXISTS idx_subscriptions_status
    ON subscriptions(status);

-- RLS: disable anon access, only service role
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY "Service role full access on subscriptions"
    ON subscriptions FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on payments"
    ON payments FOR ALL
    USING (auth.role() = 'service_role');
