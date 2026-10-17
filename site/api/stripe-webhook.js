// POST /api/stripe-webhook  (checkout.session.completed)
// Emails the buyer their password even if they closed the tab. Signature verified
// against STRIPE_WEBHOOK_SECRET (comma-separated for a live + a test endpoint).
// A non-2xx makes Stripe retry, so a failed send is retried for up to three days.
const crypto = require("crypto");
const { sendPasswordOnce, PRODUCT } = require("./_lib");

const raw = (req) => new Promise((ok, no) => { const c = []; req.on("data", (d) => c.push(d)); req.on("end", () => ok(Buffer.concat(c))); req.on("error", no); });

function verify(body, header, secrets) {
  const parts = Object.fromEntries(String(header || "").split(",").map((kv) => kv.split("=")).filter((p) => p[0] === "t"));
  const sigs = String(header || "").split(",").filter((kv) => kv.startsWith("v1=")).map((kv) => kv.slice(3));
  const t = parts.t;
  if (!t || Math.abs(Date.now() / 1000 - Number(t)) > 600) return false;
  return secrets.some((sec) => {
    const want = crypto.createHmac("sha256", sec).update(`${t}.${body}`).digest("hex");
    return sigs.some((s) => s.length === want.length && crypto.timingSafeEqual(Buffer.from(s), Buffer.from(want)));
  });
}

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).end();
  const body = await raw(req);
  const secrets = String(process.env.STRIPE_WEBHOOK_SECRET || "").split(",").filter(Boolean);
  if (!verify(body.toString("utf8"), req.headers["stripe-signature"], secrets)) return res.status(400).json({ error: "bad signature" });
  const ev = JSON.parse(body.toString("utf8"));
  const s = ev.data?.object;
  // Stripe caps an account at 16 live webhook endpoints (hit 2026-10-17), so sibling
  // products with no endpoint of their own are relayed from here: the same body and
  // signature, which they verify with this endpoint's secret (set as their
  // STRIPE_WEBHOOK_SECRET). A non-2xx from them makes Stripe retry this event.
  const fwd = JSON.parse(process.env.WEBHOOK_FORWARD || "{}")[s?.metadata?.product];
  if (ev.type === "checkout.session.completed" && fwd) {
    const r = await fetch(fwd, { method: "POST", headers: { "content-type": "application/json", "stripe-signature": req.headers["stripe-signature"] }, body });
    return res.status(r.ok ? 200 : 502).json({ forwarded: s.metadata.product, status: r.status });
  }
  if (ev.type !== "checkout.session.completed" || s?.metadata?.product !== PRODUCT) return res.status(200).json({ ignored: true });
  try {
    const r = await sendPasswordOnce(s, { who: "webhook" });
    res.status(200).json(r);
  } catch (e) {
    console.error("[webhook]", e.message);
    res.status(500).json({ error: e.message });
  }
};

module.exports.config = { api: { bodyParser: false } };
