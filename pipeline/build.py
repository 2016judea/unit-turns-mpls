#!/usr/bin/env python3
"""Build Unit Turns: Twin Cities rental managers ranked by units, plus recently sold multifamily.

Inputs (pipeline/cache/, gitignored; refresh with pull.py):
  rental.json     Minneapolis Active Rental Licenses, every field (city ArcGIS, live)
  stp_cofo.json   St. Paul Certificate of Occupancy, residential 3+ units (frozen 2025-07-01)
  Hennepin + Ramsey parcels (owner, sale month, sale price) from bricks' county snapshots.

Writes site/index.html + site/data/free.json (the free slice) and private/bundle/full.json.gz
(everything), via kit/publish.py. Every number on the page is computed here.
"""
import collections, datetime as dt, json, re, sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kit"))
from publish import publish  # noqa: E402

C = ROOT / "pipeline/cache"
PRODUCT = json.loads((ROOT / "product.json").read_text())
BRICKS = Path.home() / "Desktop/bricks/data"
SALES_FROM = "202507"   # twelve months back from the parcel snapshot's last sale month
MIN_UNITS = 10          # a manager under this is a small landlord, not a turn account
FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "comcast.net", "msn.com",
            "live.com", "me.com", "q.com", "usfamily.net", "protonmail.com", "ymail.com", "mail.com", "att.net",
            "earthlink.net", "frontiernet.net", "charter.net", "mac.com", "proton.me", "googlemail.com",
            "centurylink.net", "hotmail.co", "msn", "outlook"}


def title(s):
    s = re.sub(r"\s+", " ", (s or "").strip())
    out = []
    for w in s.split(" "):
        if re.match(r"^\d+(st|nd|rd|th)$", w, re.I): out.append(w.lower())
        elif re.match(r"^(\d|[NSEW]{1,2}$|LLC$|LLLP$|LP$|II$|III$|PHA$|MPHA$)", w, re.I): out.append(w.upper())
        else: out.append(w.capitalize())
    return " ".join(out)


