#!/usr/bin/env python3
"""Write one /for/<token>/ page per prospect in outreach/round1/ledger.csv.

Each page is site/index.html with the prospect's own post quoted on top and their
origin (for the distance sort) preset. The token sits in the PATH, never ?query or
#hash, because Vercel analytics drops those. site/for/ is gitignored (names stay local)
and deployed from disk by scripts/deploy.py. Run after pipeline/build.py, before deploy.
"""
import csv, html, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "outreach/round1/ledger.csv"
OUT = ROOT / "site/for"
page = (ROOT / "site/index.html").read_text()
shutil.rmtree(OUT, ignore_errors=True)
n = 0
for r in csv.DictReader(LEDGER.open()):
    me = {"token": r["token"], "lead": r.get("lead") or "You wrote", "quote": r["quote"], "url": r["url"],
          "fact": r.get("fact", ""), "origin": r.get("origin", ""), "sort": r.get("sort", "")}
    blob = json.dumps(me, ensure_ascii=False).replace("</", "<\\/")
    out = page.replace("<head>", '<head>\n<meta name="robots" content="noindex">', 1)
    out = out.replace("<body>", f"<body>\n<script>window.FOR={blob};</script>", 1)
    out = out.replace("<title>", f"<title>For {html.escape(r['org'])} · ", 1)
    d = OUT / r["token"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out)
    n += 1
print(f"{n} pages in {OUT}")
