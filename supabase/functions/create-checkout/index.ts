import { createClient } from "npm:@supabase/supabase-js@2";
import Stripe from "npm:stripe@17";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
  apiVersion: "2023-10-16",
});

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: corsHeaders,
    });
  }

  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader?.startsWith("Bearer ")) {
      return new Response(JSON.stringify({ error: "Missing auth token" }), {
        status: 401,
        headers: corsHeaders,
      });
    }

    const token = authHeader.replace("Bearer ", "").trim();

   const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SB_PUBLISHABLE_KEY")!
);

    const { data: claimsData, error: claimsError } = await supabase.auth.getClaims(token);

    if (claimsError || !claimsData?.claims?.sub) {
      return new Response(JSON.stringify({ error: "Invalid JWT" }), {
        status: 401,
        headers: corsHeaders,
      });
    }

    const userId = claimsData.claims.sub as string;
    const userEmail =
      typeof claimsData.claims.email === "string" ? claimsData.claims.email : undefined;

    const appUrl = Deno.env.get("APP_URL")!;

    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      customer_email: userEmail,
      line_items: [
        {
          price: Deno.env.get("STRIPE_PRICE_ID")!,
          quantity: 1,
        },
      ],
      success_url: `${appUrl}/?premium_success=1`,
      cancel_url: `${appUrl}/premium.html?canceled=1`,
      metadata: {
        supabase_user_id: userId,
        user_email: userEmail ?? "",
        product: "bj_trainer_premium",
      },
    });

    return new Response(JSON.stringify({ url: session.url }), {
      status: 200,
      headers: corsHeaders,
    });
  } catch (err) {
    console.error("create-checkout error:", err);
    return new Response(
      JSON.stringify({ error: err instanceof Error ? err.message : "Failed to create checkout session" }),
      {
        status: 500,
        headers: corsHeaders,
      }
    );
  }
});
