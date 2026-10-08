from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..ingestion.comps_import import CompIn, parse_comps_csv, parse_comps_json
from ..models import Comparable, Listing
from ..services.opportunity import (
    clear_valuation_override,
    compute_finance,
    recompute_opportunity,
    set_valuation_override,
)
from ..valuation.providers import PROVIDERS, provider_status
from .serializers import comp_out, listing_detail, valuation_out

router = APIRouter(prefix="/api/listings/{listing_id}", tags=["comparables"])


def _get(db: Session, listing_id: int) -> Listing:
    l = db.get(Listing, listing_id)
    if l is None:
        raise HTTPException(404, "listing not found")
    return l


def _add(db: Session, l: Listing, c: CompIn) -> Comparable:
    row = Comparable(listing_id=l.id, title=c.title, marketplace=c.marketplace, url=c.url, sold_date=c.sold_date, price=c.price,
                     shipping_included=c.shipping_included, shipping_amount=c.shipping_amount, is_sold=c.is_sold,
                     accepted_offer=c.accepted_offer, comp_type=("active" if not c.is_sold else c.comp_type), similarity=c.similarity,
                     evidence_quality=c.evidence_quality, condition=c.condition, differences=c.differences, source=c.source, is_demo=False)
    db.add(row)
    l.comparables.append(row)
    return row


@router.get("/comps")
def list_comps(listing_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    return {"comparables": [comp_out(c) for c in l.comparables], "valuation": valuation_out(next((v for v in l.valuations if v.is_current), None))}


@router.post("/comps", status_code=201)
def add_comp(listing_id: int, data: CompIn, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    row = _add(db, l, data)
    db.flush()
    recompute_opportunity(db, l)
    return {"comparable": comp_out(row), "listing": listing_detail(l)}


@router.post("/comps/import")
async def import_comps(listing_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    comps, errors = parse_comps_json(raw) if raw.lstrip().startswith(("[", "{")) else parse_comps_csv(raw)
    for c in comps:
        _add(db, l, c)
    db.flush()
    recompute_opportunity(db, l)
    return {"imported": len(comps), "errors": errors, "listing": listing_detail(l)}


class CompPatch(BaseModel):
    comp_type: str | None = None
    similarity: float | None = Field(default=None, ge=0, le=1)
    evidence_quality: str | None = None
    price: float | None = None
    is_sold: bool | None = None
    differences: str | None = None
    condition: str | None = None


@router.patch("/comps/{comp_id}")
def patch_comp(listing_id: int, comp_id: int, patch: CompPatch, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    c = next((x for x in l.comparables if x.id == comp_id), None)
    if c is None:
        raise HTTPException(404, "comparable not found")
    for k, v in patch.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    if c.is_sold is False:
        c.comp_type = "active"
    recompute_opportunity(db, l)
    return {"comparable": comp_out(c), "listing": listing_detail(l)}


@router.delete("/comps/{comp_id}")
def delete_comp(listing_id: int, comp_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    c = next((x for x in l.comparables if x.id == comp_id), None)
    if c is None:
        raise HTTPException(404, "comparable not found")
    l.comparables.remove(c)
    db.delete(c)
    db.flush()
    recompute_opportunity(db, l)
    return listing_detail(l)


class CompSearchIn(BaseModel):
    query: str
    provider: str = "ebay_marketplace_insights"
    limit: int = 20
    save: bool = False


@router.post("/comps/search")
def search_comps(listing_id: int, data: CompSearchIn, db: Session = Depends(get_db)):
    """Query a live sold-data provider (requires credentials + eBay approval). Results are NOT saved unless save=true."""
    l = _get(db, listing_id)
    p = PROVIDERS.get(data.provider)
    if p is None:
        raise HTTPException(400, f"unknown provider; options: {list(PROVIDERS)}")
    ok, note = p.available()
    if not ok:
        raise HTTPException(422, f"provider unavailable: {note}")
    try:
        results = p.search(data.query, data.limit)
    except Exception as e:
        raise HTTPException(502, f"provider error: {e}") from e
    if data.save:
        for c in results:
            _add(db, l, c)
        db.flush()
        recompute_opportunity(db, l)
    return {"results": [c.model_dump(mode="json") for c in results], "saved": data.save, "note": note}


class ValuationOverride(BaseModel):
    expected: float = Field(gt=0)
    conservative: float | None = None
    optimistic: float | None = None
    note: str = ""


@router.post("/valuation/override")
def override_valuation(listing_id: int, data: ValuationOverride, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    set_valuation_override(db, l, data.conservative, data.expected, data.optimistic, data.note)
    recompute_opportunity(db, l)
    return listing_detail(l)


@router.post("/valuation/recalculate")
def recalc_valuation(listing_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    clear_valuation_override(db, l)
    recompute_opportunity(db, l)
    return listing_detail(l)


class FinanceQuery(BaseModel):
    bid: float | None = None
    platform: str | None = None
    resale_price: float | None = None
    overrides: dict = Field(default_factory=dict)
    sensitivity: bool = True


@router.post("/finance")
def finance(listing_id: int, data: FinanceQuery, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    return compute_finance(db, l, bid=data.bid, platform=data.platform, resale_override=data.resale_price,
                           overrides=data.overrides, with_sensitivity=data.sensitivity)


providers_router = APIRouter(prefix="/api/providers", tags=["providers"])


@providers_router.get("/sold-data")
def sold_data_providers():
    return {"providers": provider_status()}
