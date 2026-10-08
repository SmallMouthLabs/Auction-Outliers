"""Shared parsing helpers for ingestion (no model calls; deterministic)."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

PRICE_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)")
BIDS_RE = re.compile(r"(\d+)\s*bids?", re.IGNORECASE)
PT = ZoneInfo("America/Los_Angeles")

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M", "%m/%d/%Y", "%m/%d/%y %I:%M %p", "%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p", "%b %d, %Y", "%B %d, %Y",
]


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    m = PRICE_RE.search(str(text))
    if not m:
        try:
            return float(str(text).replace(",", "").strip())
        except ValueError:
            return None
    return float(m.group(1).replace(",", ""))


def parse_int(text: str | None) -> int | None:
    if text is None or text == "":
        return None
    m = re.search(r"-?\d+", str(text))
    return int(m.group(0)) if m else None


def parse_datetime(text: str | None, assume_tz: ZoneInfo = PT) -> datetime | None:
    """Parse many date formats. Naive datetimes are assumed to be Pacific time (ShopGoodwill's timezone)."""
    if text is None:
        return None
    if isinstance(text, datetime):
        dt = text
    else:
        s = str(text).strip().replace("PT", "").replace("PST", "").replace("PDT", "").strip()
        s = re.sub(r"\s+", " ", s)
        dt = None
        for fmt in _DATE_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=assume_tz)
    return dt.astimezone(UTC)


def clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s or None
