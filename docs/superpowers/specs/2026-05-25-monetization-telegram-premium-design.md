# Monetization: Telegram Premium Subscription — Design Spec

## Goal

Monetize Master Prediction through a Telegram-first subscription model with two tiers (Free + Premium), Stripe payments, a bilingual landing page, and an admin panel for subscription management. Target: international betting audience. Launch before FIFA World Cup 2026 (June 11, 2026).

## Context

Master Prediction is a football betting intelligence platform with:
- 6 XGBoost models (base + premium × 3 targets) trained weekly
- Daily ETL pipeline generating predictions, value bets, and alerts
- Telegram bot sending picks, results, and alerts to authorized chats
- Streamlit dashboard with auth, roles (admin/viewer), and performance views
- Value bet engine with vig removal, edge calculation, and contradictory pick filtering

Current state: all notifications go to a flat list of authorized chat IDs (`TELEGRAM_AUTHORIZED_CHATS`). No concept of tiers, subscriptions, or paid access.

## Architecture Overview

```
Landing Page (GitHub Pages)
    ↓ user clicks "Subscribe"
Stripe Checkout (hosted by Stripe)
    ↓ payment succeeds
Stripe Webhook → Backend endpoint
    ↓ records payment + subscription
Supabase (subscriptions + payments tables)
    ↓ bot reads subscription status
Telegram Bot → grants access to premium channel
```

**Costo fijo mensual: $0.** Stripe only charges commission (2.9% + $0.30) on actual payments.

---

## 1. Telegram Channel Structure

### 1.1 Free Channel (Public)

A public Telegram channel where anyone can join. Serves as a marketing funnel.

**Content delivered daily:**
- Top 1-2 picks of the day (1x2 market only)
- No odds, no edge, no stake — just the prediction
- Only Premier League (club) + World Cup matches (during tournament)
- Weekly summary (general, no detailed profit)
- CTA at the bottom: "Want all picks with odds & edge? → [link to landing]"

**Content format example:**
```
⚽ Master Prediction — Free Pick

🏴󠁧󠁢󠁥󠁮󠁧󠁿 Arsenal vs Chelsea
📊 Prediction: Arsenal Win

🔒 Get all picks + odds + edge → masterprediction.com
```

### 1.2 Premium Channel (Private)

A private Telegram channel. Users get an invite link after paying through Stripe.

**Content delivered daily (same as current `send_daily_picks` but to premium channel):**
- All picks across all markets (1x2, Over/Under, BTTS)
- All 5 leagues + World Cup
- Full detail: odds, edge, stake, confidence
- Real-time alerts for high-confidence picks (stake 3)
- Daily results with profit breakdown
- Weekly detailed summary with ROI by league/market

### 1.3 Bot Commands

The existing bot gains new commands for subscription management:

| Command | Who | Action |
|---------|-----|--------|
| `/start` | Anyone | Welcome message + link to free channel |
| `/status` | Subscriber | Shows subscription status, plan, next payment date |
| `/help` | Anyone | Available commands + link to landing |

### 1.4 Admin Notifications (to Ivan's private chat)

The bot sends admin alerts to the existing `TELEGRAM_CHAT_ID`:
- "🆕 New subscriber: @username — Premium Monthly ($19.99)"
- "❌ Subscription cancelled: @username"
- "⚠️ Payment failed: @username — retrying"

---

## 2. Pricing Plans

| Plan | Price | Stripe Price ID | Notes |
|------|-------|-----------------|-------|
| Premium Monthly | $19.99/month | Created in Stripe Dashboard | Recurring |
| Premium Quarterly | $49.99/3 months | Created in Stripe Dashboard | Recurring, 17% discount |
| World Cup Promo | $9.99 first month | Stripe coupon on monthly plan | Then $19.99/month |

All prices in USD. Stripe handles currency conversion for international users.

The promo plan uses a Stripe coupon that reduces the first month from $19.99 to $9.99. Applied to the monthly price. After the first billing cycle, Stripe charges the full $19.99/month automatically.

---

## 3. Database Schema

### 3.1 Table: `subscriptions`

