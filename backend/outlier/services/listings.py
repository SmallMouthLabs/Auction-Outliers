"""Listing ingestion service: normalization, deduplication, snapshots, image storage."""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..analysis.images import image_dims, sha256_bytes
from ..analysis.prefilter import guess_domain
from ..config import get_settings
from ..models import Listing, ListingImage, ListingSnapshot

log = logging.getLogger(__name__)

SGW_ITEM_RE = re.compile(r"shopgoodwill\.com/item/(\d+)", re.IGNORECASE)


class ListingIn(BaseModel):
    """Normalized listing payload used by every ingestion path."""

    source: str = "manual"
    source_item_id: str | None = None
    source_url: str | None = None
    extraction_method: str | None = None
    title: str = Field(min_length=1, max_length=500)
    """Stripped before validation (see _strip_title)."""
    description: str | None = None
    category: str | None = None
    seller: str | None = None
    domain: str | None = None
    current_bid: float | None = Field(default=None, ge=0)
    num_bids: int | None = Field(default=None, ge=0)
    buy_now_price: float | None = Field(default=None, ge=0)
    ends_at: datetime | None = None
    shipping_cost: float | None = Field(default=None, ge=0)
    handling_fee: float | None = Field(default=None, ge=0)
    other_costs: dict[str, float] = Field(default_factory=dict)
    measurements: dict[str, Any] = Field(default_factory=dict)
    condition_text: str | None = None
    status: str = "active"
    image_urls: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    is_demo: bool = False

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("other_costs")
    @classmethod
    def _costs_nonneg(cls, v: dict[str, float]) -> dict[str, float]:
        if any(x < 0 for x in v.values()):
            raise ValueError("other_costs must be >= 0")
        return v

    @field_validator("source_url")
    @classmethod
    def _url_ok(cls, v: str | None) -> str | None:
        if v and not re.match(r"^https?://", v):
            raise ValueError("source_url must be http(s)")
        return v

    @field_validator("image_urls")
    @classmethod
    def _imgs_ok(cls, v: list[str]) -> list[str]:
        out = []
        for u in v:
            u = u.strip()
            if u and re.match(r"^https?://", u):
                out.append(u)
        return out[:30]

    @field_validator("title", "description", "condition_text", "category", "seller")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


def fingerprint(title: str, seller: str | None, ends_at: datetime | None, first_image: str | None) -> str:
    """Fallback dedupe key when no stable source id exists."""
    norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    parts = [norm, (seller or "").lower(), ends_at.isoformat() if ends_at else "", (first_image or "")]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def extract_sgw_item_id(url: str | None) -> str | None:
    if not url:
        return None
    m = SGW_ITEM_RE.search(url)
    return m.group(1) if m else None


def find_duplicate(db: Session, data: ListingIn) -> Listing | None:
    sid = data.source_item_id or extract_sgw_item_id(data.source_url)
    base = db.query(Listing).filter(Listing.is_demo == data.is_demo)  # demo fixtures never merge with real rows
    if sid:
        # any source sharing the same shopgoodwill item id is the same auction
        hit = base.filter(Listing.source_item_id == sid).first()
        if hit:
            return hit
    if data.source_url:
        hit = base.filter(Listing.source_url == data.source_url).first()
        if hit:
            return hit
    fp = fingerprint(data.title, data.seller, data.ends_at, data.image_urls[0] if data.image_urls else None)
    return base.filter(Listing.fingerprint == fp).first()


MUTABLE = ("current_bid", "num_bids", "ends_at", "shipping_cost", "handling_fee", "status", "buy_now_price")


def upsert_listing(db: Session, data: ListingIn, *, fetch_images: bool = True) -> tuple[Listing, bool, bool]:
    """Create or update a listing. Returns (listing, created, changed)."""
    sid = data.source_item_id or extract_sgw_item_id(data.source_url)
    existing = find_duplicate(db, data)
    now = datetime.now(UTC)
    if existing is None:
        l = Listing(
            source=data.source, source_item_id=sid, source_url=data.source_url, extraction_method=data.extraction_method,
            title=data.title, description=data.description, category=data.category, seller=data.seller,
            domain=data.domain or guess_domain(data.title, data.description, data.category),
            current_bid=data.current_bid, num_bids=data.num_bids, buy_now_price=data.buy_now_price, ends_at=data.ends_at,
            shipping_cost=data.shipping_cost, handling_fee=data.handling_fee, other_costs=data.other_costs,
            measurements=data.measurements, condition_text=data.condition_text, status=data.status,
            fingerprint=fingerprint(data.title, data.seller, data.ends_at, data.image_urls[0] if data.image_urls else None),
            raw=data.raw, is_demo=data.is_demo, first_seen_at=now, last_updated_at=now, last_verified_at=now,
        )
        db.add(l)
        db.flush()
        db.add(ListingSnapshot(listing_id=l.id, source=data.source, current_bid=l.current_bid, num_bids=l.num_bids,
                               ends_at=l.ends_at, shipping_cost=l.shipping_cost, status=l.status, raw=data.raw))
        add_images(db, l, data.image_urls, fetch=fetch_images)
        return l, True, True

    changed = False
    for f in MUTABLE:
        v = getattr(data, f)
        if v is not None and getattr(existing, f) != v:
            setattr(existing, f, v)
            changed = True
    # fill in missing descriptive fields only (never overwrite richer data with sparser data)
    for f in ("description", "category", "seller", "condition_text", "source_url"):
        if getattr(existing, f) in (None, "") and getattr(data, f):
            setattr(existing, f, getattr(data, f))
            changed = True
    if data.measurements and not existing.measurements:
        existing.measurements = data.measurements
        changed = True
    if data.other_costs:
        merged = {**(existing.other_costs or {}), **data.other_costs}
        if merged != existing.other_costs:
            existing.other_costs = merged
            changed = True
    if sid and not existing.source_item_id:
        existing.source_item_id = sid
    existing.last_verified_at = now
    if changed:
        existing.last_updated_at = now
        db.add(ListingSnapshot(listing_id=existing.id, source=data.source, current_bid=existing.current_bid,
                               num_bids=existing.num_bids, ends_at=existing.ends_at, shipping_cost=existing.shipping_cost,
                               status=existing.status, raw=data.raw))
    known = {im.remote_url for im in existing.images if im.remote_url}
    new_urls = [u for u in data.image_urls if u not in known]
    if new_urls:
        add_images(db, existing, new_urls, fetch=fetch_images)
        changed = True
    return existing, False, changed


