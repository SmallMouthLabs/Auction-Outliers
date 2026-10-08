"""ShopGoodwill 'Personal Shopper' notification e-mail ingestion (permitted source: your own mailbox).

The parser is deliberately tolerant: it looks for item links (shopgoodwill.com/item/<id>), takes the nearest
title text, price, bid count, end time and thumbnail image around each link. The exact HTML layout of these
e-mails could not be verified from this environment; tune `_block_for_link` if your e-mails differ.
Images in e-mails are thumbnails: upload full-size photos (or add image URLs) before running deep analysis.
"""
from __future__ import annotations

import email
import email.policy
import imaplib
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from ..services.listings import ListingIn
from .common import BIDS_RE, clean_text, parse_datetime, parse_price

log = logging.getLogger(__name__)
ITEM_LINK_RE = re.compile(r"https?://(?:www\.)?shopgoodwill\.com/item/(\d+)[^\s\"'<>]*", re.IGNORECASE)
END_RE = re.compile(r"(?:ends?|ending|end(?:s)? on|closes?)[:\s]+([A-Za-z0-9/,: ]+?(?:AM|PM|am|pm)?)(?:\s*PT)?(?=\s|$|<)", re.IGNORECASE)


def extract_html_from_eml(raw: bytes) -> tuple[str, str]:
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    subject = str(msg.get("subject", ""))
    html, text = "", ""
    for part in msg.walk():
        ctype = part.get_content_type()
        try:
            payload = part.get_content()
        except Exception:  # noqa: BLE001
            continue
        if ctype == "text/html" and not html:
            html = payload
        elif ctype == "text/plain" and not text:
            text = payload
    return subject, html or f"<pre>{text}</pre>"


def _block_for_link(a) -> Any:
    """Walk up from the anchor to a container that likely holds the whole item card."""
    node = a
    for _ in range(6):
        if node.parent is None:
            break
        node = node.parent
        txt = node.get_text(" ", strip=True)
        if ("$" in txt or BIDS_RE.search(txt)) and len(txt) < 1500:
            return node
    return a.parent or a


def parse_personal_shopper_html(html: str, *, subject: str | None = None) -> list[ListingIn]:
    soup = BeautifulSoup(html, "lxml")
    seen: dict[str, ListingIn] = {}
    for a in soup.find_all("a", href=True):
        m = ITEM_LINK_RE.search(a["href"])
        if not m:
            continue
        item_id = m.group(1)
        block = _block_for_link(a)
        btxt = block.get_text(" ", strip=True)
        title = clean_text(a.get_text(" ", strip=True))
        if not title or len(title) < 4:
            # image link: look for text siblings
            cand = [t for t in block.stripped_strings if len(t) > 8 and "$" not in t and not BIDS_RE.search(t)]
            title = clean_text(cand[0]) if cand else None
        img = block.find("img")
        img_url = img.get("src") if img and str(img.get("src", "")).startswith("http") else None
        price = parse_price(btxt)
        bids_m = BIDS_RE.search(btxt)
        end_m = END_RE.search(btxt)
        ends_at = parse_datetime(end_m.group(1)) if end_m else None
        existing = seen.get(item_id)
        if existing:
            if not existing.title or (title and len(title) > len(existing.title)):
                existing.title = title or existing.title
            if img_url and img_url not in existing.image_urls:
                existing.image_urls.append(img_url)
            continue
        if not title:
            title = f"ShopGoodwill item {item_id}"
        seen[item_id] = ListingIn(
            source="email", source_item_id=item_id, source_url=f"https://shopgoodwill.com/item/{item_id}",
            extraction_method="personal_shopper_email", title=title, current_bid=price,
            num_bids=int(bids_m.group(1)) if bids_m else None, ends_at=ends_at,
            image_urls=[img_url] if img_url else [], raw={"email_subject": subject, "block_text": btxt[:500]},
        )
    return list(seen.values())


def parse_eml(raw: bytes) -> list[ListingIn]:
    subject, html = extract_html_from_eml(raw)
    return parse_personal_shopper_html(html, subject=subject)


def poll_imap(host: str, port: int, user: str, password: str, folder: str, subject_filter: str, limit: int = 25,
              mark_seen: bool = True) -> list[tuple[str, list[ListingIn]]]:
    """Fetch unread notification e-mails from the user's own mailbox and parse them."""
    out: list[tuple[str, list[ListingIn]]] = []
    M = imaplib.IMAP4_SSL(host, port)
    try:
        M.login(user, password)
        M.select(folder)
        criteria = f'(UNSEEN SUBJECT "{subject_filter}")' if subject_filter else "(UNSEEN)"
        typ, data = M.search(None, criteria)
        ids = data[0].split() if typ == "OK" and data and data[0] else []
        for uid in ids[-limit:]:
            typ, msg_data = M.fetch(uid, "(RFC822)")
            if typ != "OK":
                continue
            raw = msg_data[0][1]
            subject, html = extract_html_from_eml(raw)
            out.append((subject, parse_personal_shopper_html(html, subject=subject)))
            if mark_seen:
                M.store(uid, "+FLAGS", "\\Seen")
    finally:
        try:
            M.logout()
        except Exception:  # noqa: BLE001
            pass
    return out
