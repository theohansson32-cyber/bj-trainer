import Stripe from "npm:stripe@17";
import { createClient } from "npm:@supabase/supabase-js@2";

const stripeSecretKey = Deno.env.get("STRIPE_SECRET_KEY");
const webhookSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET");
const supabaseUrl = Deno.env.get("SUPABASE_URL");
const supabaseServiceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

if (!stripeSecretKey) {
  throw new Error("Missing STRIPE_SECRET_KEY");
}
if (!webhookSecret) {
  throw new Error("Missing STRIPE_WEBHOOK_SECRET");
}
if (!supabaseUrl) {
  throw new Error("Missing SUPABASE_URL");
}
if (!supabaseServiceRoleKey) {
  throw new Error("Missing SUPABASE_SERVICE_ROLE_KEY");
}

const stripe = new Stripe(stripeSecretKey, {
  apiVersion: "2023-10-16",
});

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const signature = req.headers.get("stripe-signature");
  if (!signature) {
    console.error("Missing stripe-signature header");
    return new Response("Missing stripe-signature header", { status: 400 });
  }

  const body = await req.text();

  let event: Stripe.Event;

  try {
    event = await stripe.webhooks.constructEventAsync(
      body,
      signature,
      webhookSecret
    );
  } catch (err) {
    console.error("Webhook signature error:", err);
    return new Response(
      `Webhook Error: ${err instanceof Error ? err.message : "Unknown error"}`,
      { status: 400 }
    );
  }

  console.log("Stripe event received", {
    type: event.type,
    id: event.id,
  });

  try {
    if (event.type === "checkout.session.completed") {
      const session = event.data.object as Stripe.Checkout.Session;

      console.log("checkout.session.completed payload", {
        sessionId: session.id,
        paymentStatus: session.payment_status,
        customerEmail: session.customer_details?.email ?? session.customer_email,
        metadata: session.metadata,
      });

      const userId = session.metadata?.supabase_user_id?.trim();

      console.log("Resolved userId:", userId);

      if (!userId) {
        console.error("Missing supabase_user_id in session metadata");
        return new Response("Missing supabase_user_id", { status: 400 });
      }

      if (session.payment_status !== "paid") {
        console.error("Session completed but payment_status is not paid", {
          sessionId: session.id,
          paymentStatus: session.payment_status,
        });
        return new Response("Payment not completed", { status: 400 });
      }

      const supabase = createClient(supabaseUrl, supabaseServiceRoleKey);

      const { data, error } = await supabase
        .from("profiles")
        .update({ premium: true })
        .eq("id", userId)
        .select("id, email, premium");

      if (error) {
        console.error("Failed updating premium:", error);
        return new Response("Failed updating premium", { status: 500 });
      }

      if (!data || data.length === 0) {
        console.error("No profile row matched this userId", { userId });
        return new Response("No matching profile found", { status: 404 });
      }

      console.log("Premium activated", {
        userId,
        updatedRows: data,
      });
    }

    return new Response("ok", { status: 200 });
  } catch (err) {
    console.error("Webhook handler error:", err);
    return new Response("Webhook handler failed", { status: 500 });
  }
});
