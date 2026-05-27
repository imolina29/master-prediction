# Monetization: Telegram Premium Subscription — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a paid subscription tier to the Telegram bot with Stripe payments, tiered content delivery (free/premium channels), a bilingual landing page, and an admin panel for subscription management.

**Architecture:** Stripe Checkout handles payment, a Supabase Edge Function receives webhooks and Telegram bot commands, the daily notification pipeline sends differentiated content to free and premium channels, and a new Streamlit dashboard view gives the admin full visibility into subscriptions and payments.

**Tech Stack:** Python 3.12+, Supabase (PostgreSQL + Edge Functions/Deno), Stripe Checkout + Webhooks, Telegram Bot API, HTML/CSS/JS (GitHub Pages), Streamlit

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `supabase/migrations/001_subscriptions.sql` | SQL migration: create `subscriptions` and `payments` tables |
| `supabase/functions/stripe-webhook/index.ts` | Supabase Edge Function: handle Stripe webhook events |
| `supabase/functions/telegram-bot/index.ts` | Supabase Edge Function: handle Telegram bot commands (/start, /status, /help) |
| `backend/subscriptions/models.py` | Python dataclasses for subscription/payment records |
| `backend/subscriptions/service.py` | CRUD operations for subscriptions and payments via Supabase |
| `backend/subscriptions/channel.py` | Telegram channel access management (invite/revoke) |
| `backend/subscriptions/stripe_checkout.py` | Generate Stripe Checkout session URLs |
| `tests/test_subscriptions.py` | Tests for subscription service |
| `tests/test_channel_access.py` | Tests for channel access management |
| `tests/test_free_picks.py` | Tests for free pick content generation |
| `landing/index.html` | Landing page — bilingual single page |
| `landing/styles.css` | Landing page styles |
| `landing/script.js` | Language toggle + interactions |
| `dashboard/views/9_suscripciones.py` | Admin view for subscription management |

### Modified files

| File | Change |
|------|--------|
| `backend/notifications/telegram.py` | Add `send_free_picks()` method to `TelegramNotifier` |
| `scripts/run_notifications.py` | Add free channel notification alongside premium |
| `scripts/run_alerts.py` | Send alerts only to premium channel |
| `dashboard/data_access.py` | Add `get_subscriptions()`, `get_payments()`, `get_subscription_kpis()` |
| `requirements.txt` | Add `stripe>=8.0.0` |
| `.github/workflows/etl.yml` | Add `STRIPE_SECRET_KEY`, `TELEGRAM_FREE_CHANNEL_ID`, `TELEGRAM_PREMIUM_CHANNEL_ID` env vars to notification steps |

---

## Task 1: Database Migration — Subscriptions & Payments Tables

**Files:**
- Create: `supabase/migrations/001_subscriptions.sql`

This task creates the SQL migration file. The actual migration is run manually in the Supabase SQL Editor (free tier doesn't support CLI migrations).

- [ ] **Step 1: Create migration directory**

```bash
mkdir -p supabase/migrations
```

- [ ] **Step 2: Write the migration SQL**

Create `supabase/migrations/001_subscriptions.sql`:

```sql
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
```

- [ ] **Step 3: Run the migration in Supabase SQL Editor**

Go to Supabase Dashboard → SQL Editor → paste the contents of `001_subscriptions.sql` → Run.

Verify tables exist:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('subscriptions', 'payments');
```

Expected: 2 rows returned.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/001_subscriptions.sql
git commit -m "feat: add subscriptions and payments database migration"
```

---

## Task 2: Subscription Service — Python CRUD Layer

**Files:**
- Create: `backend/subscriptions/__init__.py`
- Create: `backend/subscriptions/models.py`
- Create: `backend/subscriptions/service.py`
- Create: `tests/test_subscriptions.py`

### Step 1: Write the failing tests

Create `tests/test_subscriptions.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from backend.subscriptions.models import Payment, Subscription
from backend.subscriptions.service import SubscriptionService


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def service(mock_client):
    return SubscriptionService(mock_client)


def test_subscription_model():
    sub = Subscription(
        telegram_user_id="12345",
        telegram_username="testuser",
        stripe_customer_id="cus_test",
        stripe_subscription_id="sub_test",
        plan="monthly",
        status="active",
    )
    assert sub.telegram_user_id == "12345"
    assert sub.plan == "monthly"
    assert sub.status == "active"


def test_payment_model():
    pay = Payment(
        subscription_id="uuid-123",
        stripe_payment_intent_id="pi_test",
        amount_usd=19.99,
        status="succeeded",
    )
    assert pay.amount_usd == 19.99
    assert pay.status == "succeeded"


def test_create_subscription(service, mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "uuid-1", "telegram_user_id": "12345", "status": "active"}]
    )

    result = service.create_subscription(
        telegram_user_id="12345",
        telegram_username="testuser",
        stripe_customer_id="cus_test",
        stripe_subscription_id="sub_test",
        plan="monthly",
    )
    assert result["telegram_user_id"] == "12345"
    mock_client.table.assert_called_with("subscriptions")


def test_get_active_subscription(service, mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "uuid-1", "status": "active", "telegram_user_id": "12345"}]
    )

    result = service.get_active_subscription("12345")
    assert result is not None
    assert result["status"] == "active"


def test_get_active_subscription_none(service, mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    result = service.get_active_subscription("99999")
    assert result is None


def test_cancel_subscription(service, mock_client):
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "uuid-1", "status": "cancelled"}]
    )

    service.cancel_subscription("sub_test")
    mock_client.table.assert_called_with("subscriptions")


def test_record_payment(service, mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "pay-1"}]
    )

    result = service.record_payment(
        subscription_id="uuid-1",
        stripe_payment_intent_id="pi_test",
        amount_usd=19.99,
        status="succeeded",
    )
    assert result is not None
    mock_client.table.assert_called_with("payments")


def test_get_all_subscriptions(service, mock_client):
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {"id": "1", "status": "active", "plan": "monthly"},
            {"id": "2", "status": "cancelled", "plan": "quarterly"},
        ]
    )

    result = service.get_all_subscriptions()
    assert len(result) == 2


def test_get_all_payments(service, mock_client):
    mock_client.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
        data=[{"id": "p1", "amount_usd": 19.99}]
    )

    result = service.get_all_payments()
    assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/test_subscriptions.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.subscriptions'`

### Step 3: Write the models

Create `backend/subscriptions/__init__.py` (empty file).

Create `backend/subscriptions/models.py`:

```python
from dataclasses import dataclass, field


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
```

### Step 4: Write the service

Create `backend/subscriptions/service.py`:

```python
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
        stripe_customer_id: str,
        stripe_subscription_id: str,
        plan: str,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> dict:
        row = {
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
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

    def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> dict | None:
        resp = (
            self.client.table("subscriptions")
            .select("*")
            .eq("stripe_subscription_id", stripe_subscription_id)
            .execute()
        )
        return resp.data[0] if resp.data else None

    def update_subscription_status(self, stripe_subscription_id: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.client.table("subscriptions").update(
            {"status": status, "updated_at": now}
        ).eq("stripe_subscription_id", stripe_subscription_id).execute()
        logger.info("Updated subscription %s to status=%s", stripe_subscription_id, status)

    def update_subscription_period(
        self, stripe_subscription_id: str, period_start: str, period_end: str
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.client.table("subscriptions").update(
            {
                "current_period_start": period_start,
                "current_period_end": period_end,
                "updated_at": now,
            }
        ).eq("stripe_subscription_id", stripe_subscription_id).execute()

    def cancel_subscription(self, stripe_subscription_id: str) -> None:
        self.update_subscription_status(stripe_subscription_id, "cancelled")

    def record_payment(
        self,
        subscription_id: str,
        stripe_payment_intent_id: str,
        amount_usd: float,
        status: str,
    ) -> dict:
        row = {
            "subscription_id": subscription_id,
            "stripe_payment_intent_id": stripe_payment_intent_id,
            "amount_usd": amount_usd,
            "status": status,
        }
        resp = self.client.table("payments").insert(row).execute()
        logger.info("Recorded payment %s for subscription %s", stripe_payment_intent_id, subscription_id)
        return resp.data[0]

    def get_all_subscriptions(self) -> list[dict]:
        resp = (
            self.client.table("subscriptions")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []

    def get_all_payments(self) -> list[dict]:
        resp = (
            self.client.table("payments")
            .select("*")
            .order("paid_at", desc=True)
            .execute()
        )
        return resp.data or []
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/test_subscriptions.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 6: Lint**

```bash
python3 -m ruff check backend/subscriptions/ tests/test_subscriptions.py
python3 -m ruff format backend/subscriptions/ tests/test_subscriptions.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/subscriptions/ tests/test_subscriptions.py
git commit -m "feat: add subscription service with CRUD operations"
```

---

## Task 3: Channel Access Management

**Files:**
- Create: `backend/subscriptions/channel.py`
- Create: `tests/test_channel_access.py`

### Step 1: Write the failing tests

Create `tests/test_channel_access.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from backend.subscriptions.channel import ChannelManager


@pytest.fixture
def manager():
    return ChannelManager(
        bot_token="test_token",
        premium_channel_id="-1001234567890",
    )


@patch("backend.subscriptions.channel.httpx.post")
def test_create_invite_link(mock_post, manager):
    mock_post.return_value = MagicMock(
        json=lambda: {"ok": True, "result": {"invite_link": "https://t.me/+abc123"}}
    )

    link = manager.create_invite_link()
    assert link == "https://t.me/+abc123"
    mock_post.assert_called_once()
    call_json = mock_post.call_args[1]["json"]
    assert call_json["chat_id"] == "-1001234567890"
    assert call_json["member_limit"] == 1


@patch("backend.subscriptions.channel.httpx.post")
def test_send_invite_to_user(mock_post, manager):
    mock_post.return_value = MagicMock(
        json=lambda: {"ok": True, "result": {"invite_link": "https://t.me/+abc123"}}
    )

    manager.send_invite_to_user("12345")
    assert mock_post.call_count == 2  # createChatInviteLink + sendMessage


@patch("backend.subscriptions.channel.httpx.post")
def test_revoke_user_access(mock_post, manager):
    mock_post.return_value = MagicMock(json=lambda: {"ok": True})

    manager.revoke_user_access("12345")
    assert mock_post.call_count == 3  # banChatMember + unbanChatMember + sendMessage


@patch("backend.subscriptions.channel.httpx.post")
def test_send_admin_notification(mock_post, manager):
    manager.admin_chat_id = "-100admin"
    mock_post.return_value = MagicMock(json=lambda: {"ok": True})

    manager.send_admin_notification("Test message")
    mock_post.assert_called_once()
    call_json = mock_post.call_args[1]["json"]
    assert call_json["chat_id"] == "-100admin"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/test_channel_access.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.subscriptions.channel'`

### Step 3: Write the implementation

Create `backend/subscriptions/channel.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/test_channel_access.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Lint and commit**

```bash
python3 -m ruff check backend/subscriptions/channel.py tests/test_channel_access.py
python3 -m ruff format backend/subscriptions/channel.py tests/test_channel_access.py
git add backend/subscriptions/channel.py tests/test_channel_access.py
git commit -m "feat: add Telegram channel access management (invite/revoke)"
```

---

## Task 4: Stripe Checkout URL Generator

**Files:**
- Create: `backend/subscriptions/stripe_checkout.py`
- Modify: `requirements.txt`

### Step 1: Add stripe dependency

Add `stripe>=8.0.0` to `requirements.txt` in the API section:

```
# API
fastapi>=0.115.0
uvicorn>=0.32.0
stripe>=8.0.0
```

Then install:

```bash
pip install stripe>=8.0.0
```

### Step 2: Write the checkout URL generator

Create `backend/subscriptions/stripe_checkout.py`:

```python
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
```

- [ ] **Step 3: Lint and commit**

```bash
python3 -m ruff check backend/subscriptions/stripe_checkout.py
python3 -m ruff format backend/subscriptions/stripe_checkout.py
git add backend/subscriptions/stripe_checkout.py requirements.txt
git commit -m "feat: add Stripe Checkout URL generator"
```

---

## Task 5: Stripe Webhook — Supabase Edge Function

**Files:**
- Create: `supabase/functions/stripe-webhook/index.ts`

This Edge Function receives Stripe webhook events and updates Supabase + sends Telegram notifications.

### Step 1: Create the Edge Function

```bash
mkdir -p supabase/functions/stripe-webhook
```

Create `supabase/functions/stripe-webhook/index.ts`:

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const STRIPE_WEBHOOK_SECRET = Deno.env.get("STRIPE_WEBHOOK_SECRET") || "";
const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") || "";
const TELEGRAM_ADMIN_CHAT_ID = Deno.env.get("TELEGRAM_ADMIN_CHAT_ID") || "";
const TELEGRAM_PREMIUM_CHANNEL_ID = Deno.env.get("TELEGRAM_PREMIUM_CHANNEL_ID") || "";

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

async function telegramApi(method: string, body: Record<string, unknown>) {
  const resp = await fetch(
    `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/${method}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
  );
  return resp.json();
}

