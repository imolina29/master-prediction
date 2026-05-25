import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const STRIPE_WEBHOOK_SECRET = Deno.env.get("STRIPE_WEBHOOK_SECRET") || "";
const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const TELEGRAM_BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") || "";
const TELEGRAM_ADMIN_CHAT_ID = Deno.env.get("TELEGRAM_ADMIN_CHAT_ID") || "";
const TELEGRAM_PREMIUM_CHANNEL_ID =
  Deno.env.get("TELEGRAM_PREMIUM_CHANNEL_ID") || "";

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

async function sendInviteToUser(telegramUserId: string) {
  const linkResult = await telegramApi("createChatInviteLink", {
    chat_id: TELEGRAM_PREMIUM_CHANNEL_ID,
    member_limit: 1,
  });

  if (!linkResult.ok) return;
  const inviteLink = linkResult.result.invite_link;

  await telegramApi("sendMessage", {
    chat_id: telegramUserId,
    text:
      `🎉 <b>Welcome to Master Prediction Premium!</b>\n\n` +
      `Join here:\n${inviteLink}\n\n` +
      `You'll receive all picks with odds, edge & confidence daily.`,
    parse_mode: "HTML",
  });
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
      "Renew anytime at https://masterprediction.com",
  });
}

async function verifyStripeSignature(
  body: string,
  signature: string,
): Promise<Record<string, unknown> | null> {
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
    ["sign"],
  );

  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(signedPayload),
  );
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
  const data = (event.data as Record<string, unknown>)
    .object as Record<string, unknown>;

  try {
    if (eventType === "checkout.session.completed") {
      const telegramUserId = data.client_reference_id as string;
      const metadata = data.metadata as Record<string, string>;
      const telegramUsername = metadata?.telegram_username || "";
      const stripeCustomerId = data.customer as string;
      const stripeSubscriptionId = data.subscription as string;

      const plan = "monthly";

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
        `🆕 <b>New subscriber:</b> @${telegramUsername || telegramUserId}` +
          ` — Premium ${plan} ($${plan === "monthly" ? "19.99" : "49.99"})`,
      );
    }

    if (eventType === "invoice.paid") {
      const stripeSubscriptionId = data.subscription as string;
      const amountPaid = (data.amount_paid as number) / 100;
      const paymentIntentId = data.payment_intent as string;
      const periodStart = new Date(
        (data.period_start as number) * 1000,
      ).toISOString();
      const periodEnd = new Date(
        (data.period_end as number) * 1000,
      ).toISOString();

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
        .update({
          status: "past_due",
          updated_at: new Date().toISOString(),
        })
        .eq("stripe_subscription_id", stripeSubscriptionId);

      const { data: sub } = await supabase
        .from("subscriptions")
        .select("telegram_username, telegram_user_id")
        .eq("stripe_subscription_id", stripeSubscriptionId)
        .single();

      if (sub) {
        await notifyAdmin(
          `⚠️ <b>Payment failed:</b> @${sub.telegram_username || sub.telegram_user_id}`,
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
        .update({
          status: "cancelled",
          updated_at: new Date().toISOString(),
        })
        .eq("stripe_subscription_id", stripeSubscriptionId);

      if (sub) {
        await revokeUserAccess(sub.telegram_user_id);
        await notifyAdmin(
          `❌ <b>Subscription cancelled:</b> @${sub.telegram_username || sub.telegram_user_id}`,
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
