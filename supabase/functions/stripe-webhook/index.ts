import Stripe from "npm:stripe@17";
import { createClient } from "npm:@supabase/supabase-js@2";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
  apiVersion: "2023-10-16",
});

const endpointSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET")!;

Deno.serve(async (req) => {
  const signature = req.headers.get("stripe-signature");
  const body = await req.text();

  if (!signature) {
    console.error("Missing stripe-signature header");
    return new Response("Missing stripe-signature header", { status: 400 });
  }

  let event: Stripe.Event;

  try {
    event = await stripe.webhooks.constructEventAsync(
      body,
      signature,
      endpointSecret
    );
  } catch (err) {
    console.error("Webhook signature error:", err);
    return new Response(
      `Webhook Error: ${err instanceof Error ? err.message : "Unknown error"}`,
      { status: 400 }
    );
  }

  try {
    console.log("Stripe event type:", event.type);

    if (event.type === "checkout.session.completed") {
      const session = event.data.object as Stripe.Checkout.Session;

      console.log("Session metadata:", session.metadata);

      const userId = session.metadata?.supabase_user_id;
      console.log("Resolved userId:", userId);

      if (!userId) {
        console.error("Missing supabase_user_id in metadata");
        return new Response("Missing supabase_user_id", { status: 400 });
      }

      const supabase = createClient(
        Deno.env.get("SUPABASE_URL")!,
        Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
      );

      const { error } = await supabase
        .from("profiles")
        .update({ premium: true })
        .eq("id", userId);

      if (error) {
        console.error("Failed updating premium:", error);
        return new Response("Failed updating premium", { status: 500 });
      }

      console.log(`Premium activated for user ${userId}`);
    }

    return new Response("ok", { status: 200 });
  } catch (err) {
    console.error("Webhook handler error:", err);
    return new Response("Webhook handler failed", { status: 500 });
  }
});
