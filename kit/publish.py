"""Write the public free slice and the private full bundle from one build.

    site/index.html        the page, free sample inlined (generated: edit pipeline/template.html)
    site/data/free.json    the same free slice, read by api/checkout.js for the price
    private/bundle/full.json.gz   every row; uploaded as api/_full/ by scripts/deploy.py

A paid field must never reach site/: check_free() fails the build if one does.
"""
import gzip, json
from pathlib import Path

PK = "pk_live_51TUvvcBzD4mN8eOD28H6oQkFwFHwF1SLtWxN1vHRmnSxntWFefgd33mEIVmjv8ekxWgkZft3OpPlzmVXMIeHPBwj003998hjTf"  # Brick and Mortar Stripe account
HEAD = Path(__file__).with_name("head_analytics.html")
TPL = Path(__file__).with_name("template.html")


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
    (root / "site/data").mkdir(parents=True, exist_ok=True)
    (root / "site/data/free.json").write_text(json.dumps(free, separators=(",", ":")))
    head = HEAD.read_text().replace('S="buying-window"', f'S="{product["slug"]}"')
    h = TPL.read_text()
    for k, v in {"__TITLE__": product["title"], "__DESC__": product["desc"], "__FONTS__": product["fonts"],
                 "__LIGHT__": product["light"], "__DARK__": product["dark"], "__HEAD_ANALYTICS__": head}.items():
        h = h.replace(k, v)
    h = h.replace("__DATA__", json.dumps(free, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    (root / "site/index.html").write_text(h)
    (root / "private/bundle").mkdir(parents=True, exist_ok=True)
    (root / "private/bundle/full.json.gz").write_bytes(gzip.compress(json.dumps(full, separators=(",", ":")).encode(), 9, mtime=0))
    print(f"  free: {len(free['items'])} items, {len(json.dumps(free))//1024} KB · full: {len(full['items'])} items")
