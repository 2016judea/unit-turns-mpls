# Unit Turns

**Live:** https://unit-turns-mpls.vercel.app

Every Minneapolis property manager, ranked by the rental units they run, with the
contact the city has on file for each licence. Plus St. Paul owners of record, and the
apartment buildings in both cities that sold in the last year (a new owner turns units).

For painters, cleaners and turnover crews who sell unit turns to property managers.
The first two it was built for wrote it in their own posts: *"I partner with property
management groups to complete their unit turns"* and *"Are slow unit turnovers costing
you rental income?"*

## What's free, what's paid, and why

| free (on the page, no login) | paid ($5, once) |
|---|---|
| the count of managers, units and sales; the map of every building | **every manager's licence contact: name, phone, email** |
| the top 12 managers by units, their building count and neighbourhoods | **every building behind each manager**, with units, owner of record and licence tier |
| 3 St. Paul owners, 5 recent sales (address, month, price) | **the new owner and current manager behind every sale** |
| | the sort by distance from you, by Tier 3 (problem) buildings, A to Z |
| | the spreadsheet |

The free part answers *is there enough work here?* The paid part is the step the buyer
acts on: *who do I call, and which of their buildings are near me?* Both posts end on
the same verb, call or text, so the contact and the addresses are the wall.

## Price

**$5, once.** Set by Aidan on 2026-10-17 as a hypothesis under test, not a fact. A
tenth of one use would be far higher: one unit-turn repaint is roughly $800–$1,500 of
work, and one manager on this list hands out dozens a year. $5 tests whether price is
what stops a tradesperson from buying at all (msp-house-index drew 10 checkouts and 0
payments at $100). Revise on what the funnel shows: `preview_open`, `checkout_open`,
`paid`, `unlock`.

## Data

`DATA_MODEL.md` is the ideal model, written first, and the field-by-field check
against reality. Sources:

- City of Minneapolis **Active Rental Licenses** (ArcGIS, live): units, manager
  (applicant) contact, owner, tier. A manager is grouped by the email domain on its
  licences, so one firm is one row. Under 10 units and short-term rentals are left out.
- City of St. Paul **Certificate of Occupancy, Residential**, 3+ units. The city
  stopped updating it on 2025-07-01 and it names no manager.
- Hennepin and Ramsey County **parcels** (owner of record, sale month and price), read
  from the bricks county snapshots.

Minnesota public data may be reused and sold (AG op. 852, 1995).

## The paywall

`site/` ships only the free slice (`site/data/free.json`, inlined in `site/index.html`).
`pipeline/build.py` writes every row to `private/bundle/full.json.gz` (gitignored);
`scripts/deploy.py` uploads it as `api/_full/`, read only by `/api/data`. Ported from
buying-window and msp-house-index.

| route | does |
|---|---|
| `POST /api/checkout` | Stripe embedded Checkout, $5; mints the buyer's password (nonce + HMAC under `ACCESS_SECRET`) into the session metadata and the invoice footer |
| `POST /api/stripe-webhook` | `checkout.session.completed`: emails the password (Mailgun), once per session, and emails Aidan a sale notice |
| `GET /api/session-status` | the return page: paid or not; sends the password if the webhook has not |
| `GET /api/data` | password in `x-password`: 401 without one, 402 if unpaid, else every row |

Vercel env: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `ACCESS_SECRET`,
`MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAILGUN_FROM`, `SITE_URL`. A lost password:
`python3 scripts/fulfil.py <session_id>`; every sale: `--recent`; a free copy:
`--comp "<label>"`. Analytics: Vercel Web Analytics + PostHog (`kit/head_analytics.html`).

## Run it

```
python3 pipeline/pull.py          # live city sources -> pipeline/cache/
python3 pipeline/build.py         # free slice + private bundle
python3 scripts/build_for.py      # /for/<token>/ pages from outreach/round1/ledger.csv (local)
python3 -m pytest -q tests        # the free slice leaks nothing paid
VERCEL_TOKEN=... python3 scripts/deploy.py
```

`site/index.html` is generated from `kit/template.html`; edit the template or the build.

## Licence

MIT.
