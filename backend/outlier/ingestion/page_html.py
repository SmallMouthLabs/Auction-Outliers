"""Best-effort parser for a saved ShopGoodwill item page (File > Save Page As, or the bookmarklet payload).

This is a permitted, user-initiated capture of a page the user is already viewing. The layout could not be
verified from this environment, so extraction relies on generic signals: <title>, og:/meta tags, JSON-LD,
image URLs, and labeled text ('Current Price', 'Bids', 'Ends', 'Shipping').
"""
from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from ..services.listings import ListingIn, extract_sgw_item_id
from .common import clean_text, parse_datetime, parse_int, parse_price

IMG_HOST_RE = re.compile(r"https?://[^\s\"']*(?:shopgoodwill|azureedge|cloudfront|blob\.core)[^\s\"']*\.(?:jpe?g|png|webp)(?:\?[^\s\"']*)?", re.IGNORECASE)
LABELS = {
    "current_bid": [r"current (?:bid|price)[:\s]+\$?([\d,]+\.?\d*)", r"price[:\s]+\$([\d,]+\.?\d*)"],
    "num_bids": [r"(\d+)\s*bids?"],
    "ends_at": [r"(?:ends?|ending|closes?)[:\s]+([A-Za-z0-9/,: ]+?(?:AM|PM|am|pm))"],
    "shipping_cost": [r"shipping[:\s]+\$([\d,]+\.?\d*)"],
    "handling_fee": [r"handling[:\s]+\$([\d,]+\.?\d*)"],
    "seller": [r"seller[:\s]+([A-Za-z0-9 .&'\-]{3,60})"],
    "category": [r"category[:\s]+([A-Za-z0-9 >&'\-/]{3,80})"],
}


def _first(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def parse_item_page(html: str, url: str | None = None) -> ListingIn:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        if t.name == "script" and t.get("type") == "application/ld+json":
            continue
        t.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    title = None
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"]
    if not title and soup.title and soup.title.string:
        title = soup.title.string
    h1 = soup.find("h1")
    if h1 and len(h1.get_text(strip=True)) > 5:
        title = h1.get_text(" ", strip=True)
    title = clean_text(title) or "Untitled listing"
    title = re.sub(r"\s*[|\-]\s*shopgoodwill.*$", "", title, flags=re.IGNORECASE)

    desc = None
    ld: dict[str, Any] = {}
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(s.string or "")
            if isinstance(d, dict):
                ld.update(d)
        except Exception:  # noqa: BLE001
            continue
    md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
    if md and md.get("content"):
        desc = md["content"]
    if ld.get("description"):
        desc = ld["description"]
    images: list[str] = []
    for u in IMG_HOST_RE.findall(html):
        if u not in images and "thumb" not in u.lower():
            images.append(u)
    for im in soup.find_all("img", src=True):
        src = im["src"]
        if src.startswith("http") and src not in images and re.search(r"\.(jpe?g|png|webp)", src, re.IGNORECASE):
            images.append(src)
    ogi = soup.find("meta", property="og:image")
    if ogi and ogi.get("content") and ogi["content"] not in images:
        images.insert(0, ogi["content"])

    url = url or (soup.find("link", rel="canonical") or {}).get("href") or (soup.find("meta", property="og:url") or {}).get("content")
    item_id = extract_sgw_item_id(url)
    return ListingIn(
        source="page_html", source_item_id=item_id, source_url=url if (url and url.startswith("http")) else None,
        extraction_method="saved_page_parse", title=title[:500], description=clean_text(desc),
        category=clean_text(_first(LABELS["category"], text)), seller=clean_text(_first(LABELS["seller"], text)),
        current_bid=parse_price(_first(LABELS["current_bid"], text)), num_bids=parse_int(_first(LABELS["num_bids"], text)),
        ends_at=parse_datetime(_first(LABELS["ends_at"], text)), shipping_cost=parse_price(_first(LABELS["shipping_cost"], text)),
        handling_fee=parse_price(_first(LABELS["handling_fee"], text)), image_urls=images[:20],
        raw={"ld_json_keys": list(ld.keys())[:20], "text_excerpt": text[:800]},
    )
