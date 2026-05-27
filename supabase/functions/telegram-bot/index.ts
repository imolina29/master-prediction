import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") || "";
const STRIPE_PRICE_MONTHLY = Deno.env.get("STRIPE_PRICE_MONTHLY") || "";
const STRIPE_PRICE_QUARTERLY = Deno.env.get("STRIPE_PRICE_QUARTERLY") || "";
const STRIPE_SECRET_KEY = Deno.env.get("STRIPE_SECRET_KEY") || "";
const LANDING_URL =
  Deno.env.get("LANDING_URL") || "https://masterprediction.com";
const TELEGRAM_FREE_CHANNEL_URL =
  Deno.env.get("TELEGRAM_FREE_CHANNEL_URL") || "";
const STRIPE_PROMO_CODE = Deno.env.get("STRIPE_PROMO_CODE") || "";

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

async function telegramReply(
  chatId: number | string,
  text: string,
  replyMarkup?: unknown,
) {
  const body: Record<string, unknown> = {
    chat_id: chatId,
    text,
    parse_mode: "HTML",
  };
  if (replyMarkup) body.reply_markup = replyMarkup;

  await fetch(
    `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

async function createCheckoutUrl(
  telegramUserId: string,
  username: string,
  plan: string,
  promoCode?: string,
): Promise<string | null> {
  const priceId =
    plan === "quarterly" ? STRIPE_PRICE_QUARTERLY : STRIPE_PRICE_MONTHLY;
  if (!priceId || !STRIPE_SECRET_KEY) return null;

  const params = new URLSearchParams();
  params.append("mode", "subscription");
  params.append("line_items[0][price]", priceId);
  params.append("line_items[0][quantity]", "1");
  params.append("success_url", `${LANDING_URL}/success.html`);
  params.append("cancel_url", LANDING_URL);
  params.append("client_reference_id", telegramUserId);
  params.append("metadata[telegram_username]", username);
  params.append("metadata[plan]", plan);
  if (promoCode) {
    params.append("discounts[0][promotion_code]", promoCode);
  }

  const resp = await fetch(
    "https://api.stripe.com/v1/checkout/sessions",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${STRIPE_SECRET_KEY}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    },
  );

  const session = await resp.json();
  return session.url || null;
}

async function checkActiveSubscription(userId: number): Promise<boolean> {
  const { data } = await supabase
    .from("subscriptions")
    .select("id")
    .eq("telegram_user_id", String(userId))
    .eq("status", "active")
    .maybeSingle();
  return !!data;
}

async function handleStart(
  chatId: number,
  userId: number,
  username: string,
  args: string,
) {
  if (args === "subscribe") {
    const hasActive = await checkActiveSubscription(userId);
    if (hasActive) {
      await telegramReply(
        chatId,
        "✅ You already have an active Premium subscription!\n\n" +
          "Use /status to see your subscription details.",
      );
      return;
    }

    const monthlyUrl = await createCheckoutUrl(
      String(userId),
      username,
      "monthly",
    );
    const quarterlyUrl = await createCheckoutUrl(
      String(userId),
      username,
      "quarterly",
    );

    const buttons: unknown[][] = [];
    if (monthlyUrl) {
      buttons.push([{ text: "📅 Monthly — $19.99/mo", url: monthlyUrl }]);
    }
    if (quarterlyUrl) {
      buttons.push([
        {
          text: "📅 Quarterly — $49.99/3mo (save 17%)",
          url: quarterlyUrl,
        },
      ]);
    }
    if (STRIPE_PROMO_CODE) {
      const promoUrl = await createCheckoutUrl(
        String(userId),
        username,
        "monthly",
        STRIPE_PROMO_CODE,
      );
      if (promoUrl) {
        buttons.push([
          { text: "🏆 World Cup Promo — $9.99 first month", url: promoUrl },
        ]);
      }
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
      ? new Date(sub.current_period_end).toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        })
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

async function handleCancel(
  chatId: number,
  userId: number,
  args: string,
) {
  const { data: sub } = await supabase
    .from("subscriptions")
    .select("*")
    .eq("telegram_user_id", String(userId))
    .eq("status", "active")
    .maybeSingle();

  if (!sub) {
    await telegramReply(
      chatId,
      "You don't have an active subscription to cancel.\n\n" +
        "Use /start subscribe to get Premium access!",
    );
    return;
  }

  if (args !== "confirm") {
    const endDate = sub.current_period_end
      ? new Date(sub.current_period_end).toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
        })
      : "end of current period";

    await telegramReply(
      chatId,
      "⚠️ <b>Cancel Subscription</b>\n\n" +
        `Plan: <b>${sub.plan}</b>\n` +
        `Access until: <b>${endDate}</b>\n\n` +
        "You will keep Premium access until the end of your current billing period.\n\n" +
        "To confirm cancellation, type:\n/cancel confirm",
    );
    return;
  }

  const resp = await fetch(
    `https://api.stripe.com/v1/subscriptions/${sub.stripe_subscription_id}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${STRIPE_SECRET_KEY}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: "cancel_at_period_end=true",
    },
  );
  const result = await resp.json();

  if (result.error) {
    await telegramReply(
      chatId,
      "❌ There was an error cancelling your subscription. Please try again or contact support.",
    );
    return;
  }

  const endDate = sub.current_period_end
    ? new Date(sub.current_period_end).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "end of current period";

  await telegramReply(
    chatId,
    "✅ <b>Subscription cancelled</b>\n\n" +
      `You will keep Premium access until <b>${endDate}</b>.\n` +
      "After that, you can re-subscribe anytime with /start subscribe.",
  );
}

async function handleHelp(chatId: number) {
  await telegramReply(
    chatId,
    "⚽ <b>Master Prediction — Help</b>\n\n" +
      "/start — Welcome & free channel link\n" +
      "/start subscribe — Subscribe to Premium\n" +
      "/status — Check your subscription status\n" +
      "/cancel — Cancel your subscription\n" +
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
  } else if (text.startsWith("/cancel")) {
    const cancelArgs = text.replace("/cancel", "").trim();
    await handleCancel(chatId, userId, cancelArgs);
  } else if (text === "/help") {
    await handleHelp(chatId);
  }

  return new Response("OK", { status: 200 });
});