def record_snapshot(db: Session, l: Listing, *, source: str = "manual", **fields: Any) -> ListingSnapshot:
    changed = False
    for f, v in fields.items():
        if f in MUTABLE and v is not None and getattr(l, f) != v:
            setattr(l, f, v)
            changed = True
    now = datetime.now(UTC)
    l.last_verified_at = now
    if changed:
        l.last_updated_at = now
    snap = ListingSnapshot(listing_id=l.id, source=source, current_bid=l.current_bid, num_bids=l.num_bids, ends_at=l.ends_at,
                           shipping_cost=l.shipping_cost, status=l.status, raw={k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in fields.items()})
    db.add(snap)
    db.flush()
    return snap


# ------------------------------------------------------------------ images

def _image_path(l: Listing, sha: str, ext: str) -> str:
    sub = Path("images") / str(l.id)
    (get_settings().data_dir / sub).mkdir(parents=True, exist_ok=True)
    return str(sub / f"{sha[:16]}{ext}")


def store_image_bytes(db: Session, l: Listing, data: bytes, *, remote_url: str | None = None, position: int | None = None) -> ListingImage:
    sha = sha256_bytes(data)
    dup = next((im for im in l.images if im.sha256 == sha), None)
    if dup:
        return dup
    ext = ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = ".png"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ext = ".webp"
    elif data[:3] == b"GIF":
        ext = ".gif"
    rel = _image_path(l, sha, ext)
    full = get_settings().data_dir / rel
    full.write_bytes(data)
    try:
        w, h = image_dims(full)
    except Exception as e:
        full.unlink(missing_ok=True)
        raise ValueError(f"Uploaded file is not a valid image: {e}") from e
    im = ListingImage(listing_id=l.id, position=position if position is not None else len(l.images), remote_url=remote_url,
                      local_path=rel, sha256=sha, width=w, height=h, is_demo=l.is_demo)
    db.add(im)
    l.images.append(im)
    db.flush()
    return im


def _assert_public_host(url: str) -> None:
    """Refuse to fetch from loopback / private / link-local addresses (SSRF guard)."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    host = urlparse(url).hostname
    if not host:
        raise ValueError("invalid image url")
    if host in ("localhost",) or host.endswith(".local"):
        raise ValueError("refusing to fetch from a local host")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError(f"cannot resolve host {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ValueError(f"refusing to fetch from non-public address {ip}")


def fetch_image(url: str, timeout: float = 20.0) -> bytes:
    s = get_settings()
    _assert_public_host(url)
    headers = {"User-Agent": s.sgw_user_agent, "Accept": "image/*"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as c:
        r = c.get(url)
        r.raise_for_status()
        if len(r.content) > 25 * 1024 * 1024:
            raise ValueError("image too large")
        return r.content


def add_images(db: Session, l: Listing, urls: list[str], *, fetch: bool = True) -> list[ListingImage]:
    out = []
    for url in urls:
        pos = len(l.images)
        if fetch:
            try:
                data = fetch_image(url)
                im = store_image_bytes(db, l, data, remote_url=url, position=pos)
                out.append(im)
                continue
            except Exception as e:  # noqa: BLE001
                log.warning("image fetch failed for %s: %s", url, e)
                im = ListingImage(listing_id=l.id, position=pos, remote_url=url, fetch_error=str(e)[:300], is_demo=l.is_demo)
        else:
            im = ListingImage(listing_id=l.id, position=pos, remote_url=url, is_demo=l.is_demo)
        db.add(im)
        l.images.append(im)
        out.append(im)
    db.flush()
    return out


def retry_image_fetches(db: Session, l: Listing) -> int:
    n = 0
    for im in list(l.images):
        if im.local_path or not im.remote_url:
            continue
        try:
            data = fetch_image(im.remote_url)
            sha = sha256_bytes(data)
            if any(o.sha256 == sha for o in l.images):
                db.delete(im)
                continue
            ext = ".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg"
            rel = _image_path(l, sha, ext)
            (get_settings().data_dir / rel).write_bytes(data)
            im.local_path, im.sha256, im.fetch_error = rel, sha, None
            im.width, im.height = image_dims(get_settings().data_dir / rel)
            n += 1
        except Exception as e:  # noqa: BLE001
            im.fetch_error = str(e)[:300]
    db.flush()
    return n