async function notifyAdmin(text: string) {
  if (!TELEGRAM_ADMIN_CHAT_ID) return;
  await telegramApi("sendMessage", {
    chat_id: TELEGRAM_ADMIN_CHAT_ID, text, parse_mode: "HTML",
  });
}

async function sendInviteToUser(telegramUserId: string) {
  const linkResult = await telegramApi("createChatInviteLink", {
    chat_id: TELEGRAM_PREMIUM_CHANNEL_ID, member_limit: 1,
  });

  if (!linkResult.ok) return;
  const inviteLink = linkResult.result.invite_link;

  await telegramApi("sendMessage", {
    chat_id: telegramUserId,
    text: `🎉 <b>Welcome to Master Prediction Premium!</b>\n\nJoin here:\n${inviteLink}\n\nYou'll receive all picks with odds, edge & confidence daily.`,
    parse_mode: "HTML",
  });
}

async function revokeUserAccess(telegramUserId: string) {
  await telegramApi("banChatMember", {
    chat_id: TELEGRAM_PREMIUM_CHANNEL_ID, user_id: Number(telegramUserId),
  });
  await telegramApi("unbanChatMember", {
    chat_id: TELEGRAM_PREMIUM_CHANNEL_ID, user_id: Number(telegramUserId),
  });
  await telegramApi("sendMessage", {
    chat_id: telegramUserId,
    text: "Your Master Prediction Premium subscription has ended.\n\nRenew anytime at https://masterprediction.com",
  });
}

