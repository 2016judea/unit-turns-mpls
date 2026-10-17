// POST /api/checkout -> { clientSecret } for Stripe embedded Checkout.
// One fixed price, once, for the full list (README "## Price"). The buyer's password is
// minted here so it can ride in the invoice footer (Stripe's own invoice email is a
// second copy of it). Ported from buying-window / msp-house-index.
const { SITE, PRODUCT, stripe, newPassword } = require("./_lib");
const meta = require("../data/free.json");

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });
  try {
    const { nonce, password } = newPassword();
    const b = typeof req.body === "object" && req.body ? req.body : {};
    const token = /^[a-z0-9]{6,16}$/.test(b.token || "") ? b.token : "";   // a /for/<token>/ page
    const s = await stripe("checkout/sessions", {
      method: "POST",
      form: {
        ui_mode: "embedded_page",
        mode: "payment",
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": String(meta.price_usd * 100),
        "line_items[0][price_data][product_data][name]": `${meta.name}: the full list`,
        "line_items[0][price_data][product_data][description]": meta.checkout_line,
        "payment_method_types[0]": "card",
        "payment_method_types[1]": "link",
        customer_creation: "always",
        "invoice_creation[enabled]": "true",
        "invoice_creation[invoice_data][description]": `${meta.name}: the full list`,
        "invoice_creation[invoice_data][custom_fields][0][name]": "Password",
        "invoice_creation[invoice_data][custom_fields][0][value]": password,
        "invoice_creation[invoice_data][custom_fields][1][name]": "List",
        "invoice_creation[invoice_data][custom_fields][1][value]": SITE.replace("https://", ""),
        "invoice_creation[invoice_data][footer]": `Your password: ${password}. Open the full list at ${SITE}/?pw=${password}. Brick & Mortar · aidan@brickandmortar.dev`,
        "invoice_creation[invoice_data][metadata][product]": PRODUCT,
        "metadata[product]": PRODUCT,
        "metadata[pw_nonce]": nonce,
        "metadata[password]": password,
        "metadata[token]": token,
        "payment_intent_data[metadata][product]": PRODUCT,
        "payment_intent_data[metadata][pw_nonce]": nonce,
        "payment_intent_data[description]": `${meta.name}: the full list`,
        return_url: `${SITE}/${token ? `for/${token}/` : ""}?paid={CHECKOUT_SESSION_ID}`,
      },
    });
    res.status(200).json({ clientSecret: s.client_secret });
  } catch (e) {
    console.error("[checkout]", e.message);
    res.status(502).json({ error: "Checkout could not start. Please try again in a minute." });
  }
};
