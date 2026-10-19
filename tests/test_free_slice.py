"""The free slice must never carry what the $5 buys: contacts, address lists, CSV rows.
And the paid bundle must never be a URL."""
import datetime as dt, gzip, json, re, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kit"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipeline"))
FREE = ROOT / "site/public/data/free.json"
PAGE = ROOT / "site/public/index.html"
BUNDLE = ROOT / "private/bundle/full.json.gz"


def test_free_slice_has_no_paid_fields():
    free = json.loads(FREE.read_text())
    for it in free["items"]:
        assert not it.get("c") and not it.get("csv") and not it.get("rows"), it["id"]
    blob = json.dumps(free["items"])
    assert "mailto:" not in blob and "tel:" not in blob
    assert not re.search(r"[\w.]+@[\w-]+\.(com|org|net)", blob)


def test_page_carries_analytics_and_free_data_only():
    html = PAGE.read_text()
    assert "/_vercel/insights/script.js" in html and "posthog.init" in html
    assert "mailto:" not in html


def test_only_site_public_is_static_so_the_paid_bundle_is_never_a_url():
    """2026-10-18: with outputDirectory "." every uploaded file was static, and the redirect that
    guarded /api/_full/ matched the raw path only. /api/%5Ffull/full.json.gz, /api/_full%2Ffull.json.gz
    and /api/_full/full.json.gz/ each served the whole paid bundle to anyone, on all three sibling
    products. The bundle is uploaded as api/_full/, which must sit outside the static directory."""
    v = json.loads((ROOT / "site/vercel.json").read_text())
    out = v["outputDirectory"]
    assert out == "public", out
    assert FREE.exists() and PAGE.exists()
    assert (ROOT / "site/api/checkout.js").read_text().count('require("../public/data/free.json")') == 1
    import deploy
    assert str(deploy.BUNDLE).endswith("private/bundle")
    if BUNDLE.exists():
        rels = [str(rel) for rel, _ in deploy.collect()]
        assert "api/_full/full.json.gz" in rels
        assert "public/index.html" in rels and "public/data/free.json" in rels
        assert not any(r.startswith("public/") and "_full" in r for r in rels)


def test_record_text_is_escaped_before_it_becomes_html():
    """Item 'c' is rendered with innerHTML. Applicant names, owners and emails come off the city,
    county and state feeds unescaped ('L&M Property', and one day a '<')."""
    from publish import esc
    assert esc('A&B <Props> "x"') == "A&amp;B &lt;Props&gt; &quot;x&quot;"
    assert esc(None) == ""
    if not BUNDLE.exists():
        pytest.skip("private bundle is not on this machine")
    full = json.loads(gzip.decompress(BUNDLE.read_bytes()))
    strip = lambda c: re.sub(r'<a href="(tel|mailto):[^"]*">|</a>|<br>|</?b>', "", str(c))
    bad = [i["id"] for i in full["items"] if re.search(r"[<>]|&(?!(amp|lt|gt|quot|#x27);)", strip(i.get("c", "")))]
    assert not bad, bad[:5]


def test_page_is_dated_by_the_pull_not_the_build():
    """The note says "pulled <built>". A rebuild on a later day used to move that date (and the
    day-relative windows) off the data it was computed from."""
    free = json.loads(FREE.read_text())
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", free["built"])
    caches = sorted((ROOT / "pipeline/cache").glob("*.json")) if (ROOT / "pipeline/cache").exists() else []
    if not caches:
        pytest.skip("pipeline cache is not on this machine")
    pulled = {dt.date.fromtimestamp(c.stat().st_mtime).isoformat() for c in caches}
    assert free["built"] in pulled, (free["built"], pulled)


def test_recent_sale_flag_survives_a_january_snapshot():
    """hot = sold in the last two months of the parcel snapshot. The old expression
    f"{yyyy}{int(mm)-2:02d}" gave '2026-1' for a January snapshot, and every 2026 sale string
    compares above that while every 2025 sale compares below it."""
    from dates import months_back
    assert months_back("202607", 2) == "202605"
    assert months_back("202601", 2) == "202511"
    assert months_back("202602", 2) == "202512"
    assert months_back("202603", 2) == "202601"
    old = f"{'2026'}{int('01')-2:02d}"
    assert old == "2026-1" and "202601" >= old and not "202512" >= old   # the bug, pinned
    assert "202512" >= months_back("202601", 2) and not "202510" >= months_back("202601", 2)
