import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const WEBHOOK_SECRET = Deno.env.get("LS_WEBHOOK_SECRET") || "";
const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_SERVICE_ROLE_KEY =
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") || "";
const TELEGRAM_ADMIN_CHAT_ID = Deno.env.get("TELEGRAM_ADMIN_CHAT_ID") || "";
const TELEGRAM_PREMIUM_CHANNEL_ID =
  Deno.env.get("TELEGRAM_PREMIUM_CHANNEL_ID") || "";
const LANDING_URL =
  Deno.env.get("LANDING_URL") ||
  "https://imolina29.github.io/master-prediction";

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

async function telegramApi(
  method: string,
  body: Record<string, unknown>,
) {
  const resp = await fetch(
    `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/${method}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  return resp.json();
}

async function notifyAdmin(text: string) {
  if (!TELEGRAM_ADMIN_CHAT_ID) return;
  await telegramApi("sendMessage", {
    chat_id: TELEGRAM_ADMIN_CHAT_ID,
    text,
    parse_mode: "HTML",
  });
}

async function sendInviteToUser(telegramUserId: string): Promise<boolean> {
  for (let attempt = 0; attempt < 3; attempt++) {
    const linkResult = await telegramApi("createChatInviteLink", {
      chat_id: TELEGRAM_PREMIUM_CHANNEL_ID,
      member_limit: 1,
    });

    if (!linkResult.ok) {
      if (attempt < 2) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
      await notifyAdmin(
        `🚨 <b>ERROR:</b> Could not create invite link for user ${telegramUserId} after 3 attempts. Manual action required.`,
      );
      return false;
    }

    const inviteLink = linkResult.result.invite_link;
    await telegramApi("sendMessage", {
      chat_id: telegramUserId,
      text:
        `🎉 <b>Welcome to Master Prediction Premium!</b>\n\n` +
        `Join here:\n${inviteLink}\n\n` +
        `You'll receive all picks with odds, edge & confidence daily.`,
      parse_mode: "HTML",
    });
    return true;
  }
  return false;
}

async function revokeUserAccess(telegramUserId: string) {
  await telegramApi("banChatMember", {
    chat_id: TELEGRAM_PREMIUM_CHANNEL_ID,
    user_id: Number(telegramUserId),
  });
  await telegramApi("unbanChatMember", {
    chat_id: TELEGRAM_PREMIUM_CHANNEL_ID,
    user_id: Number(telegramUserId),
  });
  await telegramApi("sendMessage", {
    chat_id: telegramUserId,
    text:
      "Your Master Prediction Premium subscription has ended.\n\n" +
      `Renew anytime at ${LANDING_URL}`,
  });
}

async function verifySignature(
  body: string,
  signature: string,
): Promise<boolean> {
  if (!signature || !WEBHOOK_SECRET) return false;

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(WEBHOOK_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(body),
  );
  const computed = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  return computed === signature;
}

function detectPlan(variantName: string, intervalCount: number): string {
  if (intervalCount === 3) return "quarterly";
  if (
    variantName.toLowerCase().includes("trimestral") ||
    variantName.toLowerCase().includes("quarterly")
  ) {
    return "quarterly";
  }
  return "monthly";
}

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const body = await req.text();
  const signature = req.headers.get("x-signature") || "";

  const valid = await verifySignature(body, signature);
  if (!valid) {
    return new Response("Invalid signature", { status: 400 });
  }

  const payload = JSON.parse(body);
  const eventName = payload.meta?.event_name as string;
  const customData = payload.meta?.custom_data || {};
  const attrs = payload.data?.attributes || {};
  const lsSubscriptionId = String(payload.data?.id || "");

  try {
    if (eventName === "subscription_created") {
      const telegramUserId = customData.telegram_user_id || "";
      const telegramUsername = customData.telegram_username || "";
      const lsCustomerId = String(attrs.customer_id || "");
      const variantName = attrs.variant_name || "";
      const intervalCount = attrs.billing_anchor || 1;
      const plan = detectPlan(variantName, intervalCount);
      const renewsAt = attrs.renews_at || null;

      const { data: existing } = await supabase
        .from("subscriptions")
        .select("id")
        .eq("provider_subscription_id", lsSubscriptionId)
        .maybeSingle();

      if (existing) {
        return new Response(
          JSON.stringify({ received: true, duplicate: true }),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        );
      }

      await supabase.from("subscriptions").insert({
        telegram_user_id: telegramUserId,
        telegram_username: telegramUsername,
        provider_customer_id: lsCustomerId,
        provider_subscription_id: lsSubscriptionId,
        plan,
        status: "active",
        current_period_end: renewsAt,
      });

      const invited = await sendInviteToUser(telegramUserId);
      await notifyAdmin(
        `🆕 <b>New subscriber:</b> @${telegramUsername || telegramUserId}` +
          ` — Premium ${plan}` +
          (invited ? "" : "\n⚠️ Invite link failed — send manually"),
      );
    }

    if (eventName === "subscription_updated") {
      const status = attrs.status as string;
      const renewsAt = attrs.renews_at || null;
      const endsAt = attrs.ends_at || null;

      const dbStatus =
        status === "active"
          ? "active"
          : status === "past_due"
            ? "past_due"
            : status === "cancelled"
              ? "cancelled"
              : status === "expired"
                ? "expired"
                : "active";

      await supabase
        .from("subscriptions")
        .update({
          status: dbStatus,
          current_period_end: endsAt || renewsAt,
          updated_at: new Date().toISOString(),
        })
        .eq("provider_subscription_id", lsSubscriptionId);
    }

    if (eventName === "subscription_payment_success") {
      const { data: sub } = await supabase
        .from("subscriptions")
        .select("id")
        .eq("provider_subscription_id", lsSubscriptionId)
        .maybeSingle();

      if (sub) {
        const amount = attrs.subtotal_formatted
          ? parseFloat(String(attrs.subtotal || 0)) / 100
          : 0;

        await supabase.from("payments").insert({
          subscription_id: sub.id,
          provider_payment_id: String(payload.data?.id || ""),
          amount: amount,
          status: "succeeded",
        });
      }
    }

    if (eventName === "subscription_payment_failed") {
      await supabase
        .from("subscriptions")
        .update({
          status: "past_due",
          updated_at: new Date().toISOString(),
        })
        .eq("provider_subscription_id", lsSubscriptionId);

      const { data: sub } = await supabase
        .from("subscriptions")
        .select("telegram_username, telegram_user_id")
        .eq("provider_subscription_id", lsSubscriptionId)
        .maybeSingle();

      if (sub) {
        await notifyAdmin(
          `⚠️ <b>Payment failed:</b> @${sub.telegram_username || sub.telegram_user_id}`,
        );
      }
    }

    if (
      eventName === "subscription_cancelled" ||
      eventName === "subscription_expired"
    ) {
      const { data: sub } = await supabase
        .from("subscriptions")
        .select("telegram_user_id, telegram_username")
        .eq("provider_subscription_id", lsSubscriptionId)
        .maybeSingle();

      const newStatus =
        eventName === "subscription_expired" ? "expired" : "cancelled";

      await supabase
        .from("subscriptions")
        .update({
          status: newStatus,
          updated_at: new Date().toISOString(),
        })
        .eq("provider_subscription_id", lsSubscriptionId);

      if (sub) {
        await revokeUserAccess(sub.telegram_user_id);
        await notifyAdmin(
          `❌ <b>Subscription ${newStatus}:</b> @${sub.telegram_username || sub.telegram_user_id}`,
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
