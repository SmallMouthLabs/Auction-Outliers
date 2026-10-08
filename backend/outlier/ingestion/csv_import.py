"""CSV / JSON listing import with tolerant column mapping."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from ..services.listings import ListingIn
from .common import clean_text, parse_datetime, parse_int, parse_price

COLUMN_ALIASES = {
    "source_item_id": ["item_id", "itemid", "id", "listing_id", "sgw_id"],
    "source_url": ["url", "link", "listing_url", "item_url"],
    "title": ["title", "name", "listing_title"],
    "description": ["description", "desc", "details"],
    "category": ["category", "cat"],
    "seller": ["seller", "seller_name", "store"],
    "current_bid": ["current_bid", "bid", "price", "current_price", "currentprice"],
    "num_bids": ["num_bids", "bids", "bid_count", "numberofbids"],
    "buy_now_price": ["buy_now", "buy_now_price", "buynowprice"],
    "ends_at": ["ends_at", "end_time", "ending", "end_date", "endtime", "auction_end"],
    "shipping_cost": ["shipping", "shipping_cost", "ship"],
    "handling_fee": ["handling", "handling_fee"],
    "condition_text": ["condition", "condition_text"],
    "image_urls": ["images", "image_urls", "image", "photo", "photos", "imageurl", "image_url"],
}


def _lookup(row: dict[str, Any], field: str) -> Any:
    keys = {k.strip().lower().replace(" ", "_"): k for k in row}
    for alias in [field] + COLUMN_ALIASES.get(field, []):
        if alias in keys:
            return row[keys[alias]]
    return None


def row_to_listing(row: dict[str, Any], source: str = "csv") -> ListingIn | None:
    title = clean_text(_lookup(row, "title"))
    if not title:
        return None
    imgs = _lookup(row, "image_urls")
    if isinstance(imgs, str):
        image_urls = [u.strip() for u in imgs.replace("|", ",").replace(";", ",").replace("\n", ",").split(",") if u.strip()]
    elif isinstance(imgs, list):
        image_urls = [str(u) for u in imgs]
    else:
        image_urls = []
    meas = row.get("measurements") if isinstance(row.get("measurements"), dict) else {}
    sid = _lookup(row, "source_item_id")
    return ListingIn(
        source=source, source_item_id=str(sid) if sid not in (None, "") else None, source_url=clean_text(_lookup(row, "source_url")),
        extraction_method=f"{source}_import", title=title, description=clean_text(_lookup(row, "description")),
        category=clean_text(_lookup(row, "category")), seller=clean_text(_lookup(row, "seller")),
        current_bid=parse_price(_lookup(row, "current_bid")), num_bids=parse_int(_lookup(row, "num_bids")),
        buy_now_price=parse_price(_lookup(row, "buy_now_price")), ends_at=parse_datetime(_lookup(row, "ends_at")),
        shipping_cost=parse_price(_lookup(row, "shipping_cost")), handling_fee=parse_price(_lookup(row, "handling_fee")),
        condition_text=clean_text(_lookup(row, "condition_text")), image_urls=image_urls, measurements=meas,
        raw={k: v for k, v in row.items() if isinstance(v, (str, int, float, bool)) or v is None},
    )


def parse_csv(text: str, source: str = "csv") -> tuple[list[ListingIn], list[str]]:
    reader = csv.DictReader(io.StringIO(text))
    out, errors = [], []
    for i, row in enumerate(reader, start=2):
        try:
            li = row_to_listing(row, source)
            if li is None:
                errors.append(f"line {i}: missing title")
            else:
                out.append(li)
        except Exception as e:  # noqa: BLE001
            errors.append(f"line {i}: {e}")
    return out, errors


def parse_json(text: str, source: str = "json") -> tuple[list[ListingIn], list[str]]:
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("listings") or data.get("items") or [data]
    out, errors = [], []
    for i, row in enumerate(data):
        try:
            li = row_to_listing(row, source) if isinstance(row, dict) else None
            if li is None:
                errors.append(f"item {i}: invalid")
            else:
                out.append(li)
        except Exception as e:  # noqa: BLE001
            errors.append(f"item {i}: {e}")
    return out, errors
