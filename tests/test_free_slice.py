"""The free slice must never carry what the $5 buys: contacts, addresses lists, CSV rows."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_free_slice_has_no_paid_fields():
    free = json.loads((ROOT / "site/data/free.json").read_text())
    for it in free["items"]:
        assert not it.get("c") and not it.get("csv") and not it.get("rows"), it["id"]
    blob = json.dumps(free["items"])
    assert "mailto:" not in blob and "tel:" not in blob
    assert not re.search(r"[\w.]+@[\w-]+\.(com|org|net)", blob)


def test_page_carries_analytics_and_free_data_only():
    html = (ROOT / "site/index.html").read_text()
    assert "/_vercel/insights/script.js" in html and "posthog.init" in html
    assert "mailto:" not in html
