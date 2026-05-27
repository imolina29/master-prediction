import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_SERVICE_ROLE_KEY =
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") || "";
const LS_API_KEY = Deno.env.get("LS_API_KEY") || "";
const LS_STORE_ID = Deno.env.get("LS_STORE_ID") || "";
const LS_VARIANT_MONTHLY = Deno.env.get("LS_VARIANT_MONTHLY") || "";
const LS_VARIANT_QUARTERLY = Deno.env.get("LS_VARIANT_QUARTERLY") || "";
const LANDING_URL =
  Deno.env.get("LANDING_URL") ||
  "https://imolina29.github.io/master-prediction";
const TELEGRAM_FREE_CHANNEL_URL =
  Deno.env.get("TELEGRAM_FREE_CHANNEL_URL") || "";

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
  variantId: string,
): Promise<string | null> {
  if (!LS_API_KEY || !LS_STORE_ID || !variantId) return null;

  const resp = await fetch("https://api.lemonsqueezy.com/v1/checkouts", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${LS_API_KEY}`,
      "Content-Type": "application/vnd.api+json",
      Accept: "application/vnd.api+json",
    },
    body: JSON.stringify({
      data: {
        type: "checkouts",
        attributes: {
          checkout_data: {
            custom: {
              telegram_user_id: telegramUserId,
              telegram_username: username,
            },
          },
          product_options: {
            redirect_url: `${LANDING_URL}/success.html`,
          },
        },
        relationships: {
          store: { data: { type: "stores", id: LS_STORE_ID } },
          variant: { data: { type: "variants", id: variantId } },
        },
      },
    }),
  });

  const result = await resp.json();
  return result.data?.attributes?.url || null;
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
      LS_VARIANT_MONTHLY,
    );
    const quarterlyUrl = await createCheckoutUrl(
      String(userId),
      username,
      LS_VARIANT_QUARTERLY,
    );

    const buttons: unknown[][] = [];
    if (monthlyUrl) {
      buttons.push([
        { text: "📅 Mensual — $80,000 COP/mes", url: monthlyUrl },
      ]);
    }
    if (quarterlyUrl) {
      buttons.push([
        {
          text: "📅 Trimestral — $185,000 COP/3 meses",
          url: quarterlyUrl,
        },
      ]);
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
    `https://api.lemonsqueezy.com/v1/subscriptions/${sub.provider_subscription_id}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${LS_API_KEY}`,
        Accept: "application/vnd.api+json",
      },
    },
  );

  if (!resp.ok) {
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
