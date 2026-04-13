import { createClient } from "npm:@supabase/supabase-js@2";
import Stripe from "npm:stripe@17";

const stripeSecretKey = Deno.env.get("STRIPE_SECRET_KEY");
const supabaseUrl = Deno.env.get("SUPABASE_URL");
const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY");
const appUrl = Deno.env.get("APP_URL");
const stripePriceId = Deno.env.get("STRIPE_PRICE_ID");

if (!stripeSecretKey) throw new Error("Missing STRIPE_SECRET_KEY");
if (!supabaseUrl) throw new Error("Missing SUPABASE_URL");
if (!supabaseAnonKey) throw new Error("Missing SUPABASE_ANON_KEY");
if (!appUrl) throw new Error("Missing APP_URL");
if (!stripePriceId) throw new Error("Missing STRIPE_PRICE_ID");

const stripe = new Stripe(stripeSecretKey, {
  apiVersion: "2023-10-16",
});

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ error: "Method not allowed" }),
      { status: 405, headers: corsHeaders }
    );
  }

  try {
    const authHeader = req.headers.get("Authorization");

    if (!authHeader?.startsWith("Bearer ")) {
      return new Response(
        JSON.stringify({ error: "Missing auth token" }),
        { status: 401, headers: corsHeaders }
      );
    }

    const token = authHeader.replace("Bearer ", "").trim();

    const supabase = createClient(supabaseUrl, supabaseAnonKey);

    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser(token);

    if (userError || !user) {
      console.error("getUser failed:", userError);
      return new Response(
        JSON.stringify({ error: "Invalid JWT" }),
        { status: 401, headers: corsHeaders }
      );
    }

    const userId = user.id;
    const userEmail = user.email ?? "";

    console.log("Authenticated user:", {
      userId,
      userEmail,
    });

    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      customer_email: userEmail || undefined,
      line_items: [
        {
          price: stripePriceId,
          quantity: 1,
        },
      ],
      success_url: `${appUrl}/?premium_success=1&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${appUrl}/premium.html?canceled=1`,
      metadata: {
        supabase_user_id: userId,
        user_email: userEmail,
        product: "bj_trainer_premium",
      },
    });

    console.log("Checkout session created:", {
      sessionId: session.id,
      userId,
      userEmail,
      metadata: session.metadata,
    });

    return new Response(
      JSON.stringify({ url: session.url }),
      { status: 200, headers: corsHeaders }
    );
  } catch (err) {
    console.error("create-checkout error:", err);

    return new Response(
      JSON.stringify({
        error:
          err instanceof Error
            ? err.message
            : "Failed to create checkout session",
      }),
      { status: 500, headers: corsHeaders }
    );
  }
});
