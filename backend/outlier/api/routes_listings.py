from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..ingestion.csv_import import parse_csv, parse_json
from ..ingestion.email_import import parse_eml, parse_personal_shopper_html
from ..ingestion.page_html import parse_item_page
from ..jobs.queue import enqueue
from ..models import Listing, ListingImage
from ..services.listings import ListingIn, add_images, record_snapshot, store_image_bytes, upsert_listing
from ..services.opportunity import recompute_opportunity
from .serializers import image_out, listing_detail, listing_summary

router = APIRouter(prefix="/api/listings", tags=["listings"])
MAX_UPLOAD = 25 * 1024 * 1024


def _get(db: Session, listing_id: int) -> Listing:
    l = db.get(Listing, listing_id)
    if l is None:
        raise HTTPException(404, "listing not found")
    return l


def _ingest(db: Session, items: list[ListingIn], fetch_images: bool, analyze: bool) -> dict[str, Any]:
    created, updated, unchanged, ids = 0, 0, 0, []
    for li in items:
        l, was_created, changed = upsert_listing(db, li, fetch_images=fetch_images)
        recompute_opportunity(db, l)
        ids.append(l.id)
        if was_created:
            created += 1
        elif changed:
            updated += 1
        else:
            unchanged += 1
        if analyze and (was_created or changed):
            enqueue(db, "analyze_listing", listing_id=l.id, payload={"mode": "auto"})
    return {"created": created, "updated": updated, "unchanged": unchanged, "ids": ids}


@router.post("", status_code=201)
def create_listing(data: ListingIn, fetch_images: bool = True, analyze: bool = False, db: Session = Depends(get_db)):
    l, created, changed = upsert_listing(db, data, fetch_images=fetch_images)
    recompute_opportunity(db, l)
    if analyze:
        enqueue(db, "analyze_listing", listing_id=l.id, payload={"mode": "auto"})
    return {"listing": listing_detail(l), "created": created, "changed": changed}


@router.post("/import/json")
def import_json(body: dict[str, Any], fetch_images: bool = True, analyze: bool = False, db: Session = Depends(get_db)):
    import json

    items, errors = parse_json(json.dumps(body))
    res = _ingest(db, items, fetch_images, analyze)
    return {**res, "errors": errors}


@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...), fetch_images: bool = True, analyze: bool = False, db: Session = Depends(get_db)):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "file too large")
    items, errors = parse_csv(raw.decode("utf-8-sig", errors="replace"))
    res = _ingest(db, items, fetch_images, analyze)
    return {**res, "errors": errors}


@router.post("/import/email")
async def import_email(file: UploadFile | None = File(default=None), html: str | None = Form(default=None),
                       fetch_images: bool = True, analyze: bool = False, db: Session = Depends(get_db)):
    """Import ShopGoodwill Personal Shopper notification e-mails (.eml upload or pasted HTML)."""
    if file is not None:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, "file too large")
        items = parse_eml(raw) if raw.lstrip()[:1] != b"<" else parse_personal_shopper_html(raw.decode("utf-8", errors="replace"))
    elif html:
        items = parse_personal_shopper_html(html)
    else:
        raise HTTPException(400, "provide an .eml file or html")
    if not items:
        return {"created": 0, "updated": 0, "unchanged": 0, "ids": [], "errors": ["No shopgoodwill.com/item/<id> links found in the e-mail."]}
    res = _ingest(db, items, fetch_images, analyze)
    return {**res, "errors": [], "parsed": [i.model_dump(mode="json") for i in items]}


@router.post("/import/page")
async def import_page(file: UploadFile | None = File(default=None), html: str | None = Form(default=None), url: str | None = Form(default=None),
                      fetch_images: bool = True, analyze: bool = False, db: Session = Depends(get_db)):
    """Import a saved ShopGoodwill item page (HTML)."""
    if file is not None:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, "file too large")
        html = raw.decode("utf-8", errors="replace")
    if not html:
        raise HTTPException(400, "provide an html file or html text")
    li = parse_item_page(html, url)
    if li.title == "Untitled listing" and not li.image_urls and li.current_bid is None and not li.source_item_id:
        raise HTTPException(400, "Could not find a listing in that HTML (no title, price, item id or images).")
    res = _ingest(db, [li], fetch_images, analyze)
    return {**res, "errors": [], "parsed": li.model_dump(mode="json")}


