from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..analysis.pipeline import analyze_listing
from ..analysis.reference_match import match_references
from ..db import get_db
from ..jobs.queue import enqueue
from ..models import Identification, Listing
from ..providers.base import ProviderError, ProviderNotConfigured
from ..services.opportunity import recompute_opportunity
from .serializers import identification_out, listing_detail, run_out

router = APIRouter(prefix="/api/listings/{listing_id}", tags=["analysis"])


def _get(db: Session, listing_id: int) -> Listing:
    l = db.get(Listing, listing_id)
    if l is None:
        raise HTTPException(404, "listing not found")
    return l


class AnalyzeIn(BaseModel):
    mode: str = Field(default="auto", pattern="^(auto|prefilter|triage|deep)$")
    provider: str | None = None  # auto|anthropic|gemini|demo
    model: str | None = None
    force: bool = False
    background: bool = False


@router.post("/analyze")
def analyze(listing_id: int, data: AnalyzeIn, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    if data.background:
        job = enqueue(db, "analyze_listing", listing_id=l.id, payload=data.model_dump(exclude={"background"}), dedupe=False)
        return {"job_id": job.id, "status": job.status}
    try:
        summary = analyze_listing(db, l, mode=data.mode, provider=data.provider, model=data.model, force=data.force)
    except ProviderNotConfigured:
        raise
    except ProviderError as e:
        db.commit()  # keep the failed run / usage rows
        raise HTTPException(502, str(e)) from e
    recompute_opportunity(db, l)
    return {"summary": summary, "listing": listing_detail(l)}


@router.get("/analysis")
def analysis_runs(listing_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    return {"runs": [run_out(r, include_output=True) for r in sorted(l.analysis_runs, key=lambda r: -r.id)],
            "identification": identification_out(next((i for i in l.identifications if i.is_current), None))}


class IdentificationCorrection(BaseModel):
    summary: str = Field(min_length=2, max_length=500)
    domain: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    brand_or_maker: str | None = None
    era: str | None = None
    notes: str | None = None
    demand_indicator: str | None = None
    liquidity_indicator: str | None = None


@router.post("/identification")
def correct_identification(listing_id: int, data: IdentificationCorrection, db: Session = Depends(get_db)):
    """User correction of the AI identification. Stored as a new current identification (origin=user)."""
    l = _get(db, listing_id)
    prev = next((i for i in l.identifications if i.is_current), None)
    base: dict[str, Any] = dict(prev.data) if prev else {}
    base.update({
        "headline_identification": data.summary, "overall_confidence": data.confidence if data.confidence is not None else 0.9,
        "user_correction": {"brand_or_maker": data.brand_or_maker, "era": data.era, "notes": data.notes},
    })
    if data.demand_indicator:
        base["demand_indicator"] = data.demand_indicator
    if data.liquidity_indicator:
        base["liquidity_indicator"] = data.liquidity_indicator
    if data.brand_or_maker:
        if (data.domain or l.domain) == "jewelry":
            base.setdefault("jewelry", {})
            if isinstance(base["jewelry"], dict):
                base["jewelry"]["potential_maker"] = data.brand_or_maker
                base["jewelry"]["maker_confidence"] = data.confidence if data.confidence is not None else 0.9
        else:
            base.setdefault("clothing", {})
            if isinstance(base["clothing"], dict):
                base["clothing"]["brand_or_manufacturer"] = data.brand_or_maker
                base["clothing"]["brand_confidence"] = data.confidence if data.confidence is not None else 0.9
    base["reference_matches"] = match_references(db, domain=data.domain or l.domain, texts=[data.summary, data.brand_or_maker or "", l.title])
    for i in l.identifications:
        i.is_current = False
    ident = Identification(listing_id=l.id, origin="user", run_id=None, domain=data.domain or l.domain, summary=data.summary,
                           confidence=data.confidence if data.confidence is not None else 0.9, data=base,
                           discrepancy=prev.discrepancy if prev else {}, warrants_research=prev.warrants_research if prev else False,
                           is_current=True)
    db.add(ident)
    l.identifications.append(ident)
    if data.domain in ("clothing", "jewelry"):
        l.domain = data.domain
    recompute_opportunity(db, l)
    return listing_detail(l)


@router.delete("/identification/user")
def revert_identification(listing_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    users = [i for i in l.identifications if i.origin == "user"]
    for i in users:
        i.is_current = False
    ai = [i for i in l.identifications if i.origin != "user"]
    if ai:
        max(ai, key=lambda i: i.id).is_current = True
    recompute_opportunity(db, l)
    return listing_detail(l)


@router.get("/references")
def references_for_listing(listing_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    ident = next((i for i in l.identifications if i.is_current), None)
    texts = [l.title, l.description or "", l.category or ""] + ([ident.summary] if ident else [])
    return {"matches": match_references(db, domain=l.domain, texts=texts)}
