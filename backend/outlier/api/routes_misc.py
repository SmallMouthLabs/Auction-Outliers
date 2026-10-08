"""Watchlist, feedback/outcomes/notes, reference db, settings, analytics, jobs, demo, webhooks, status."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import __version__
from ..config import get_secrets, get_settings
from ..db import get_db
from ..demo.loader import clear_demo, load_demo, run_demo_workflow, seed_references
from ..jobs.queue import enqueue, process_pending
from ..models import (
    AnalysisRun,
    Feedback,
    Identification,
    Job,
    Listing,
    Opportunity,
    Outcome,
    ReferenceEntry,
    ResearchNote,
    WatchlistItem,
)
from ..providers.registry import provider_status
from ..providers.usage import usage_summary
from ..services.listings import ListingIn, upsert_listing
from ..services.opportunity import recompute_all, recompute_opportunity
from ..settings_store import DEFAULT_SETTINGS, get_all_settings, reset_settings, update_settings
from ..valuation.providers import provider_status as sold_provider_status
from .serializers import listing_detail, listing_summary, watchlist_out

router = APIRouter(prefix="/api", tags=["misc"])
FEEDBACK_LABELS = ["excellent_find", "worth_investigating", "not_worth_buying", "incorrect_identification", "incorrect_valuation",
                   "too_risky", "too_slow_to_resell", "purchased", "sold"]


def _get(db: Session, listing_id: int) -> Listing:
    l = db.get(Listing, listing_id)
    if l is None:
        raise HTTPException(404, "listing not found")
    return l


# ----------------------------------------------------------------------------- status
@router.get("/health")
def health():
    return {"ok": True, "version": __version__}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    s = get_settings()
    sec = get_secrets().configured()
    demo_count = db.query(func.count(Listing.id)).filter(Listing.is_demo == True).scalar()
    live_count = db.query(func.count(Listing.id)).filter(Listing.is_demo == False).scalar()
    return {
        "version": __version__,
        "components": {
            "ai_triage": {"state": "live" if (sec["anthropic"] or sec["gemini"]) else "needs_config",
                          "detail": "Gemini Flash or Claude Haiku; set GEMINI_API_KEY or ANTHROPIC_API_KEY"},
            "ai_deep": {"state": "live" if (sec["anthropic"] or sec["gemini"]) else "needs_config",
                        "detail": "Claude Opus 5.5 (preferred) or Gemini Pro; set ANTHROPIC_API_KEY or GEMINI_API_KEY"},
            "demo_mode": {"state": "available", "detail": f"{demo_count} demo listings loaded (synthetic fixtures)"},
            "ingest_manual": {"state": "live", "detail": "manual form, JSON, CSV, saved page HTML, photo upload"},
            "ingest_email": {"state": "live" if (s.imap_host and s.imap_user and sec["imap"]) else "needs_config",
                             "detail": "Personal Shopper e-mails: .eml upload works now; IMAP polling needs OUTLIER_IMAP_* settings"},
            "ingest_sgw_unofficial": {"state": "enabled" if s.enable_unofficial_sgw_api else "disabled",
                                      "detail": "unofficial buyer API adapter (off by default; see docs/research.md)"},
            "sold_data_manual": {"state": "live", "detail": "manual / CSV / JSON comparable entry"},
            "sold_data_ebay_insights": {"state": "live" if sec["ebay"] else "needs_config",
                                        "detail": "eBay Marketplace Insights (limited release; needs eBay approval)"},
            "active_data_ebay_browse": {"state": "live" if sec["ebay"] else "needs_config", "detail": "eBay Browse (active listings only)"},
            "webhooks": {"state": "live" if s.webhook_token else "needs_config", "detail": "set OUTLIER_WEBHOOK_TOKEN to enable /api/webhooks/* for n8n"},
            "worker": {"state": "live" if s.run_worker else "disabled", "detail": "background job worker"},
        },
        "providers": [p.__dict__ for p in provider_status()],
        "sold_data_providers": sold_provider_status(),
        "counts": {"demo_listings": demo_count, "live_listings": live_count},
        "budget": {"daily_budget_usd": s.daily_budget_usd, "per_listing_budget_usd": s.per_listing_budget_usd},
    }


# ----------------------------------------------------------------------------- opportunities
@router.get("/opportunities")
def opportunities(tier: str | None = None, min_score: float = 0, include_demo: bool = True, limit: int = Query(200, le=1000),
                  db: Session = Depends(get_db)):
    q = db.query(Listing).join(Opportunity).filter(Listing.archived == False)
    if not include_demo:
        q = q.filter(Listing.is_demo == False)
    if tier:
        q = q.filter(Opportunity.tier == tier)
    q = q.filter(Opportunity.score >= min_score).order_by(Opportunity.score.desc()).limit(limit)
    return {"items": [listing_summary(l) for l in q.all()]}


@router.post("/opportunities/recompute")
def recompute(db: Session = Depends(get_db)):
    return {"recomputed": recompute_all(db)}


# ----------------------------------------------------------------------------- watchlist
class WatchIn(BaseModel):
    status: str | None = None
    user_max_bid: float | None = None
    remind_minutes_before_end: int | None = None
    notes: str | None = None
    archived: bool | None = None


@router.get("/watchlist")
def watchlist(include_archived: bool = False, db: Session = Depends(get_db)):
    q = db.query(WatchlistItem)
    if not include_archived:
        q = q.filter(WatchlistItem.archived == False)
    rows = q.all()
    rows.sort(key=lambda w: (w.listing.ends_at.isoformat() if w.listing.ends_at else "9999"))
    return {"items": [{**listing_summary(w.listing), "watchlist": watchlist_out(w)} for w in rows]}


@router.put("/watchlist/{listing_id}")
def upsert_watch(listing_id: int, data: WatchIn, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    w = l.watchlist
    if w is None:
        w = WatchlistItem(listing_id=l.id)
        db.add(w)
        l.watchlist = w
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(w, k, v)
    if w.remind_minutes_before_end is None:
        w.remind_minutes_before_end = get_all_settings(db)["notifications"]["reminder_minutes_before_end"]
    db.flush()
    return {**listing_summary(l), "watchlist": watchlist_out(w)}


@router.delete("/watchlist/{listing_id}")
def remove_watch(listing_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    if l.watchlist:
        db.delete(l.watchlist)
        l.watchlist = None
    return {"ok": True}


@router.get("/watchlist/reminders/due")
def due_reminders(db: Session = Depends(get_db)):
    """Reminders due now (also fired by the worker job 'watchlist_reminders')."""
    now = datetime.now(UTC)
    due = []
    for w in db.query(WatchlistItem).filter(WatchlistItem.archived == False).all():
        l = w.listing
        if not l.ends_at or w.remind_minutes_before_end is None:
            continue
        ends = l.ends_at if l.ends_at.tzinfo else l.ends_at.replace(tzinfo=UTC)
        secs = (ends - now).total_seconds()
        if 0 < secs <= w.remind_minutes_before_end * 60:
            due.append({"listing_id": l.id, "title": l.title, "ends_at": ends.isoformat(), "minutes_left": round(secs / 60, 1),
                        "user_max_bid": w.user_max_bid, "current_bid": l.current_bid})
    return {"due": due}


# ----------------------------------------------------------------------------- feedback / notes / outcomes
class FeedbackIn(BaseModel):
    label: str
    note: str | None = None


@router.post("/listings/{listing_id}/feedback", status_code=201)
def add_feedback(listing_id: int, data: FeedbackIn, db: Session = Depends(get_db)):
    if data.label not in FEEDBACK_LABELS:
        raise HTTPException(400, f"label must be one of {FEEDBACK_LABELS}")
    l = _get(db, listing_id)
    fb = Feedback(listing_id=l.id, label=data.label, note=data.note)
    db.add(fb)
    l.feedback.append(fb)
    if data.label in ("purchased", "sold"):
        if l.outcome is None:
            l.outcome = Outcome(listing_id=l.id)
            db.add(l.outcome)
        if data.label == "purchased":
            l.outcome.purchased = True
        else:
            l.outcome.sold = True
    recompute_opportunity(db, l)
    return listing_detail(l)


@router.delete("/listings/{listing_id}/feedback/{feedback_id}")
def delete_feedback(listing_id: int, feedback_id: int, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    fb = next((f for f in l.feedback if f.id == feedback_id), None)
    if fb:
        l.feedback.remove(fb)
        db.delete(fb)
    recompute_opportunity(db, l)
    return listing_detail(l)


class NoteIn(BaseModel):
    text: str = Field(min_length=1)
    flagged: bool = False


@router.post("/listings/{listing_id}/notes", status_code=201)
def add_note(listing_id: int, data: NoteIn, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    n = ResearchNote(listing_id=l.id, text=data.text, flagged=data.flagged)
    db.add(n)
    l.notes.append(n)
    db.flush()
    return listing_detail(l)


class NotePatch(BaseModel):
    text: str | None = None
    flagged: bool | None = None
    resolved: bool | None = None


@router.patch("/listings/{listing_id}/notes/{note_id}")
def patch_note(listing_id: int, note_id: int, data: NotePatch, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    n = next((x for x in l.notes if x.id == note_id), None)
    if n is None:
        raise HTTPException(404, "note not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(n, k, v)
    db.flush()
    return listing_detail(l)


class OutcomeIn(BaseModel):
    purchased: bool | None = None
    purchase_price: float | None = None
    acquisition_expenses: float | None = None
    purchased_at: datetime | None = None
    sold: bool | None = None
    resale_price: float | None = None
    selling_fees: float | None = None
    resale_platform: str | None = None
    sold_at: datetime | None = None
    notes: str | None = None


@router.put("/listings/{listing_id}/outcome")
def upsert_outcome(listing_id: int, data: OutcomeIn, db: Session = Depends(get_db)):
    l = _get(db, listing_id)
    o = l.outcome
    if o is None:
        o = Outcome(listing_id=l.id)
        db.add(o)
        l.outcome = o
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(o, k, v)
    if o.purchased_at and o.sold_at:
        o.days_to_sale = max((o.sold_at - o.purchased_at).days, 0)
    if o.sold and o.resale_price is not None:
        o.realized_profit = round((o.resale_price or 0) - (o.selling_fees or 0) - (o.purchase_price or 0) - (o.acquisition_expenses or 0), 2)
    db.flush()
    return listing_detail(l)


# ----------------------------------------------------------------------------- reference database
class ReferenceIn(BaseModel):
    name: str
    entry_type: str = "brand"
    domain: str = "clothing"
    category: str | None = None
    characteristics: str | None = None
    identifiers: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    reference_image_urls: list[str] = Field(default_factory=list)
    price_evidence: list[dict[str, Any]] = Field(default_factory=list)
    typical_low: float | None = None
    typical_high: float | None = None
    demand: str = "medium"
    liquidity: str = "medium"
    id_confidence_notes: str | None = None
    source: str = "user"


def _ref_out(r: ReferenceEntry) -> dict[str, Any]:
    return {c.name: getattr(r, c.name) for c in r.__table__.columns} | {"created_at": r.created_at.isoformat() if r.created_at else None}


@router.get("/reference")
def list_reference(q: str | None = None, domain: str | None = None, db: Session = Depends(get_db)):
    qry = db.query(ReferenceEntry)
    if domain:
        qry = qry.filter(ReferenceEntry.domain == domain)
    if q:
        qry = qry.filter(ReferenceEntry.name.ilike(f"%{q}%"))
    return {"items": [_ref_out(r) for r in qry.order_by(ReferenceEntry.name).all()]}


@router.post("/reference", status_code=201)
def create_reference(data: ReferenceIn, db: Session = Depends(get_db)):
    r = ReferenceEntry(**data.model_dump())
    db.add(r)
    db.flush()
    return _ref_out(r)


@router.put("/reference/{ref_id}")
def update_reference(ref_id: int, data: ReferenceIn, db: Session = Depends(get_db)):
    r = db.get(ReferenceEntry, ref_id)
    if r is None:
        raise HTTPException(404, "not found")
    for k, v in data.model_dump().items():
        setattr(r, k, v)
    return _ref_out(r)


@router.delete("/reference/{ref_id}")
def delete_reference(ref_id: int, db: Session = Depends(get_db)):
    r = db.get(ReferenceEntry, ref_id)
    if r:
        db.delete(r)
    return {"ok": True}


@router.post("/reference/seed")
def seed_reference(db: Session = Depends(get_db)):
    return {"seeded": seed_references(db)}


# ----------------------------------------------------------------------------- settings
def _settings_payload(db: Session) -> dict[str, Any]:
    s = get_settings()
    return {
        "settings": get_all_settings(db), "defaults": DEFAULT_SETTINGS,
        "env": {  # read-only, from environment; no secrets
            "triage_provider": s.triage_provider, "triage_model": s.triage_model, "deep_provider": s.deep_provider,
            "deep_model": s.deep_model, "daily_budget_usd": s.daily_budget_usd, "per_listing_budget_usd": s.per_listing_budget_usd,
            "max_zoom_calls": s.max_zoom_calls, "enable_unofficial_sgw_api": s.enable_unofficial_sgw_api,
            "imap_host": s.imap_host, "imap_user": s.imap_user, "buyer_zip": s.buyer_zip,
        },
        "credentials_configured": get_secrets().configured(),
        "feedback_labels": FEEDBACK_LABELS,
    }


@router.get("/settings")
def get_settings_api(db: Session = Depends(get_db)):
    return _settings_payload(db)


@router.put("/settings")
def put_settings(patch: dict[str, Any], db: Session = Depends(get_db)):
    try:
        update_settings(db, patch)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    recompute_all(db)
    return _settings_payload(db)


@router.post("/settings/reset")
def reset_settings_api(db: Session = Depends(get_db)):
    reset_settings(db)
    recompute_all(db)
    return _settings_payload(db)


# ----------------------------------------------------------------------------- analytics
@router.get("/analytics/summary")
def analytics(days: int = 30, db: Session = Depends(get_db)):
    since = datetime.now(UTC) - timedelta(days=days)
    total = db.query(func.count(Listing.id)).scalar()
    analyzed = db.query(func.count(func.distinct(AnalysisRun.listing_id))).filter(AnalysisRun.stage == "deep", AnalysisRun.status == "succeeded").scalar()
    tiers = dict(db.query(Opportunity.tier, func.count(Opportunity.id)).group_by(Opportunity.tier).all())
    by_domain = {}
    for domain, tier, n in db.query(Listing.domain, Opportunity.tier, func.count(Listing.id)).join(Opportunity).group_by(Listing.domain, Opportunity.tier).all():
        by_domain.setdefault(domain, {})[tier] = n
    margins = [o.finance.get("expected_roi_pct") for o in db.query(Opportunity).all() if o.finance and o.finance.get("expected_roi_pct") is not None]
    profits = [o.finance.get("expected_profit") for o in db.query(Opportunity).all() if o.finance and o.finance.get("expected_profit") is not None]
    corrections = db.query(func.count(Identification.id)).filter(Identification.origin == "user").scalar()
    feedback_counts = dict(db.query(Feedback.label, func.count(Feedback.id)).group_by(Feedback.label).all())
    outcomes = db.query(Outcome).all()
    purchased = [o for o in outcomes if o.purchased]
    sold = [o for o in outcomes if o.sold and o.realized_profit is not None]
    by_category = {}
    for cat, n in db.query(Listing.category, func.count(Listing.id)).join(Opportunity).filter(Opportunity.tier.in_(["HIGH_CONFIDENCE", "SPECULATIVE_HIGH_UPSIDE"])).group_by(Listing.category).all():
        by_category[cat or "(none)"] = n
    demo_count = db.query(func.count(Listing.id)).filter(Listing.is_demo == True).scalar()
    return {
        "items_total": total, "items_demo": demo_count, "items_analyzed_deep": analyzed,
        "opportunities_by_tier": tiers, "by_domain": by_domain, "opportunity_categories": by_category,
        "avg_projected_roi_pct": round(sum(margins) / len(margins), 1) if margins else None,
        "avg_projected_profit_usd": round(sum(profits) / len(profits), 2) if profits else None,
        "identification_corrections": corrections, "feedback_counts": feedback_counts,
        "purchases": len(purchased), "sales": len(sold),
        "realized_profit_total": round(sum(o.realized_profit for o in sold), 2) if sold else 0.0,
        "avg_days_to_sale": round(sum(o.days_to_sale for o in sold if o.days_to_sale is not None) / max(1, len([o for o in sold if o.days_to_sale is not None])), 1) if sold else None,
        "ai_usage": usage_summary(db, days),
        "recent_runs": db.query(func.count(AnalysisRun.id)).filter(AnalysisRun.created_at >= since).scalar(),
    }


# ----------------------------------------------------------------------------- jobs
@router.get("/jobs")
def jobs(status: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    rows = q.order_by(Job.id.desc()).limit(limit).all()
    return {"items": [{"id": j.id, "job_type": j.job_type, "listing_id": j.listing_id, "payload": j.payload, "status": j.status,
                       "attempts": j.attempts, "max_attempts": j.max_attempts, "error": j.error, "result": j.result,
                       "created_at": j.created_at.isoformat() if j.created_at else None,
                       "finished_at": j.finished_at.isoformat() if j.finished_at else None} for j in rows]}


class JobIn(BaseModel):
    job_type: str
    listing_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/jobs", status_code=201)
def create_job(data: JobIn, db: Session = Depends(get_db)):
    if data.job_type not in ("analyze_listing", "fetch_images", "recompute_opportunity", "poll_email", "refresh_listing_unofficial", "watchlist_reminders"):
        raise HTTPException(400, "unknown job type")
    j = enqueue(db, data.job_type, listing_id=data.listing_id, payload=data.payload, dedupe=False)
    return {"id": j.id, "status": j.status}


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if j is None:
        raise HTTPException(404, "job not found")
    j.status, j.error, j.run_after, j.attempts = "pending", None, None, 0
    return {"id": j.id, "status": j.status}


@router.post("/jobs/process")
def process_jobs(limit: int = 10):
    """Process pending jobs synchronously (useful when the worker is disabled or in tests)."""
    return {"processed": process_pending(limit)}


# ----------------------------------------------------------------------------- demo
@router.post("/demo/load")
def demo_load(db: Session = Depends(get_db)):
    return load_demo(db)


@router.post("/demo/run")
def demo_run(db: Session = Depends(get_db)):
    return run_demo_workflow(db)


@router.delete("/demo")
def demo_clear(db: Session = Depends(get_db)):
    return {"removed": clear_demo(db)}


# ----------------------------------------------------------------------------- webhooks (n8n etc.)
def _check_token(x_outlier_token: str | None) -> None:
    tok = get_settings().webhook_token
    if not tok:
        raise HTTPException(503, "webhooks disabled: set OUTLIER_WEBHOOK_TOKEN")
    if x_outlier_token != tok:
        raise HTTPException(401, "bad token")


@router.post("/webhooks/listing")
def webhook_listing(data: ListingIn, analyze: bool = True, x_outlier_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_token(x_outlier_token)
    l, created, changed = upsert_listing(db, data, fetch_images=True)
    recompute_opportunity(db, l)
    if analyze and (created or changed):
        enqueue(db, "analyze_listing", listing_id=l.id, payload={"mode": "auto"})
    return {"id": l.id, "created": created, "changed": changed}


class WebhookEmail(BaseModel):
    html: str
    subject: str | None = None


@router.post("/webhooks/email")
def webhook_email(data: WebhookEmail, analyze: bool = True, x_outlier_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    from ..ingestion.email_import import parse_personal_shopper_html

    _check_token(x_outlier_token)
    ids = []
    for li in parse_personal_shopper_html(data.html, subject=data.subject):
        l, created, changed = upsert_listing(db, li, fetch_images=True)
        recompute_opportunity(db, l)
        ids.append(l.id)
        if analyze and (created or changed):
            enqueue(db, "analyze_listing", listing_id=l.id, payload={"mode": "auto"})
    return {"ids": ids}