@router.get("")
def list_listings(
    q: str | None = None, domain: str | None = None, tier: str | None = None, source: str | None = None,
    status: str | None = None, include_demo: bool = True, include_archived: bool = False, watchlist_only: bool = False,
    sort: str = "score", order: str = "desc", limit: int = Query(100, le=500), offset: int = 0, db: Session = Depends(get_db),
):
    qry = db.query(Listing)
    if not include_archived:
        qry = qry.filter(Listing.archived == False)
    if not include_demo:
        qry = qry.filter(Listing.is_demo == False)
    if q:
        like = f"%{q}%"
        qry = qry.filter(or_(Listing.title.ilike(like), Listing.description.ilike(like), Listing.category.ilike(like)))
    if domain:
        qry = qry.filter(Listing.domain == domain)
    if source:
        qry = qry.filter(Listing.source == source)
    if status:
        qry = qry.filter(Listing.status == status)
    rows = qry.all()
    out = [listing_summary(l) for l in rows]
    if tier:
        out = [r for r in out if (r["opportunity"] or {}).get("tier") == tier]
    if watchlist_only:
        out = [r for r in out if r["watchlist"] and not r["watchlist"]["archived"]]

    def key(r):
        f = (r["opportunity"] or {}).get("finance") or {}
        return {
            "score": (r["opportunity"] or {}).get("score") or 0,
            "profit": f.get("expected_profit") if f.get("expected_profit") is not None else -1e9,
            "max_bid": f.get("max_bid") if f.get("max_bid") is not None else -1e9,
            "ends_at": r["ends_at"] or "9999",
            "current_bid": r["current_bid"] or 0,
            "confidence": (r["identification"] or {}).get("confidence") or 0,
            "updated": r["last_updated_at"] or "",
        }.get(sort, 0)

    out.sort(key=key, reverse=(order == "desc"))
    total = len(out)
    return {"total": total, "items": out[offset: offset + limit]}


@router.get("/{listing_id}")
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    return listing_detail(_get(db, listing_id))


class ListingPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    category: str | None = None
    seller: str | None = None
    domain: str | None = Field(default=None, pattern="^(clothing|jewelry|other|unknown)$")
    condition_text: str | None = None
    measurements: dict[str, Any] | None = None
    other_costs: dict[str, float] | None = None
    assumptions: dict[str, Any] | None = None
    user_notes: str | None = None
    archived: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|ended|unknown)$")
    source_url: str | None = Field(default=None, pattern="^https?://")

    @field_validator("title", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("other_costs")
    @classmethod
    def _nonneg(cls, v):
        if v and any(x < 0 for x in v.values()):
            raise ValueError("other_costs must be >= 0")
        return v



@router.patch("/{listing_id}")
def patch_listing(listing_id: int, patch: ListingPatch, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    data = patch.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is None:
        raise HTTPException(400, "title cannot be null")
    if "assumptions" in data:
        from ..finance.overrides import validate_overrides

        data["assumptions"] = validate_overrides(data["assumptions"]) if data["assumptions"] else {}
    for k, v in data.items():
        setattr(l, k, v)
    recompute_opportunity(db, l)
    return listing_detail(l)


class SnapshotIn(BaseModel):
    current_bid: float | None = Field(default=None, ge=0)
    num_bids: int | None = Field(default=None, ge=0)
    ends_at: datetime | None = None
    shipping_cost: float | None = Field(default=None, ge=0)
    handling_fee: float | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern="^(active|ended|unknown)$")
    source: str = "manual"


@router.post("/{listing_id}/snapshot")
def add_snapshot(listing_id: int, data: SnapshotIn, db: Session = Depends(get_db)):
    """Record a manual price/status update (authorized source: you looked at the page)."""
    l = _get(db, listing_id)
    fields = data.model_dump(exclude_unset=True, exclude={"source"})
    record_snapshot(db, l, source=data.source, **fields)
    recompute_opportunity(db, l)
    return listing_detail(l)


@router.post("/{listing_id}/images")
async def upload_images(listing_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    out = []
    for f in files:
        raw = await f.read()
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, f"{f.filename}: too large")
        if not (f.content_type or "").startswith("image/"):
            raise HTTPException(400, f"{f.filename}: not an image")
        try:
            out.append(image_out(store_image_bytes(db, l, raw)))
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
    return {"images": out}


class ImageUrlsIn(BaseModel):
    urls: list[str]


@router.post("/{listing_id}/image-urls")
def add_image_urls(listing_id: int, data: ImageUrlsIn, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    known = {im.remote_url for im in l.images}
    ims = add_images(db, l, [u for u in data.urls if u.startswith("http") and u not in known], fetch=True)
    return {"images": [image_out(im) for im in ims]}


@router.delete("/{listing_id}/images/{image_id}")
def delete_image(listing_id: int, image_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    im = next((i for i in l.images if i.id == image_id), None)
    if im is None:
        raise HTTPException(404, "image not found")
    if im.local_path:
        (get_settings().data_dir / im.local_path).unlink(missing_ok=True)
    db.delete(im)
    return {"ok": True}


@router.delete("/{listing_id}")
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    db.delete(l)
    return {"ok": True}


image_router = APIRouter(prefix="/api/images", tags=["images"])


@image_router.get("/{image_id}")
def serve_image(image_id: int, db: Session = Depends(get_db)):
    im = db.get(ListingImage, image_id)
    if im is None or not im.local_path:
        raise HTTPException(404, "image not found")
    data_dir = get_settings().data_dir.resolve()
    path = (data_dir / im.local_path).resolve()
    if data_dir not in path.parents or not path.exists():
        raise HTTPException(404, "image file missing")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})
