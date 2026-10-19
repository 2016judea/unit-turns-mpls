#!/usr/bin/env python3
"""The paywall's backup, run by hand. Nothing here emails anyone.

    python3 scripts/fulfil.py cs_live_...        # a buyer lost their password: reprint it
    python3 scripts/fulfil.py --recent           # every session of ours since launch, paid or not
    python3 scripts/fulfil.py --comp "<label>"   # a free password, no Stripe session behind it

Copied from msp-house-index (scripts/fulfil.py + issue_password.py, 2026-10-11). The paid
password lives in the session metadata (minted by site/api/checkout.js) and in the invoice
footer. A comp password's last seven characters are an HMAC of its first five in the
"comp:" domain (site/api/_lib.js checkPassword); the same label always gives the same one.
Reads STRIPE_SECRET_KEY from ~/Desktop/bricks/.env and ACCESS_SECRET from ./.env.
"""
import csv, datetime as dt, hashlib, hmac, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://unit-turns-mpls.vercel.app"
PRODUCT = "unit-turns-mpls"
ALPHA = "23456789BCDFGHJKMNPQRSTVWXYZ"  # same as site/api/_lib.js


def env(path, key):
    for line in Path(path).expanduser().read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{key} missing from {path}")


def chars(b, n):
    return "".join(ALPHA[x % len(ALPHA)] for x in b[:n])


def comp(label):
    s = env(ROOT / ".env", "ACCESS_SECRET").encode()
    nonce = chars(hmac.new(s, ("label:" + label).encode(), hashlib.sha256).digest(), 5)
    raw = nonce + chars(hmac.new(s, ("comp:" + nonce).encode(), hashlib.sha256).digest(), 7)
    log = ROOT / "private/comp_passwords.csv"
    log.parent.mkdir(exist_ok=True)
    new = not log.exists()
    with log.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["issued", "label", "nonce"])
        w.writerow([dt.date.today().isoformat(), label, nonce])
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


S = requests.Session()


def stripe(path):
    S.auth = (env("~/Desktop/bricks/.env", "STRIPE_SECRET_KEY"), "")
    j = S.get(f"https://api.stripe.com/v1/{path}").json()
    if "error" in j:
        sys.exit(f"stripe: {j['error'].get('message')}")
    return j


def sessions(path):
    """Every session, not just the newest 100: Stripe caps a list page at 100 and signals
    the rest with has_more; a bare limit=100 read silently shows the newest hundred only."""
    while True:
        j = stripe(path)
        yield from j["data"]
        if not j.get("has_more") or not j["data"]:
            return
        path = path.split("&starting_after=")[0] + f"&starting_after={j['data'][-1]['id']}"


def show(s):
    m = s.get("metadata") or {}
    print(f"{s['id']}\n  status   {s['status']} / {s['payment_status']}  ${(s.get('amount_total') or 0) / 100:.2f}"
          f"\n  email    {(s.get('customer_details') or {}).get('email')}\n  password {m.get('password')}"
          f"\n  link     {SITE}/?pw={m.get('password')}\n  emailed  {m.get('pw_emailed') or 'NOT YET'}")


if len(sys.argv) < 2:
    sys.exit(__doc__)
arg = sys.argv[1]
if arg == "--recent":
    for s in sessions("checkout/sessions?limit=100&created[gte]=1792000000"):
        if (s.get("metadata") or {}).get("product") == PRODUCT:
            show(s)
elif arg == "--comp":
    if len(sys.argv) < 3 or not sys.argv[2].strip():
        sys.exit(__doc__)
    pw = comp(sys.argv[2].strip())
    print(f"{sys.argv[2]}\n  password {pw}\n  link     {SITE}/?pw={pw}")
else:
    show(stripe(f"checkout/sessions/{arg}"))