```sql
CREATE TABLE subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_user_id TEXT NOT NULL,
    telegram_username TEXT,
    stripe_customer_id TEXT NOT NULL,
    stripe_subscription_id TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL CHECK (plan IN ('monthly', 'quarterly')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'past_due', 'expired')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 3.2 Table: `payments`

```sql
CREATE TABLE payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subscription_id UUID REFERENCES subscriptions(id),
    stripe_payment_intent_id TEXT UNIQUE,
    amount_usd NUMERIC(10, 2) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed', 'refunded')),
    paid_at TIMESTAMPTZ DEFAULT now()
);
```

### 3.3 Row-Level Security

Both tables use service role key only (no anon access). The dashboard reads via service key, same as existing pattern.

---

## 4. Stripe Integration

### 4.1 Stripe Checkout Flow

The key challenge is linking a Stripe payment to a Telegram user. The flow uses the bot as the entry point:

1. User sees CTA in free channel → clicks link to bot DM (`t.me/botname?start=subscribe`)
2. Bot captures the user's numeric Telegram ID and username
3. Bot replies with a Stripe Checkout link that includes `client_reference_id=<telegram_user_id>` and `metadata.telegram_username=<username>`
4. User pays on Stripe's hosted checkout page (no custom payment form needed)
5. On success, Stripe redirects to a "Thank you" page with instructions to wait for the invite link
6. Stripe webhook fires → backend creates subscription → bot sends invite link to the user via DM

The landing page "Subscribe" buttons also link to `t.me/botname?start=subscribe`, routing through the bot to capture the Telegram ID before checkout.

**Important:** The bot currently is notification-only (sends messages, does not receive commands). This subsystem requires adding a command handler. Two options:
- **Telegram webhook on Supabase Edge Function**: Telegram sends updates to a URL. Low cost, event-driven. Recommended.
- **Long polling script**: Runs continuously, listens for updates. Needs persistent hosting.

Recommended: Supabase Edge Function for both Stripe webhooks and Telegram bot updates (can be two separate functions).

### 4.2 Webhook Endpoint

A lightweight HTTP endpoint to receive Stripe webhook events. Options for hosting:

**Recommended: Supabase Edge Function** — free tier includes 500K invocations/month, runs on Deno, perfect for webhooks. No extra hosting cost.

**Alternative: GitHub Actions workflow_dispatch** — receives webhook via a relay service. More complex, less reliable.

The webhook handles these events:

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Create subscription record, notify admin, send invite link to user |
| `invoice.paid` | Record payment, update `current_period_end` |
| `invoice.payment_failed` | Update status to `past_due`, notify admin |
| `customer.subscription.deleted` | Update status to `cancelled`, revoke channel access, notify admin |

### 4.3 Stripe Setup (Manual, in Stripe Dashboard)

- Create Products and Prices (monthly, quarterly)
- Create a coupon for World Cup promo
- Configure webhook endpoint URL
- Get API keys (publishable + secret)

---

## 5. Landing Page

### 5.1 Tech

Static HTML/CSS/JS hosted on GitHub Pages. No framework needed — single page, fast loading.

Repository: can be a separate repo (`master-prediction-landing`) or a `/landing` folder in the existing repo deployed via GitHub Pages.

### 5.2 Sections

1. **Hero**: Headline + subtitle + live stats (win rate, total picks, ROI) + CTA button
2. **How it works**: 3 icons — "AI analyzes 100K+ matches" → "Generates value bets daily" → "You receive picks on Telegram"
3. **Track record**: Table/chart with backtest results by model, accuracy, ROI. Profit curve image.
4. **Free vs Premium**: Side-by-side comparison table
5. **Pricing**: 3 plan cards (monthly, quarterly, promo) with Stripe Checkout links
6. **World Cup banner**: Promotional section for the FIFA 2026 tournament picks
7. **FAQ**: 5-6 common questions
8. **Footer**: Link to free Telegram channel, legal disclaimer, contact

### 5.3 Bilingual

Toggle button EN/ES. Content stored in a simple JS object (`translations.en`, `translations.es`). Default: English.

### 5.4 Legal Disclaimer

Required text: "Master Prediction is an informational service. We do not guarantee profits. Sports betting involves risk. Gamble responsibly. 18+."

---

## 6. Notification System Changes

### 6.1 Current System

`TelegramNotifier.send_to_all()` sends to all `TELEGRAM_AUTHORIZED_CHATS`. No tier differentiation.

### 6.2 New System

Two notifier instances:

- **Free notifier**: sends to the free public channel (new channel ID)
- **Premium notifier**: sends to the premium private channel (new channel ID)

The pipeline script (`run_notifications.py`) generates two versions of the content:
- Free version: filtered (1x2 only, top 1-2, no odds/edge, single league)
- Premium version: full content (same as current `send_daily_picks`)

### 6.3 Free Content Generation

New function `build_free_picks(picks)` that:
1. Filters to 1x2 market only
2. Filters to Premier League + World Cup division
3. Sorts by confidence, takes top 2
4. Strips odds, edge, and stake from the message
5. Appends CTA to landing page

---

## 7. Admin Panel (Streamlit)

### 7.1 New Dashboard View: "Suscripciones"

Added as a new view in `dashboard/views/` accessible only to admin role.

**KPI row:**
- MRR (Monthly Recurring Revenue)
- Active subscribers count
- New subscribers this month
- Churn rate (cancelled / total)

**Payments table (full history):**
- Columns: Date, Telegram user, Amount, Plan, Status
- Filters: date range, plan, status
- Export to CSV (optional, later)

**Subscribers table:**
- Columns: Telegram user, Plan, Status, Start date, Next payment, Actions
- Action buttons: "Revoke access", "Extend 7 days" (for support cases)

### 7.2 Data Access

New functions in `dashboard/data_access.py`:
- `get_subscriptions()` — all subscriptions with filters
- `get_payments()` — all payments with filters
- `get_subscription_kpis()` — computed MRR, churn, etc.

---

## 8. Bot Access Control

### 8.1 Channel Access Management

When a subscription is created:
1. Bot generates a one-time invite link for the premium channel (`createChatInviteLink` with `member_limit=1`)
2. Bot sends the link to the user via DM
3. User joins the premium channel

When a subscription is cancelled/expired:
1. Bot kicks the user from the premium channel (`banChatMember` + `unbanChatMember` to remove without permanent ban)
2. Bot sends a message to the user: "Your subscription has ended. Renew at [landing URL]"

### 8.2 Subscription Verification

The bot checks subscription status before processing commands. The `is_authorized_chat` function in `auth_telegram.py` is extended to check subscription status from Supabase, not just environment variables.

---

## 9. World Cup Strategy

### 9.1 Timeline

- **May 25 – June 10**: Build and test everything in develop
- **June 8-10**: Create Telegram channels, set up Stripe, deploy landing
- **June 11**: World Cup starts — free channel begins posting World Cup picks
- **June 11 – July 19**: Active marketing during tournament
- **Post-World Cup**: Transition to league season content

### 9.2 Marketing Hooks

- Free channel posts World Cup picks daily during the tournament
- Each free pick message includes CTA to premium
- Landing page has prominent World Cup promo section
- Promo price ($9.99 first month) highlighted during the tournament

### 9.3 Model Readiness

The models already support international matches via national team features (`load_national_features()` in `run_predictions.py`). The ETL already fetches World Cup fixtures when available.

---

## 10. Implementation Scope

### What to build (in order):

1. **Database**: Create `subscriptions` and `payments` tables in Supabase
2. **Stripe webhook**: Supabase Edge Function to handle Stripe events
3. **Bot enhancements**: Tier-based content delivery, access control, admin notifications
4. **Notification split**: Free vs premium content generation in pipeline
5. **Landing page**: Static site with Stripe Checkout links
6. **Admin panel**: New Streamlit view for subscription management
7. **Testing**: End-to-end flow with Stripe test mode

### What NOT to build (YAGNI):

- Mobile app
- Custom payment form (use Stripe Checkout)
- Email marketing system
- Referral/affiliate system
- Multi-currency pricing
- Free trial (the free channel IS the trial)
- API access tier
- Automated marketing campaigns

### Environment:

- All development on `develop` branch
- Stripe in **test mode** (no real charges)
- Telegram channels created as test channels first
- Landing page on a test GitHub Pages URL
- Promotion to production is a separate decision by Ivan

---

## 11. Subsystem Decomposition

This project has 5 independent subsystems that should be built in order:

1. **Database + Stripe webhook** — foundation, no dependencies
2. **Bot access control** — depends on database
3. **Notification split (free/premium)** — depends on bot changes
4. **Landing page** — independent, can be built in parallel
5. **Admin panel** — depends on database

Each subsystem gets its own tasks in the implementation plan.
