"""Write the public free slice and the private full bundle from one build.

    site/public/index.html        the page, free sample inlined (generated: edit kit/template.html)
    site/public/data/free.json    the same free slice, read by api/checkout.js for the price
    private/bundle/full.json.gz   every row; uploaded as api/_full/ by scripts/deploy.py

A paid field must never reach site/public/: check_free() fails the build if one does.
Only site/public/ is static on Vercel (vercel.json outputDirectory). With "." the whole
upload was static, and api/_full/full.json.gz was downloadable at a URL-encoded path
(/api/%5Ffull/full.json.gz) that the redirect never saw (found 2026-10-18).
"""
import gzip, html, json
from pathlib import Path

PK = "pk_live_51TUvvcBzD4mN8eOD28H6oQkFwFHwF1SLtWxN1vHRmnSxntWFefgd33mEIVmjv8ekxWgkZft3OpPlzmVXMIeHPBwj003998hjTf"  # Brick and Mortar Stripe account
HEAD = Path(__file__).with_name("head_analytics.html")
TPL = Path(__file__).with_name("template.html")

def esc(s):
    """HTML-escape a value from a public record before it goes into a 'c' field, which the page
    renders with innerHTML. Names, emails, owners and addresses come off city, county and state
    feeds unescaped; one '<' in an applicant name would otherwise run as markup on every page."""
    return html.escape("" if s is None else str(s), quote=True)


def check_free(free, paid_keys):
    blob = json.dumps(free)
    for it in free["items"]:
        for k in paid_keys:
            assert not it.get(k), f"paid field {k} leaked into the free slice: {it.get('id')}"
    return blob


def publish(root, product, free, full, paid_keys=("c", "csv", "rows")):
    root = Path(root)
    free = {**free, "slug": product["slug"], "name": product["name"], "price_usd": product["price_usd"], "stripe_pk": PK}
    check_free(free, paid_keys)
    (root / "site/public/data").mkdir(parents=True, exist_ok=True)
    (root / "site/public/data/free.json").write_text(json.dumps(free, separators=(",", ":")))
    head = HEAD.read_text().replace('S="buying-window"', f'S="{product["slug"]}"')
    h = TPL.read_text()
    for k, v in {"__TITLE__": product["title"], "__DESC__": product["desc"], "__FONTS__": product["fonts"],
                 "__LIGHT__": product["light"], "__DARK__": product["dark"], "__HEAD_ANALYTICS__": head}.items():
        h = h.replace(k, v)
    h = h.replace("__DATA__", json.dumps(free, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    (root / "site/public/index.html").write_text(h)
    (root / "private/bundle").mkdir(parents=True, exist_ok=True)
    (root / "private/bundle/full.json.gz").write_bytes(gzip.compress(json.dumps(full, separators=(",", ":")).encode(), 9, mtime=0))
    print(f"  free: {len(free['items'])} items, {len(json.dumps(free))//1024} KB · full: {len(full['items'])} items")