async function verifyStripeSignature(body: string, signature: string): Promise<Record<string, unknown> | null> {
  // Stripe webhook signature verification using Web Crypto API
  const parts = signature.split(",");
  const timestampPart = parts.find((p) => p.startsWith("t="));
  const sigPart = parts.find((p) => p.startsWith("v1="));
  if (!timestampPart || !sigPart) return null;

  const timestamp = timestampPart.split("=")[1];
  const expectedSig = sigPart.split("=")[1];
  const signedPayload = `${timestamp}.${body}`;

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(STRIPE_WEBHOOK_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(signedPayload));
  const computed = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  if (computed !== expectedSig) return null;
  return JSON.parse(body);
}

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const body = await req.text();
  const signature = req.headers.get("stripe-signature") || "";

  const event = await verifyStripeSignature(body, signature);
  if (!event) {
    return new Response("Invalid signature", { status: 400 });
  }

  const eventType = event.type as string;
  const data = (event.data as Record<string, unknown>).object as Record<string, unknown>;

  try {
    if (eventType === "checkout.session.completed") {
      const telegramUserId = data.client_reference_id as string;
      const metadata = data.metadata as Record<string, string>;
      const telegramUsername = metadata?.telegram_username || "";
      const stripeCustomerId = data.customer as string;
      const stripeSubscriptionId = data.subscription as string;

      // Determine plan from the price
      const plan = "monthly"; // Default; can be refined by checking line_items

      await supabase.from("subscriptions").insert({
        telegram_user_id: telegramUserId,
        telegram_username: telegramUsername,
        stripe_customer_id: stripeCustomerId,
        stripe_subscription_id: stripeSubscriptionId,
        plan,
        status: "active",
      });

      await sendInviteToUser(telegramUserId);
      await notifyAdmin(
        `🆕 <b>New subscriber:</b> @${telegramUsername || telegramUserId} — Premium ${plan} ($${plan === "monthly" ? "19.99" : "49.99"})`
      );
    }

    if (eventType === "invoice.paid") {
      const stripeSubscriptionId = data.subscription as string;
      const amountPaid = (data.amount_paid as number) / 100;
      const paymentIntentId = data.payment_intent as string;
      const periodStart = new Date((data.period_start as number) * 1000).toISOString();
      const periodEnd = new Date((data.period_end as number) * 1000).toISOString();

      const { data: sub } = await supabase
        .from("subscriptions")
        .select("id")
        .eq("stripe_subscription_id", stripeSubscriptionId)
        .single();

      if (sub) {
        await supabase.from("payments").insert({
          subscription_id: sub.id,
          stripe_payment_intent_id: paymentIntentId,
          amount_usd: amountPaid,
          status: "succeeded",
        });

        await supabase
          .from("subscriptions")
          .update({
            current_period_start: periodStart,
            current_period_end: periodEnd,
            updated_at: new Date().toISOString(),
          })
          .eq("stripe_subscription_id", stripeSubscriptionId);
      }
    }

    if (eventType === "invoice.payment_failed") {
      const stripeSubscriptionId = data.subscription as string;

      await supabase
        .from("subscriptions")
        .update({ status: "past_due", updated_at: new Date().toISOString() })
        .eq("stripe_subscription_id", stripeSubscriptionId);

      const { data: sub } = await supabase
        .from("subscriptions")
        .select("telegram_username, telegram_user_id")
        .eq("stripe_subscription_id", stripeSubscriptionId)
        .single();

      if (sub) {
        await notifyAdmin(
          `⚠️ <b>Payment failed:</b> @${sub.telegram_username || sub.telegram_user_id}`
        );
      }
    }

    if (eventType === "customer.subscription.deleted") {
      const stripeSubscriptionId = data.id as string;

      const { data: sub } = await supabase
        .from("subscriptions")
        .select("telegram_user_id, telegram_username")
        .eq("stripe_subscription_id", stripeSubscriptionId)
        .single();

      await supabase
        .from("subscriptions")
        .update({ status: "cancelled", updated_at: new Date().toISOString() })
        .eq("stripe_subscription_id", stripeSubscriptionId);

      if (sub) {
        await revokeUserAccess(sub.telegram_user_id);
        await notifyAdmin(
          `❌ <b>Subscription cancelled:</b> @${sub.telegram_username || sub.telegram_user_id}`
        );
      }
    }
  } catch (err) {
    console.error("Webhook handler error:", err);
    return new Response("Internal error", { status: 500 });
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add supabase/functions/stripe-webhook/
git commit -m "feat: add Stripe webhook Edge Function"
```

**Deployment note:** Deploy to Supabase via the Dashboard (Settings → Edge Functions) or using the Supabase CLI: `supabase functions deploy stripe-webhook`. Configure the required environment variables (secrets) in the Supabase Dashboard under Edge Functions settings.

---

## Task 6: Telegram Bot Command Handler — Edge Function

**Files:**
- Create: `supabase/functions/telegram-bot/index.ts`

### Step 1: Create the Edge Function

```bash
mkdir -p supabase/functions/telegram-bot
```

Create `supabase/functions/telegram-bot/index.ts`:

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") || "";
const STRIPE_PRICE_MONTHLY = Deno.env.get("STRIPE_PRICE_MONTHLY") || "";
const STRIPE_PRICE_QUARTERLY = Deno.env.get("STRIPE_PRICE_QUARTERLY") || "";
const STRIPE_SECRET_KEY = Deno.env.get("STRIPE_SECRET_KEY") || "";
const LANDING_URL = Deno.env.get("LANDING_URL") || "https://masterprediction.com";
const TELEGRAM_FREE_CHANNEL_URL = Deno.env.get("TELEGRAM_FREE_CHANNEL_URL") || "";

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

async function telegramReply(chatId: number | string, text: string, replyMarkup?: unknown) {
  const body: Record<string, unknown> = {
    chat_id: chatId, text, parse_mode: "HTML",
  };
  if (replyMarkup) body.reply_markup = replyMarkup;

  await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function createCheckoutUrl(telegramUserId: string, username: string, plan: string): Promise<string | null> {
  const priceId = plan === "quarterly" ? STRIPE_PRICE_QUARTERLY : STRIPE_PRICE_MONTHLY;
  if (!priceId || !STRIPE_SECRET_KEY) return null;

  const params = new URLSearchParams();
  params.append("mode", "subscription");
  params.append("line_items[0][price]", priceId);
  params.append("line_items[0][quantity]", "1");
  params.append("success_url", `${LANDING_URL}/success.html`);
  params.append("cancel_url", LANDING_URL);
  params.append("client_reference_id", telegramUserId);
  params.append("metadata[telegram_username]", username);

  const resp = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${STRIPE_SECRET_KEY}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params.toString(),
  });

  const session = await resp.json();
  return session.url || null;
}

async function handleStart(chatId: number, userId: number, username: string, args: string) {
  if (args === "subscribe") {
    const monthlyUrl = await createCheckoutUrl(String(userId), username, "monthly");
    const quarterlyUrl = await createCheckoutUrl(String(userId), username, "quarterly");

    const buttons: unknown[][] = [];
    if (monthlyUrl) {
      buttons.push([{ text: "📅 Monthly — $19.99/mo", url: monthlyUrl }]);
    }
    if (quarterlyUrl) {
      buttons.push([{ text: "📅 Quarterly — $49.99/3mo (save 17%)", url: quarterlyUrl }]);
    }

    await telegramReply(
      chatId,
      "⚽ <b>Master Prediction Premium</b>\n\n" +
      "Get all picks with odds, edge & confidence:\n" +
      "• All 5 top leagues + World Cup\n" +
      "• 1x2, Over/Under, BTTS markets\n" +
      "• Real-time high-confidence alerts\n" +
      "• Daily results & profit tracking\n\n" +
      "Choose your plan:",
      { inline_keyboard: buttons },
    );
    return;
  }

  await telegramReply(
    chatId,
    "⚽ <b>Welcome to Master Prediction!</b>\n\n" +
    "AI-powered football predictions with verified track record.\n\n" +
    `📢 Free picks: ${TELEGRAM_FREE_CHANNEL_URL || "coming soon"}\n` +
    `🔒 Premium: /start subscribe or visit ${LANDING_URL}\n\n` +
    "Commands:\n" +
    "/status — Check your subscription\n" +
    "/help — More info",
  );
}

async function handleStatus(chatId: number, userId: number) {
  const { data: sub } = await supabase
    .from("subscriptions")
    .select("*")
    .eq("telegram_user_id", String(userId))
    .eq("status", "active")
    .maybeSingle();

  if (sub) {
    const endDate = sub.current_period_end
      ? new Date(sub.current_period_end).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
      : "—";

    await telegramReply(
      chatId,
      "✅ <b>Active Subscription</b>\n\n" +
      `Plan: <b>${sub.plan}</b>\n` +
      `Status: <b>${sub.status}</b>\n` +
      `Next payment: <b>${endDate}</b>`,
    );
  } else {
    await telegramReply(
      chatId,
      "You don't have an active subscription.\n\n" +
      "Use /start subscribe to get Premium access!",
    );
  }
}

async function handleHelp(chatId: number) {
  await telegramReply(
    chatId,
    "⚽ <b>Master Prediction — Help</b>\n\n" +
    "/start — Welcome & free channel link\n" +
    "/start subscribe — Subscribe to Premium\n" +
    "/status — Check your subscription status\n" +
    "/help — This message\n\n" +
    `🌐 Website: ${LANDING_URL}`,
  );
}

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("OK", { status: 200 });
  }

  const update = await req.json();
  const message = update.message;

  if (!message || !message.text) {
    return new Response("OK", { status: 200 });
  }

  const chatId = message.chat.id;
  const userId = message.from.id;
  const username = message.from.username || "";
  const text = message.text.trim();

  if (text.startsWith("/start")) {
    const args = text.replace("/start", "").trim();
    await handleStart(chatId, userId, username, args);
  } else if (text === "/status") {
    await handleStatus(chatId, userId);
  } else if (text === "/help") {
    await handleHelp(chatId);
  }

  return new Response("OK", { status: 200 });
});
```

- [ ] **Step 2: Commit**

```bash
git add supabase/functions/telegram-bot/
git commit -m "feat: add Telegram bot command handler Edge Function"
```

**Deployment note:** After deploying via Supabase CLI or Dashboard, register the webhook URL with Telegram:
```bash
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=<SUPABASE_FUNCTION_URL>"
```

---

## Task 7: Free Picks Content Generation

**Files:**
- Modify: `backend/notifications/telegram.py`
- Create: `tests/test_free_picks.py`

### Step 1: Write the failing tests

Create `tests/test_free_picks.py`:

```python
from backend.notifications.telegram import TelegramNotifier, build_free_picks


def test_build_free_picks_filters_1x2_only():
    picks = [
        {"market": "1x2_home", "home_team": "Arsenal", "away_team": "Chelsea",
         "division": "E0", "stake": 3, "edge": 0.12, "odd": 1.85},
        {"market": "over25", "home_team": "Arsenal", "away_team": "Chelsea",
         "division": "E0", "stake": 2, "edge": 0.10, "odd": 1.90},
        {"market": "1x2_away", "home_team": "Liverpool", "away_team": "Man City",
         "division": "E0", "stake": 2, "edge": 0.09, "odd": 2.50},
    ]
    result = build_free_picks(picks)
    assert len(result) == 2
    assert all(p["market"].startswith("1x2") for p in result)


def test_build_free_picks_filters_by_division():
    picks = [
        {"market": "1x2_home", "home_team": "Arsenal", "away_team": "Chelsea",
         "division": "E0", "stake": 3, "edge": 0.12, "odd": 1.85},
        {"market": "1x2_home", "home_team": "Barcelona", "away_team": "Madrid",
         "division": "SP1", "stake": 3, "edge": 0.15, "odd": 1.70},
    ]
    result = build_free_picks(picks)
    assert len(result) == 1
    assert result[0]["division"] == "E0"


def test_build_free_picks_includes_world_cup():
    picks = [
        {"market": "1x2_home", "home_team": "Brazil", "away_team": "Germany",
         "division": "WC", "stake": 3, "edge": 0.12, "odd": 2.10},
    ]
    result = build_free_picks(picks)
    assert len(result) == 1


def test_build_free_picks_max_two():
    picks = [
        {"market": "1x2_home", "home_team": f"Team{i}", "away_team": f"Opp{i}",
         "division": "E0", "stake": 3 - (i % 3), "edge": 0.10 + i * 0.01, "odd": 1.80}
        for i in range(5)
    ]
    result = build_free_picks(picks)
    assert len(result) <= 2


def test_build_free_picks_sorted_by_stake_then_edge():
    picks = [
        {"market": "1x2_home", "home_team": "A", "away_team": "B",
         "division": "E0", "stake": 1, "edge": 0.20, "odd": 1.80},
        {"market": "1x2_home", "home_team": "C", "away_team": "D",
         "division": "E0", "stake": 3, "edge": 0.08, "odd": 1.90},
    ]
    result = build_free_picks(picks)
    assert result[0]["home_team"] == "C"


def test_build_free_picks_empty():
    result = build_free_picks([])
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=. python3 -m pytest tests/test_free_picks.py -v
```

Expected: FAIL — `ImportError: cannot import name 'build_free_picks'`

### Step 3: Implement `build_free_picks` and `send_free_picks`

Add to `backend/notifications/telegram.py` at the bottom, before the class ends — actually, `build_free_picks` is a module-level function. Add it after the `TelegramNotifier` class:

```python
FREE_DIVISIONS = {"E0", "WC"}


def build_free_picks(picks: list[dict]) -> list[dict]:
    filtered = [
        p for p in picks
        if p.get("market", "").startswith("1x2") and p.get("division") in FREE_DIVISIONS
    ]
    sorted_picks = sorted(filtered, key=lambda p: (-p.get("stake", 0), -p.get("edge", 0)))
    return sorted_picks[:2]
```

Also add `send_free_picks` method to the `TelegramNotifier` class:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=. python3 -m pytest tests/test_free_picks.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run all tests to check for regressions**

```bash
PYTHONPATH=. python3 -m pytest tests/ -x -q
```

Expected: all tests pass.

- [ ] **Step 6: Lint and commit**

```bash
python3 -m ruff check backend/notifications/telegram.py tests/test_free_picks.py
python3 -m ruff format backend/notifications/telegram.py tests/test_free_picks.py
git add backend/notifications/telegram.py tests/test_free_picks.py
git commit -m "feat: add free picks content generation (1x2 only, EPL + WC, top 2)"
```

---

## Task 8: Notification Pipeline — Free + Premium Split

**Files:**
- Modify: `scripts/run_notifications.py`
- Modify: `scripts/run_alerts.py`
- Modify: `.github/workflows/etl.yml`

### Step 1: Update `run_notifications.py`

Replace the contents of `scripts/run_notifications.py` with:

```python
"""Send daily Telegram notifications to free and premium channels."""

import logging
import os
from datetime import date

from backend.betting.tracker import calculate_performance
from backend.db.client import get_supabase
from backend.notifications.telegram import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    client = get_supabase()

    free_channel_id = os.environ.get("TELEGRAM_FREE_CHANNEL_ID", "")
    premium_channel_id = os.environ.get("TELEGRAM_PREMIUM_CHANNEL_ID", "")
    landing_url = os.environ.get("LANDING_URL", "https://masterprediction.com")

    premium_notifier = TelegramNotifier()
    logger.info("Premium notifier: %d chat(s)", len(premium_notifier.chat_ids))

    active_resp = (
        client.table("value_bets")
        .select("*")
        .is_("result", "null")
        .gte("stake", 1)
        .order("stake", desc=True)
        .execute()
    )
    picks = active_resp.data or []

    resolved_resp = client.table("value_bets").select("*").not_.is_("result", "null").execute()
    resolved = resolved_resp.data or []
    performance = calculate_performance(resolved) if resolved else None

    # Premium channel: full picks (existing behavior)
    if picks:
        if premium_channel_id:
            results = premium_notifier.send_daily_picks(picks, performance)
            ok_count = sum(1 for r in results if r.get("ok"))
            logger.info("Premium picks sent to %d/%d chats", ok_count, len(results))
        else:
            results = premium_notifier.send_daily_picks(picks, performance)
            ok_count = sum(1 for r in results if r.get("ok"))
            logger.info("Picks sent to %d/%d chats (legacy mode)", ok_count, len(results))

    # Free channel: filtered picks
    if picks and free_channel_id:
        free_results = premium_notifier.send_free_picks(
            picks, chat_id=free_channel_id, landing_url=landing_url
        )
        ok_count = sum(1 for r in free_results if r.get("ok"))
        logger.info("Free picks sent to free channel: %d ok", ok_count)

    # Resolved summary: premium only
    today_resolved = [
        p for p in resolved if p.get("resolved_at", "").startswith(date.today().isoformat())
    ]
    if today_resolved:
        results = premium_notifier.send_resolved_summary(today_resolved)
        ok_count = sum(1 for r in results if r.get("ok"))
        logger.info("Resolved summary sent to %d/%d chats", ok_count, len(results))


if __name__ == "__main__":
    main()
```

### Step 2: Update `scripts/run_alerts.py`

No change needed — alerts already go to `TelegramNotifier.send_to_all()` which sends to authorized chats (premium). The premium channel ID should be added to `TELEGRAM_AUTHORIZED_CHATS` in production.

### Step 3: Add new env vars to ETL workflow

In `.github/workflows/etl.yml`, add the new environment variables to the notification steps. Find the "Send Telegram notifications" step and add:

```yaml
          TELEGRAM_FREE_CHANNEL_ID: ${{ secrets.TELEGRAM_FREE_CHANNEL_ID }}
          TELEGRAM_PREMIUM_CHANNEL_ID: ${{ secrets.TELEGRAM_PREMIUM_CHANNEL_ID }}
          LANDING_URL: ${{ secrets.LANDING_URL }}
```

Do the same for the "Check and send smart alerts" step.

- [ ] **Step 4: Run all tests**

```bash
PYTHONPATH=. python3 -m pytest tests/ -x -q
```

Expected: all tests pass (no functional changes to tested code).

- [ ] **Step 5: Lint and commit**

```bash
python3 -m ruff check scripts/run_notifications.py scripts/run_alerts.py
python3 -m ruff format scripts/run_notifications.py scripts/run_alerts.py
git add scripts/run_notifications.py .github/workflows/etl.yml
git commit -m "feat: split notifications into free and premium channels"
```

---

## Task 9: Landing Page

**Files:**
- Create: `landing/index.html`
- Create: `landing/styles.css`
- Create: `landing/script.js`
- Create: `landing/success.html`

### Step 1: Create the landing page

```bash
mkdir -p landing
```

Create `landing/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Prediction — AI Football Predictions</title>
    <link rel="stylesheet" href="styles.css">
    <meta name="description" content="AI-powered football predictions with verified track record. Get daily value bets with edge analysis.">
</head>
<body>
    <!-- Language Toggle -->
    <div class="lang-toggle">
        <button id="btn-en" class="active" onclick="setLang('en')">EN</button>
        <button id="btn-es" onclick="setLang('es')">ES</button>
    </div>

    <!-- Hero -->
    <section class="hero">
        <div class="container">
            <h1 data-i18n="hero.title">AI-Powered Football Predictions</h1>
            <p class="subtitle" data-i18n="hero.subtitle">Machine learning models trained on 100,000+ matches. Daily value bets with verified edge.</p>
            <div class="stats-row">
                <div class="stat">
                    <span class="stat-value">55%+</span>
                    <span class="stat-label" data-i18n="hero.accuracy">Accuracy</span>
                </div>
                <div class="stat">
                    <span class="stat-value">5</span>
                    <span class="stat-label" data-i18n="hero.leagues">Top Leagues</span>
                </div>
                <div class="stat">
                    <span class="stat-value">6</span>
                    <span class="stat-label" data-i18n="hero.models">ML Models</span>
                </div>
            </div>
            <a href="#pricing" class="cta-btn" data-i18n="hero.cta">Get Premium Picks</a>
        </div>
    </section>

    <!-- How It Works -->
    <section class="how-it-works">
        <div class="container">
            <h2 data-i18n="how.title">How It Works</h2>
            <div class="steps">
                <div class="step">
                    <div class="step-icon">🤖</div>
                    <h3 data-i18n="how.step1.title">AI Analyzes</h3>
                    <p data-i18n="how.step1.desc">Our models process 100K+ historical matches, form stats, odds, and xG data</p>
                </div>
                <div class="step">
                    <div class="step-icon">📊</div>
                    <h3 data-i18n="how.step2.title">Finds Value</h3>
                    <p data-i18n="how.step2.desc">Compares model probabilities against bookmaker odds to find real edge</p>
                </div>
                <div class="step">
                    <div class="step-icon">📱</div>
                    <h3 data-i18n="how.step3.title">You Receive</h3>
                    <p data-i18n="how.step3.desc">Daily picks delivered to your Telegram with odds, edge, and confidence</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Free vs Premium -->
    <section class="comparison">
        <div class="container">
            <h2 data-i18n="compare.title">Free vs Premium</h2>
            <div class="compare-table">
                <div class="compare-row header">
                    <div class="compare-feature" data-i18n="compare.feature">Feature</div>
                    <div class="compare-free" data-i18n="compare.free">Free</div>
                    <div class="compare-premium" data-i18n="compare.premium">Premium</div>
                </div>
                <div class="compare-row">
                    <div class="compare-feature" data-i18n="compare.picks">Daily Picks</div>
                    <div class="compare-free">1-2</div>
                    <div class="compare-premium" data-i18n="compare.all">All</div>
                </div>
                <div class="compare-row">
                    <div class="compare-feature" data-i18n="compare.markets">Markets</div>
                    <div class="compare-free">1x2</div>
                    <div class="compare-premium">1x2 + O/U + BTTS</div>
                </div>
                <div class="compare-row">
                    <div class="compare-feature" data-i18n="compare.leagues_label">Leagues</div>
                    <div class="compare-free">EPL</div>
                    <div class="compare-premium" data-i18n="compare.all_leagues">All 5 + World Cup</div>
                </div>
                <div class="compare-row">
                    <div class="compare-feature" data-i18n="compare.odds">Odds & Edge</div>
                    <div class="compare-free">❌</div>
                    <div class="compare-premium">✅</div>
                </div>
                <div class="compare-row">
                    <div class="compare-feature" data-i18n="compare.alerts">Real-time Alerts</div>
                    <div class="compare-free">❌</div>
                    <div class="compare-premium">✅</div>
                </div>
                <div class="compare-row">
                    <div class="compare-feature" data-i18n="compare.results">Daily Results</div>
                    <div class="compare-free">❌</div>
                    <div class="compare-premium">✅</div>
                </div>
            </div>
        </div>
    </section>

    <!-- World Cup Banner -->
    <section class="worldcup">
        <div class="container">
            <h2>🏆 FIFA World Cup 2026</h2>
            <p data-i18n="wc.desc">Get AI predictions for every World Cup match. Our models are trained on international football data.</p>
            <p class="promo" data-i18n="wc.promo">First month just $9.99 — World Cup special!</p>
        </div>
    </section>

    <!-- Pricing -->
    <section class="pricing" id="pricing">
        <div class="container">
            <h2 data-i18n="pricing.title">Choose Your Plan</h2>
            <div class="plans">
                <div class="plan">
                    <h3 data-i18n="pricing.monthly">Monthly</h3>
                    <div class="price">$19.99<span>/mo</span></div>
                    <ul>
                        <li data-i18n="pricing.feature1">All picks, all markets</li>
                        <li data-i18n="pricing.feature2">5 leagues + World Cup</li>
                        <li data-i18n="pricing.feature3">Real-time alerts</li>
                        <li data-i18n="pricing.feature4">Cancel anytime</li>
                    </ul>
                    <a href="TELEGRAM_BOT_SUBSCRIBE_LINK" class="plan-btn" data-i18n="pricing.subscribe">Subscribe</a>
                </div>
                <div class="plan featured">
                    <div class="badge" data-i18n="pricing.save">Save 17%</div>
                    <h3 data-i18n="pricing.quarterly">Quarterly</h3>
                    <div class="price">$49.99<span>/3mo</span></div>
                    <ul>
                        <li data-i18n="pricing.feature1">All picks, all markets</li>
                        <li data-i18n="pricing.feature2">5 leagues + World Cup</li>
                        <li data-i18n="pricing.feature3">Real-time alerts</li>
                        <li data-i18n="pricing.feature4_q">Best value</li>
                    </ul>
                    <a href="TELEGRAM_BOT_SUBSCRIBE_LINK" class="plan-btn" data-i18n="pricing.subscribe">Subscribe</a>
                </div>
                <div class="plan promo">
                    <div class="badge">🏆 World Cup</div>
                    <h3 data-i18n="pricing.promo_title">Promo</h3>
                    <div class="price">$9.99<span data-i18n="pricing.first_month"> 1st month</span></div>
                    <p class="promo-note" data-i18n="pricing.then">Then $19.99/mo</p>
                    <ul>
                        <li data-i18n="pricing.feature1">All picks, all markets</li>
                        <li data-i18n="pricing.feature_wc">World Cup coverage</li>
                        <li data-i18n="pricing.feature3">Real-time alerts</li>
                    </ul>
                    <a href="TELEGRAM_BOT_SUBSCRIBE_LINK" class="plan-btn" data-i18n="pricing.subscribe">Subscribe</a>
                </div>
            </div>
        </div>
    </section>

    <!-- FAQ -->
    <section class="faq">
        <div class="container">
            <h2 data-i18n="faq.title">FAQ</h2>
            <div class="faq-item">
                <h4 data-i18n="faq.q1">How do I receive picks?</h4>
                <p data-i18n="faq.a1">Via Telegram. After subscribing, our bot sends you an invite link to the premium channel where picks are posted daily.</p>
            </div>
            <div class="faq-item">
                <h4 data-i18n="faq.q2">Can I cancel anytime?</h4>
                <p data-i18n="faq.a2">Yes. Cancel through Stripe and you'll keep access until the end of your billing period.</p>
            </div>
            <div class="faq-item">
                <h4 data-i18n="faq.q3">What leagues do you cover?</h4>
                <p data-i18n="faq.a3">Premier League, La Liga, Serie A, Bundesliga, Ligue 1, and FIFA World Cup 2026.</p>
            </div>
            <div class="faq-item">
                <h4 data-i18n="faq.q4">How are predictions generated?</h4>
                <p data-i18n="faq.a4">We use 6 XGBoost machine learning models trained on 100,000+ historical matches with 46+ features including form, xG, Elo ratings, and head-to-head stats.</p>
            </div>
            <div class="faq-item">
                <h4 data-i18n="faq.q5">Do you guarantee profits?</h4>
                <p data-i18n="faq.a5">No. Master Prediction is an informational service. Sports betting involves risk. We provide data-driven analysis, not financial advice.</p>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer>
        <div class="container">
            <p>📢 <a href="TELEGRAM_FREE_CHANNEL_LINK" data-i18n="footer.free">Join Free Channel</a></p>
            <p class="disclaimer" data-i18n="footer.disclaimer">Master Prediction is an informational service. We do not guarantee profits. Sports betting involves risk. Gamble responsibly. 18+.</p>
            <p class="copyright">© 2026 Master Prediction</p>
        </div>
    </footer>

    <script src="script.js"></script>
</body>
</html>
```

### Step 2: Create styles

Create `landing/styles.css`:

```css
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0a0a0a;
    color: #e0e0e0;
    line-height: 1.6;
}

.container { max-width: 960px; margin: 0 auto; padding: 0 20px; }

/* Language Toggle */
.lang-toggle {
    position: fixed; top: 16px; right: 16px; z-index: 100;
    display: flex; gap: 4px;
}
.lang-toggle button {
    background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
    color: #aaa; padding: 6px 12px; cursor: pointer; border-radius: 4px;
    font-size: 13px; transition: all 0.2s;
}
.lang-toggle button.active {
    background: #1B5E20; color: #fff; border-color: #4CAF50;
}

/* Hero */
.hero {
    text-align: center; padding: 100px 20px 60px;
    background: linear-gradient(180deg, #0d2818 0%, #0a0a0a 100%);
}
.hero h1 { font-size: 2.5rem; color: #4CAF50; margin-bottom: 16px; }
.subtitle { font-size: 1.15rem; color: #999; max-width: 600px; margin: 0 auto 32px; }
.stats-row { display: flex; justify-content: center; gap: 40px; margin-bottom: 32px; }
.stat-value { display: block; font-size: 2rem; font-weight: 700; color: #FFD700; }
.stat-label { font-size: 0.85rem; color: #888; }
.cta-btn {
    display: inline-block; background: #2E7D32; color: #fff; padding: 14px 32px;
    border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.05rem;
    transition: background 0.2s;
}
.cta-btn:hover { background: #388E3C; }

/* Sections */
section { padding: 60px 0; }
section:nth-child(even) { background: rgba(27, 94, 32, 0.05); }
h2 { text-align: center; font-size: 1.8rem; color: #4CAF50; margin-bottom: 32px; }

/* How It Works */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.step { text-align: center; padding: 24px; }
.step-icon { font-size: 2.5rem; margin-bottom: 12px; }
.step h3 { color: #66BB6A; margin-bottom: 8px; }
.step p { color: #999; font-size: 0.9rem; }

/* Comparison Table */
.compare-table { max-width: 600px; margin: 0 auto; }
.compare-row {
    display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 8px;
    padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.06);
}
.compare-row.header { font-weight: 600; color: #4CAF50; border-bottom: 2px solid rgba(76,175,80,0.3); }
.compare-free { text-align: center; color: #888; }
.compare-premium { text-align: center; color: #FFD700; font-weight: 500; }

/* World Cup */
.worldcup {
    text-align: center; padding: 48px 20px;
    background: linear-gradient(135deg, rgba(27, 94, 32, 0.2), rgba(255, 215, 0, 0.05));
    border: 1px solid rgba(255, 215, 0, 0.15);
    margin: 0 20px; border-radius: 16px;
}
.worldcup h2 { color: #FFD700; }
.promo { color: #FFD700; font-weight: 600; font-size: 1.1rem; margin-top: 12px; }

/* Pricing */
.plans { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.plan {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 32px 24px; text-align: center; position: relative;
}
.plan.featured { border-color: #4CAF50; background: rgba(46, 125, 50, 0.08); }
.plan.promo { border-color: #FFD700; }
.badge {
    position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
    background: #4CAF50; color: #fff; padding: 4px 16px; border-radius: 20px;
    font-size: 0.8rem; font-weight: 600;
}
.plan.promo .badge { background: #FFD700; color: #000; }
.plan h3 { color: #66BB6A; margin-bottom: 12px; }
.price { font-size: 2.2rem; font-weight: 700; color: #fff; margin-bottom: 8px; }
.price span { font-size: 0.9rem; color: #888; }
.promo-note { color: #888; font-size: 0.85rem; margin-bottom: 16px; }
.plan ul { list-style: none; margin: 20px 0; text-align: left; }
.plan li { padding: 6px 0; color: #bbb; font-size: 0.9rem; }
.plan li::before { content: "✓ "; color: #4CAF50; font-weight: 600; }
.plan-btn {
    display: block; background: #2E7D32; color: #fff; padding: 12px;
    border-radius: 8px; text-decoration: none; font-weight: 600;
    transition: background 0.2s;
}
.plan-btn:hover { background: #388E3C; }

/* FAQ */
.faq-item { max-width: 700px; margin: 0 auto 20px; }
.faq-item h4 { color: #66BB6A; margin-bottom: 6px; }
.faq-item p { color: #999; font-size: 0.9rem; }

/* Footer */
footer { text-align: center; padding: 40px 20px; border-top: 1px solid rgba(255,255,255,0.06); }
footer a { color: #4CAF50; text-decoration: none; }
.disclaimer { color: #666; font-size: 0.75rem; margin-top: 16px; max-width: 600px; margin-left: auto; margin-right: auto; }
.copyright { color: #444; font-size: 0.75rem; margin-top: 8px; }

/* Responsive */
@media (max-width: 768px) {
    .hero h1 { font-size: 1.8rem; }
    .stats-row { gap: 20px; }
    .steps { grid-template-columns: 1fr; }
    .plans { grid-template-columns: 1fr; }
    .compare-row { font-size: 0.9rem; }
}
```

### Step 3: Create the i18n script

Create `landing/script.js`:

```javascript
const translations = {
  en: {
    "hero.title": "AI-Powered Football Predictions",
    "hero.subtitle": "Machine learning models trained on 100,000+ matches. Daily value bets with verified edge.",
    "hero.accuracy": "Accuracy",
    "hero.leagues": "Top Leagues",
    "hero.models": "ML Models",
    "hero.cta": "Get Premium Picks",
    "how.title": "How It Works",
    "how.step1.title": "AI Analyzes",
    "how.step1.desc": "Our models process 100K+ historical matches, form stats, odds, and xG data",
    "how.step2.title": "Finds Value",
    "how.step2.desc": "Compares model probabilities against bookmaker odds to find real edge",
    "how.step3.title": "You Receive",
    "how.step3.desc": "Daily picks delivered to your Telegram with odds, edge, and confidence",
    "compare.title": "Free vs Premium",
    "compare.feature": "Feature",
    "compare.free": "Free",
    "compare.premium": "Premium",
    "compare.picks": "Daily Picks",
    "compare.all": "All",
    "compare.markets": "Markets",
    "compare.leagues_label": "Leagues",
    "compare.all_leagues": "All 5 + World Cup",
    "compare.odds": "Odds & Edge",
    "compare.alerts": "Real-time Alerts",
    "compare.results": "Daily Results",
    "wc.desc": "Get AI predictions for every World Cup match. Our models are trained on international football data.",
    "wc.promo": "First month just $9.99 — World Cup special!",
    "pricing.title": "Choose Your Plan",
    "pricing.monthly": "Monthly",
    "pricing.quarterly": "Quarterly",
    "pricing.promo_title": "Promo",
    "pricing.save": "Save 17%",
    "pricing.first_month": " 1st month",
    "pricing.then": "Then $19.99/mo",
    "pricing.feature1": "All picks, all markets",
    "pricing.feature2": "5 leagues + World Cup",
    "pricing.feature3": "Real-time alerts",
    "pricing.feature4": "Cancel anytime",
    "pricing.feature4_q": "Best value",
    "pricing.feature_wc": "World Cup coverage",
    "pricing.subscribe": "Subscribe",
    "faq.title": "FAQ",
    "faq.q1": "How do I receive picks?",
    "faq.a1": "Via Telegram. After subscribing, our bot sends you an invite link to the premium channel where picks are posted daily.",
    "faq.q2": "Can I cancel anytime?",
    "faq.a2": "Yes. Cancel through Stripe and you'll keep access until the end of your billing period.",
    "faq.q3": "What leagues do you cover?",
    "faq.a3": "Premier League, La Liga, Serie A, Bundesliga, Ligue 1, and FIFA World Cup 2026.",
    "faq.q4": "How are predictions generated?",
    "faq.a4": "We use 6 XGBoost machine learning models trained on 100,000+ historical matches with 46+ features including form, xG, Elo ratings, and head-to-head stats.",
    "faq.q5": "Do you guarantee profits?",
    "faq.a5": "No. Master Prediction is an informational service. Sports betting involves risk. We provide data-driven analysis, not financial advice.",
    "footer.free": "Join Free Channel",
    "footer.disclaimer": "Master Prediction is an informational service. We do not guarantee profits. Sports betting involves risk. Gamble responsibly. 18+.",
  },
  es: {
    "hero.title": "Predicciones de Fútbol con IA",
    "hero.subtitle": "Modelos de machine learning entrenados con 100,000+ partidos. Apuestas de valor diarias con edge verificado.",
    "hero.accuracy": "Precisión",
    "hero.leagues": "Ligas Top",
    "hero.models": "Modelos ML",
    "hero.cta": "Obtener Picks Premium",
    "how.title": "Cómo Funciona",
    "how.step1.title": "La IA Analiza",
    "how.step1.desc": "Nuestros modelos procesan 100K+ partidos históricos, estadísticas, cuotas y datos xG",
    "how.step2.title": "Encuentra Valor",
    "how.step2.desc": "Compara probabilidades del modelo contra cuotas de casas de apuestas para encontrar edge real",
    "how.step3.title": "Tú Recibes",
    "how.step3.desc": "Picks diarios en tu Telegram con cuotas, edge y confianza",
    "compare.title": "Gratis vs Premium",
    "compare.feature": "Característica",
    "compare.free": "Gratis",
    "compare.premium": "Premium",
    "compare.picks": "Picks Diarios",
    "compare.all": "Todos",
    "compare.markets": "Mercados",
    "compare.leagues_label": "Ligas",
    "compare.all_leagues": "Las 5 + Mundial",
    "compare.odds": "Cuotas y Edge",
    "compare.alerts": "Alertas en Tiempo Real",
    "compare.results": "Resultados Diarios",
    "wc.desc": "Obtén predicciones IA para cada partido del Mundial. Nuestros modelos están entrenados con datos de fútbol internacional.",
    "wc.promo": "¡Primer mes solo $9.99 — Especial Mundial!",
    "pricing.title": "Elige Tu Plan",
    "pricing.monthly": "Mensual",
    "pricing.quarterly": "Trimestral",
    "pricing.promo_title": "Promo",
    "pricing.save": "Ahorra 17%",
    "pricing.first_month": " 1er mes",
    "pricing.then": "Luego $19.99/mes",
    "pricing.feature1": "Todos los picks, todos los mercados",
    "pricing.feature2": "5 ligas + Mundial",
    "pricing.feature3": "Alertas en tiempo real",
    "pricing.feature4": "Cancela cuando quieras",
    "pricing.feature4_q": "Mejor valor",
    "pricing.feature_wc": "Cobertura del Mundial",
    "pricing.subscribe": "Suscribirse",
    "faq.title": "Preguntas Frecuentes",
    "faq.q1": "¿Cómo recibo los picks?",
    "faq.a1": "Por Telegram. Después de suscribirte, nuestro bot te envía un link de invitación al canal premium donde se publican los picks diariamente.",
    "faq.q2": "¿Puedo cancelar en cualquier momento?",
    "faq.a2": "Sí. Cancela a través de Stripe y mantendrás el acceso hasta el final de tu período de facturación.",
    "faq.q3": "¿Qué ligas cubren?",
    "faq.a3": "Premier League, La Liga, Serie A, Bundesliga, Ligue 1 y Copa Mundial FIFA 2026.",
    "faq.q4": "¿Cómo se generan las predicciones?",
    "faq.a4": "Usamos 6 modelos XGBoost entrenados con 100,000+ partidos históricos con 46+ features incluyendo forma, xG, ratings Elo y estadísticas directas.",
    "faq.q5": "¿Garantizan ganancias?",
    "faq.a5": "No. Master Prediction es un servicio informativo. Las apuestas deportivas implican riesgo. Proporcionamos análisis basado en datos, no asesoría financiera.",
    "footer.free": "Unirse al Canal Gratis",
    "footer.disclaimer": "Master Prediction es un servicio informativo. No garantizamos ganancias. Las apuestas deportivas implican riesgo. Apuesta responsablemente. 18+.",
  },
};

function setLang(lang) {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (translations[lang] && translations[lang][key]) {
      el.textContent = translations[lang][key];
    }
  });
  document.getElementById("btn-en").classList.toggle("active", lang === "en");
  document.getElementById("btn-es").classList.toggle("active", lang === "es");
  localStorage.setItem("lang", lang);
}

// Init
const saved = localStorage.getItem("lang") || "en";
setLang(saved);
```

### Step 4: Create success page

Create `landing/success.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Premium — Master Prediction</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <section class="hero" style="min-height: 100vh; display: flex; align-items: center;">
        <div class="container" style="text-align: center;">
            <div style="font-size: 4rem; margin-bottom: 24px;">🎉</div>
            <h1 style="color: #4CAF50;">Payment Successful!</h1>
            <p class="subtitle">Our bot will send you an invite link to the premium channel shortly.</p>
            <p class="subtitle">Check your Telegram messages from <b>@MasterPredictionBot</b>.</p>
            <a href="https://t.me/MasterPredictionBot" class="cta-btn" style="margin-top: 24px;">Open Telegram Bot</a>
        </div>
    </section>
</body>
</html>
```

- [ ] **Step 5: Commit**

```bash
git add landing/
git commit -m "feat: add bilingual landing page with pricing and World Cup promo"
```

**Note:** Replace `TELEGRAM_BOT_SUBSCRIBE_LINK` and `TELEGRAM_FREE_CHANNEL_LINK` placeholders with real URLs when deploying. To deploy on GitHub Pages, enable Pages for the `/landing` folder or create a separate repo.

---

## Task 10: Admin Panel — Suscripciones View

**Files:**
- Modify: `dashboard/data_access.py`
- Create: `dashboard/views/9_suscripciones.py`

### Step 1: Add data access functions

Add to the bottom of `dashboard/data_access.py`:

```python
@st.cache_data(ttl=60)
def get_subscriptions() -> list[dict]:
    client = get_supabase_client()
    resp = (
        client.table("subscriptions")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


@st.cache_data(ttl=60)
def get_payments() -> list[dict]:
    client = get_supabase_client()
    resp = (
        client.table("payments")
        .select("*, subscriptions(telegram_username, plan)")
        .order("paid_at", desc=True)
        .execute()
    )
    return resp.data or []


def get_subscription_kpis(subscriptions: list[dict], payments: list[dict]) -> dict:
    from datetime import datetime, timezone

    active = [s for s in subscriptions if s["status"] == "active"]
    cancelled = [s for s in subscriptions if s["status"] == "cancelled"]

    mrr = 0.0
    for s in active:
        if s["plan"] == "monthly":
            mrr += 19.99
        elif s["plan"] == "quarterly":
            mrr += 49.99 / 3

    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y-%m")
    new_this_month = sum(
        1 for s in subscriptions
        if s.get("created_at", "").startswith(current_month)
    )

    total = len(subscriptions)
    churn_rate = len(cancelled) / total * 100 if total > 0 else 0.0

    month_payments = [
        p for p in payments
        if p.get("paid_at", "").startswith(current_month) and p["status"] == "succeeded"
    ]
    revenue_this_month = sum(float(p["amount_usd"]) for p in month_payments)

    return {
        "mrr": round(mrr, 2),
        "active_count": len(active),
        "new_this_month": new_this_month,
        "churn_rate": round(churn_rate, 1),
        "revenue_this_month": round(revenue_this_month, 2),
    }
```

### Step 2: Create the admin view

Create `dashboard/views/9_suscripciones.py`:

```python
import pandas as pd
import streamlit as st

from dashboard.auth import require_admin
from dashboard.components.theme import section_header, stat_card
from dashboard.data_access import (
    get_payments,
    get_subscription_kpis,
    get_subscriptions,
    get_supabase_client,
)

if not require_admin():
    st.stop()

st.markdown(
    '<h1 style="font-size:2rem;">💳 Suscripciones</h1>',
    unsafe_allow_html=True,
)

subscriptions = get_subscriptions()
payments = get_payments()
kpis = get_subscription_kpis(subscriptions, payments)

# ── KPIs ──
st.markdown(section_header("📊", "Indicadores"), unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        stat_card("MRR", f"${kpis['mrr']:.2f}", "ingreso recurrente mensual"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        stat_card("Activos", str(kpis["active_count"]), "suscriptores"),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        stat_card("Nuevos", str(kpis["new_this_month"]), "este mes"),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        stat_card("Churn", f"{kpis['churn_rate']:.1f}%", "tasa de cancelacion"),
        unsafe_allow_html=True,
    )

# ── Suscriptores ──
st.markdown(section_header("👥", "Suscriptores"), unsafe_allow_html=True)

if subscriptions:
    status_filter = st.selectbox(
        "Filtrar por estado",
        ["Todos", "active", "cancelled", "past_due", "expired"],
        key="sub_status_filter",
    )

    filtered = subscriptions
    if status_filter != "Todos":
        filtered = [s for s in subscriptions if s["status"] == status_filter]

    STATUS_ICONS = {
        "active": "🟢",
        "cancelled": "🔴",
        "past_due": "🟡",
        "expired": "⚫",
    }

    rows = []
    for s in filtered:
        icon = STATUS_ICONS.get(s["status"], "")
        end_date = s.get("current_period_end", "")[:10] if s.get("current_period_end") else "—"
        rows.append(
            {
                "Usuario": f"@{s.get('telegram_username') or s['telegram_user_id']}",
                "Plan": s["plan"].capitalize(),
                "Estado": f"{icon} {s['status']}",
                "Inicio": s.get("created_at", "")[:10],
                "Proximo Cobro": end_date,
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Actions ──
    st.markdown(section_header("🔧", "Acciones"), unsafe_allow_html=True)

    active_subs = [s for s in subscriptions if s["status"] == "active"]
    if active_subs:
        usernames = [
            f"@{s.get('telegram_username') or s['telegram_user_id']}" for s in active_subs
        ]
        selected = st.selectbox("Seleccionar suscriptor", usernames, key="sub_action_select")
        selected_sub = active_subs[usernames.index(selected)]

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("❌ Revocar Acceso", use_container_width=True):
                client = get_supabase_client()
                client.table("subscriptions").update(
                    {"status": "cancelled"}
                ).eq("id", selected_sub["id"]).execute()
                st.success(f"Acceso revocado para {selected}")
                st.rerun()
        with col_b:
            if st.button("📅 Extender 7 dias", use_container_width=True):
                from datetime import datetime, timedelta, timezone

                current_end = selected_sub.get("current_period_end")
                if current_end:
                    new_end = datetime.fromisoformat(
                        current_end.replace("Z", "+00:00")
                    ) + timedelta(days=7)
                else:
                    new_end = datetime.now(timezone.utc) + timedelta(days=7)

                client = get_supabase_client()
                client.table("subscriptions").update(
                    {"current_period_end": new_end.isoformat()}
                ).eq("id", selected_sub["id"]).execute()
                st.success(f"Suscripcion extendida 7 dias para {selected}")
                st.rerun()
    else:
        st.info("No hay suscriptores activos.")
else:
    st.info("No hay suscripciones registradas.")

# ── Historial de Pagos ──
st.markdown(section_header("💰", "Historial de Pagos"), unsafe_allow_html=True)

if payments:
    pay_status_filter = st.selectbox(
        "Filtrar por estado",
        ["Todos", "succeeded", "failed", "refunded"],
        key="pay_status_filter",
    )

    filtered_payments = payments
    if pay_status_filter != "Todos":
        filtered_payments = [p for p in payments if p["status"] == pay_status_filter]

    pay_rows = []
    for p in filtered_payments:
        sub_info = p.get("subscriptions") or {}
        username = sub_info.get("telegram_username", "—")
        plan = sub_info.get("plan", "—")

        STATUS_PAY_ICONS = {"succeeded": "✅", "failed": "❌", "refunded": "↩️"}
        icon = STATUS_PAY_ICONS.get(p["status"], "")

        pay_rows.append(
            {
                "Fecha": p.get("paid_at", "")[:10],
                "Usuario": f"@{username}" if username != "—" else "—",
                "Monto": f"${float(p['amount_usd']):.2f}",
                "Plan": plan.capitalize() if plan != "—" else "—",
                "Estado": f"{icon} {p['status']}",
            }
        )

    st.dataframe(pd.DataFrame(pay_rows), use_container_width=True, hide_index=True)

    total_revenue = sum(
        float(p["amount_usd"]) for p in payments if p["status"] == "succeeded"
    )
    st.markdown(
        stat_card("Ingresos Totales", f"${total_revenue:.2f}", "todos los pagos exitosos"),
        unsafe_allow_html=True,
    )
else:
    st.info("No hay pagos registrados.")
```

- [ ] **Step 3: Lint**

```bash
python3 -m ruff check dashboard/views/9_suscripciones.py dashboard/data_access.py
python3 -m ruff format dashboard/views/9_suscripciones.py dashboard/data_access.py
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/views/9_suscripciones.py dashboard/data_access.py
git commit -m "feat: add admin subscriptions panel with KPIs, payments, and subscriber management"
```

---

## Task 11: Integration Verification

**Files:** None (verification only)

### Step 1: Run all tests

```bash
PYTHONPATH=. python3 -m pytest tests/ -x -q
```

Expected: all tests pass including new tests for subscriptions, channel access, and free picks.

### Step 2: Lint entire project

```bash
python3 -m ruff check .
python3 -m ruff format --check .
```

Expected: no errors.

### Step 3: Verify file structure

```bash
ls backend/subscriptions/
# Expected: __init__.py  models.py  service.py  channel.py  stripe_checkout.py

ls supabase/functions/
# Expected: stripe-webhook/  telegram-bot/

ls landing/
# Expected: index.html  styles.css  script.js  success.html

ls dashboard/views/9_suscripciones.py
# Expected: file exists
```

### Step 4: Final commit (if any lint fixes)

```bash
git add -A
git diff --cached --quiet || git commit -m "chore: lint fixes for monetization integration"
```

---

## Post-Implementation: Manual Setup Steps

These steps are done manually, not in code:

1. **Stripe Dashboard:**
   - Create account at stripe.com
   - Create Product "Master Prediction Premium"
   - Create two Prices: $19.99/month and $49.99/3 months
   - Create a coupon for World Cup promo ($10.00 off first month)
   - Copy Price IDs to environment variables
   - Configure webhook endpoint URL

2. **Supabase:**
   - Run SQL migration in SQL Editor
   - Deploy Edge Functions (stripe-webhook, telegram-bot)
   - Set Edge Function secrets (STRIPE_WEBHOOK_SECRET, TELEGRAM_BOT_TOKEN, etc.)

3. **Telegram:**
   - Create free public channel
   - Create premium private channel
   - Register bot webhook: `curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<EDGE_FUNCTION_URL>"`
   - Add bot as admin to both channels

4. **GitHub:**
   - Add new secrets: STRIPE_SECRET_KEY, TELEGRAM_FREE_CHANNEL_ID, TELEGRAM_PREMIUM_CHANNEL_ID, LANDING_URL
   - Enable GitHub Pages for landing page

5. **Landing page:**
   - Replace placeholder links (TELEGRAM_BOT_SUBSCRIBE_LINK, TELEGRAM_FREE_CHANNEL_LINK)
   - Update bot name in success.html