def phone(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1": d = d[1:]
    return f"{d[:3]}-{d[3:6]}-{d[6:]}" if len(d) == 10 else ""


def units(r):
    try: return int(float(r["licensedUnits"] or 0))
    except ValueError: return 0


def domain(e):
    m = re.search(r"@([\w.-]+\.[a-z]{2,})$", (e or "").strip().lower())
    return m.group(1) if m else ""


# ---------------- Minneapolis managers
lic = [r for r in json.loads((C / "rental.json").read_text())
       if not (r["category"] or "").startswith("ShrtTrm") and r["latitude"]]
groups = collections.defaultdict(list)
for r in lic:
    d = domain(r["applicantEmail"])
    key = ("firm", d) if d and d not in FREEMAIL else ("person", re.sub(r"\W+", " ", (r["applicantName"] or "").upper()).strip())
    if key[1]:
        groups[key].append(r)

items, points = [], []
mpls_units = sum(units(r) for r in lic)


def size_group(u):
    return "Managers, 100+ units" if u >= 100 else "Managers, 20–99 units" if u >= 20 else "Managers, 10–19 units"


for (kind, k), rs in groups.items():
    u = sum(units(r) for r in rs)
    if u < MIN_UNITS:
        continue
    names = collections.Counter(title(r["applicantName"]) for r in rs if r["applicantName"])
    t = k if kind == "firm" else title(rs[0]["applicantName"])
    contacts = collections.Counter((title(r["applicantName"]), phone(r["applicantPhone"]), (r["applicantEmail"] or "").strip().lower()) for r in rs)
    top = [c for c, _ in contacts.most_common(3) if c[1] or c[2]]
    hoods = collections.Counter(r["neighborhoodDesc"] for r in rs if r["neighborhoodDesc"])
    t3 = sum(1 for r in rs if r["tier"] == "Tier 3")
    bl = sorted(rs, key=lambda r: -units(r))
    g = size_group(u)
    it = {
        "id": f"m:{k}"[:60], "g": g, "t": t, "tag": f"{u:,} units", "hot": u >= 100,
        "m": [f"{len(rs)} building{'s' if len(rs) != 1 else ''}", "Minneapolis", "Mostly " + ", ".join(h for h, _ in hoods.most_common(2)) if hoods else "",
              f"{t3} Tier 3 (problem) building{'s' if t3 != 1 else ''}" if t3 else ""],
        "w": ("Firm, by the email domain on its licences. Contact on file: " + ", ".join(n for n, _ in names.most_common(2))) if kind == "firm" else "Manager or owner named on the licences",
        "lat": round(bl[0]["latitude"], 4), "lon": round(bl[0]["longitude"], 4),
        "k": {"units": -u, "t3": -t3, "name": t.lower()},
        "c": "<br>".join(" · ".join(x for x in [n, f'<a href="tel:{p}">{p}</a>' if p else "", " ".join(f'<a href="mailto:{x}">{x}</a>' for x in re.split(r"[;,\s]+", e) if "@" in x) if e else ""] if x) for n, p, e in top),
        "rows_label": f"All {len(rs)} building{'s' if len(rs) != 1 else ''}",
        "rows": [{"a": title(r["address"]), "m": f"{units(r)} units · {r['neighborhoodDesc'] or ''} · {r['tier'] or ''} · owner {title(r['ownerName'])}",
                  "lat": round(r["latitude"], 5), "lon": round(r["longitude"], 5)} for r in bl],
        "csv": [[g, t, n, p, e, title(r["address"]), units(r), r["neighborhoodDesc"] or "", title(r["ownerName"]), r["tier"] or "", "", ""]
                for r in bl for (n, p, e) in [top[0] if top else ("", "", "")]],
    }
    items.append(it)
    for r in rs:
        points.append([round(r["latitude"], 3), round(r["longitude"], 3), g])
managers = [i for i in items]

# ---------------- St. Paul owners of record (no manager published)
stp = json.loads((C / "stp_cofo.json").read_text())
rcon = duckdb.connect(str(BRICKS / "ramsey_gis.duckdb"), read_only=True)
rown = {p: (o, sd, sp) for p, o, sd, sp in rcon.execute("select pin, owner, sale_date, sale_price from parcels").fetchall()}
og = collections.defaultdict(list)
for x in stp:
    o = (rown.get(x["PIN"] or "") or (None,))[0]
    if o and x["LATITUE"]:
        og[o].append(x)
stp_items = []
for o, xs in og.items():
    u = sum(x["UNITS"] or 0 for x in xs)
    if u < MIN_UNITS:
        continue
    xs.sort(key=lambda x: -(x["UNITS"] or 0))
    stp_items.append({
        "id": f"s:{o}"[:60], "g": "St. Paul owners", "t": title(o), "tag": f"{u:,} units", "hot": u >= 100,
        "m": [f"{len(xs)} building{'s' if len(xs) != 1 else ''}", "St. Paul", (title(xs[0]["PROPNAME"]) if xs[0]["PROPNAME"] else "")],
        "w": "Owner of record (Ramsey County). St. Paul publishes no manager or contact.",
        "lat": round(float(xs[0]["LATITUE"]), 4), "lon": round(float(xs[0]["LONGITUTE"]), 4),
        "k": {"units": -u, "t3": 0, "name": o.lower()},
        "rows_label": f"All {len(xs)} building{'s' if len(xs) != 1 else ''}",
        "rows": [{"a": title(x["ADDRESS"]), "m": f"{x['UNITS']} units · {title(x['PROPNAME'] or '')} · C of O grade {x['GRADE'] or '?'}",
                  "lat": round(float(x["LATITUE"]), 5), "lon": round(float(x["LONGITUTE"]), 5)} for x in xs],
        "csv": [["St. Paul owners", title(o), "", "", "", title(x["ADDRESS"]), x["UNITS"], "", title(o), "C of O grade " + (x["GRADE"] or ""), "", ""] for x in xs],
    })
    for x in xs:
        points.append([round(float(x["LATITUE"]), 3), round(float(x["LONGITUTE"]), 3), "St. Paul owners"])
items += stp_items

# ---------------- recently sold multifamily (new owner = owner of record now)
by_apn = collections.defaultdict(list)
for r in lic:
    if r["apn"]: by_apn[r["apn"]].append(r)
mgr_of = {}
for (kind, k), rs in groups.items():
    for r in rs:
        mgr_of[r["licenseNumber"]] = (k if kind == "firm" else title(r["applicantName"]), title(r["applicantName"]), phone(r["applicantPhone"]), (r["applicantEmail"] or "").lower())
hcon = duckdb.connect(str(BRICKS / "hennepin_gis.duckdb"), read_only=True)
sales = hcon.execute(f"""select pin, sale_date, sale_price, owner, addr_house, addr_street, PR_TYP_NM1, lat, lon from parcels
  where munic='MINNEAPOLIS' and sale_date >= '{SALES_FROM}' and PR_TYP_NM1 in ('APARTMENT','TRIPLEX','LOW INCOME RENTAL')
  and sale_price >= 50000 and lat is not null""").fetchall()
sales += [("R" + p, sd, sp, o, h, s, "St. Paul " + (uc or ""), la, lo) for p, sd, sp, o, h, s, uc, la, lo in rcon.execute(f"""
  select pin, sale_date, sale_price, owner, addr_house, addr_street, USECLASS1, lat, lon from parcels
  where munic ilike 'saint paul%' and sale_date >= '{SALES_FROM}' and USECLASS1 ilike '4A APARTMENT%' and sale_price >= 50000 and lat is not null""").fetchall()]
last_sale = max(s[1] for s in sales)
sale_items = []
seen = set()
for pin, sd, sp, o, h, s, typ, la, lo in sorted(sales, key=lambda x: (x[1], x[2]), reverse=True):
    addr = title(f"{h or ''} {s or ''}")
    if (addr, sd) in seen: continue
    seen.add((addr, sd))
    lr = by_apn.get(pin, [])
    u = sum(units(r) for r in lr)
    mg = mgr_of.get(lr[0]["licenseNumber"]) if lr else None
    month = dt.date(int(sd[:4]), int(sd[4:6]), 1).strftime("%b %Y")
    city = "St. Paul" if str(pin).startswith("R") else "Minneapolis"
    sale_items.append({
        "id": f"x:{pin}", "g": "Sold since July 2025", "t": addr, "tag": f"Sold {month}", "hot": sd >= f"{last_sale[:4]}{int(last_sale[4:])-2:02d}",
        "m": [city, f"${sp:,.0f}", f"{u} licensed units" if u else (typ or "").replace("St. Paul ", "").title()],
        "w": "",
        "lat": round(la, 4), "lon": round(lo, 4),
        "k": {"units": -(u or 0), "t3": 0, "name": addr.lower(), "date": -int(sd)},
        "c": f"New owner of record: <b>{title(o)}</b>" + (f" · licence manager: {mg[0]} ({' · '.join(x for x in mg[1:] if x)})" if mg else ""),
        "csv": [["Sold since July 2025", mg[0] if mg else "", mg[1] if mg else "", mg[2] if mg else "", mg[3] if mg else "", addr, u or "", "", title(o), "", month, sp]],
    })
    points.append([round(la, 3), round(lo, 3), "Sold since July 2025"])
items += sale_items

# ---------------- free slice
points = [list(p) for p in sorted({tuple(p) for p in points})]
items.sort(key=lambda i: i["k"]["units"])
mg = sorted(managers, key=lambda i: i["k"]["units"])
free_items = []
for i in mg[:12] + sorted(stp_items, key=lambda i: i["k"]["units"])[:3] + sale_items[:5]:
    f = {k: v for k, v in i.items() if k not in ("c", "csv", "rows")}
    if i["g"] == "Sold since July 2025":
        f["rows_locked"] = "New owner and manager in the full list"
    elif i["g"] == "St. Paul owners":
        f["rows_locked"] = f"{len(i['rows'])} addresses in the full list"
    else:
        f["rows_locked"] = f"{len(i['rows'])} addresses and the licence contact in the full list"
    if i["g"].startswith("Managers"):
        f["w"] = "Firm, by the email domain on its licences" if i["w"].startswith("Firm") else i["w"]
    free_items.append(f)

gc = collections.Counter(i["g"] for i in items)
n100 = gc["Managers, 100+ units"]
big_units = sum(-i["k"]["units"] for i in managers if i["g"] == "Managers, 100+ units")
ORDER = ["Managers, 100+ units", "Managers, 20–99 units", "Managers, 10–19 units", "St. Paul owners", "Sold since July 2025"]
built = dt.date.today().isoformat()
total_mgr = len(managers)
free = {
    "built": built,
    "eyebrow": f"Unit Turns · Minneapolis and St. Paul rental licences · built {dt.date.today():%b %-d, %Y}",
    "h1": f"{total_mgr} Minneapolis property managers, ranked by the units they turn",
    "lede": (f"Every rental in Minneapolis carries a city licence that names the manager the city calls. "
             f"Grouped by firm, <b>{n100} managers run 100 units or more, {big_units:,} units between them.</b> "
             f"Plus {len(stp_items)} St. Paul owners with 10+ units, and {len(sale_items)} apartment buildings that sold since July 2025, "
             f"where a new owner is about to turn units."),
    "stats": [[f"{total_mgr}", "managers with 10+ units"], [f"{mpls_units:,}", "licensed Minneapolis units"], [f"{len(sale_items)}", "apartment buildings sold since Jul 2025"]],
    "pay_h": f"The full list: all {len(items):,}, with who to call",
    "pay_line": ("Every manager's contact from the licence (name, phone, email), every building with its units, owner and condition tier, "
                 "the new owner behind every sale, the sort by distance from you, and the spreadsheet."),
    "checkout_line": f"{total_mgr} Twin Cities rental managers with licence contacts, {len(stp_items)} St. Paul owners, {len(sale_items)} recent multifamily sales.",
    "noun": "managers, owners and sales",
    "ghost": "Jane Smith · 612-555-0100 · jane@example.com · 14 buildings",
    "total": len(items),
    "group_counts": {g: gc[g] for g in ORDER},
    "group_order": ORDER,
    "legend": [["Managers, 100+ units", "var(--hot)", "100+ units"], ["Managers, 20–99 units", "var(--accent)", "20–99"],
               ["Managers, 10–19 units", "var(--mid)", "10–19"], ["St. Paul owners", "var(--stp)", "St. Paul"], ["Sold since July 2025", "var(--sold)", "Sold"]],
    "points": points,
    "sorts": [{"key": "units", "label": "Most units"}, {"key": "near", "label": "Closest to", "near": True, "paid": True},
              {"key": "t3", "label": "Most Tier 3 (problem) buildings", "paid": True}, {"key": "name", "label": "A to Z", "paid": True}],
    "origins": [["Anoka", 45.1977, -93.3872], ["Saint Paul", 44.9537, -93.0900], ["Downtown Minneapolis", 44.9778, -93.2650],
                ["Brooklyn Park", 45.0941, -93.3563], ["Bloomington", 44.8408, -93.2983], ["Uptown", 44.9489, -93.2985]],
    "csv_cols": ["group", "manager or owner", "contact", "phone", "email", "building", "units", "neighborhood", "owner of record", "licence tier / grade", "sold", "sale price"],
    "items": free_items,
    "note": (f"<p>Sources: City of Minneapolis Active Rental Licenses (live, pulled {built}); St. Paul Certificate of Occupancy, residential 3+ units "
             f"(the city stopped updating it on Jul 1, 2025); Hennepin and Ramsey County parcel records for owner of record and sale month and price "
             f"(snapshot through {dt.date(int(last_sale[:4]), int(last_sale[4:]), 1):%B %Y}).</p>"
             f"<p>A manager is grouped by the email domain on its licences, so one firm is one row. Individuals with under {MIN_UNITS} units and short-term rentals are left out. "
             f"No public record says how many units are turning this month or who does a firm's turns today, so units stand in for turn volume.</p>"
             f"<p>The contact is the one the city has on file for the licence. Made by Aidan Jude at Brick &amp; Mortar (aidan@brickandmortar.dev).</p>"),
}
publish(ROOT, PRODUCT, free, {"items": items})
print(f"managers {total_mgr} (100+: {n100}, {big_units:,} units) · stp owners {len(stp_items)} · sales {len(sale_items)} · mpls units {mpls_units:,} · last sale {last_sale}")
