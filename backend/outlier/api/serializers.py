"""ORM -> JSON serializers (no secrets)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import (
    AnalysisRun,
    Comparable,
    Identification,
    Listing,
    ListingImage,
    Opportunity,
    Valuation,
    WatchlistItem,
)
from ..services.opportunity import current_identification, current_valuation


def dt(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


def image_out(im: ListingImage) -> dict[str, Any]:
    return {
        "id": im.id, "position": im.position, "remote_url": im.remote_url,
        "url": f"/api/images/{im.id}" if im.local_path else None, "sha256": im.sha256,
        "width": im.width, "height": im.height, "fetch_error": im.fetch_error, "is_demo": im.is_demo,
    }


def comp_out(c: Comparable) -> dict[str, Any]:
    return {
        "id": c.id, "listing_id": c.listing_id, "title": c.title, "marketplace": c.marketplace, "url": c.url,
        "sold_date": dt(c.sold_date), "price": c.price, "shipping_included": c.shipping_included,
        "shipping_amount": c.shipping_amount, "is_sold": c.is_sold, "accepted_offer": c.accepted_offer,
        "comp_type": c.comp_type, "similarity": c.similarity, "evidence_quality": c.evidence_quality,
        "condition": c.condition, "differences": c.differences, "source": c.source, "is_demo": c.is_demo, "created_at": dt(c.created_at),
    }


def valuation_out(v: Valuation | None) -> dict[str, Any] | None:
    if v is None:
        return None
    return {
        "id": v.id, "method": v.method, "conservative": v.conservative, "expected": v.expected, "optimistic": v.optimistic,
        "is_speculative": v.is_speculative, "evidence_quality": v.evidence_quality, "n_sold_comps": v.n_sold_comps,
        "detail": v.detail, "created_at": dt(v.created_at),
    }


def identification_out(i: Identification | None) -> dict[str, Any] | None:
    if i is None:
        return None
    return {
        "id": i.id, "origin": i.origin, "run_id": i.run_id, "domain": i.domain, "summary": i.summary,
        "confidence": i.confidence, "data": i.data, "discrepancy": i.discrepancy, "warrants_research": i.warrants_research,
        "is_current": i.is_current, "is_demo": i.is_demo, "created_at": dt(i.created_at),
    }


def run_out(r: AnalysisRun, include_output: bool = False) -> dict[str, Any]:
    d = {
        "id": r.id, "stage": r.stage, "provider": r.provider, "model": r.model, "status": r.status,
        "tokens_in": r.tokens_in, "tokens_out": r.tokens_out, "est_cost_usd": r.est_cost_usd, "duration_ms": r.duration_ms,
        "error": r.error, "is_demo": r.is_demo, "created_at": dt(r.created_at), "input_hash": r.input_hash,
    }
    if include_output:
        d["output"] = r.output
    return d


def opportunity_out(o: Opportunity | None) -> dict[str, Any] | None:
    if o is None:
        return None
    return {"score": o.score, "tier": o.tier, "components": o.components, "finance": o.finance, "computed_at": dt(o.computed_at)}


def watchlist_out(w: WatchlistItem | None) -> dict[str, Any] | None:
    if w is None:
        return None
    return {
        "id": w.id, "listing_id": w.listing_id, "status": w.status, "user_max_bid": w.user_max_bid,
        "remind_minutes_before_end": w.remind_minutes_before_end, "reminder_sent_at": dt(w.reminder_sent_at),
        "notes": w.notes, "archived": w.archived, "created_at": dt(w.created_at), "updated_at": dt(w.updated_at),
    }


def listing_summary(l: Listing) -> dict[str, Any]:
    ident = current_identification(l)
    val = current_valuation(l)
    first = next((im for im in l.images if im.local_path), None) or (l.images[0] if l.images else None)
    return {
        "id": l.id, "source": l.source, "source_item_id": l.source_item_id, "source_url": l.source_url,
        "extraction_method": l.extraction_method, "is_demo": l.is_demo, "title": l.title, "category": l.category,
        "seller": l.seller, "domain": l.domain, "current_bid": l.current_bid, "num_bids": l.num_bids,
        "buy_now_price": l.buy_now_price, "ends_at": dt(l.ends_at), "shipping_cost": l.shipping_cost,
        "handling_fee": l.handling_fee, "status": l.status, "archived": l.archived,
        "first_seen_at": dt(l.first_seen_at), "last_updated_at": dt(l.last_updated_at), "last_verified_at": dt(l.last_verified_at),
        "image_count": len(l.images), "thumbnail": image_out(first) if first else None,
        "identification": {
            "summary": ident.summary, "confidence": ident.confidence, "origin": ident.origin, "domain": ident.domain,
            "warrants_research": ident.warrants_research, "misidentification_signal": (ident.discrepancy or {}).get("signal"),
            "is_demo": ident.is_demo,
        } if ident else None,
        "valuation": {
            "conservative": val.conservative, "expected": val.expected, "optimistic": val.optimistic,
            "evidence_quality": val.evidence_quality, "is_speculative": val.is_speculative, "n_sold_comps": val.n_sold_comps, "method": val.method,
        } if val else None,
        "opportunity": opportunity_out(l.opportunity),
        "watchlist": watchlist_out(l.watchlist),
        "feedback_labels": sorted({f.label for f in l.feedback}),
    }


def listing_detail(l: Listing) -> dict[str, Any]:
    d = listing_summary(l)
    d.update({
        "description": l.description, "other_costs": l.other_costs, "measurements": l.measurements,
        "condition_text": l.condition_text, "assumptions": l.assumptions, "user_notes": l.user_notes, "raw": l.raw,
        "images": [image_out(im) for im in l.images],
        "snapshots": [{"id": s.id, "captured_at": dt(s.captured_at), "source": s.source, "current_bid": s.current_bid,
                       "num_bids": s.num_bids, "ends_at": dt(s.ends_at), "shipping_cost": s.shipping_cost, "status": s.status}
                      for s in l.snapshots],
        "identification_full": identification_out(current_identification(l)),
        "identification_history": [identification_out(i) for i in sorted(l.identifications, key=lambda i: -i.id)],
        "valuation_full": valuation_out(current_valuation(l)),
        "comparables": [comp_out(c) for c in sorted(l.comparables, key=lambda c: (not c.is_sold, -(c.similarity or 0)))],
        "analysis_runs": [run_out(r, include_output=True) for r in sorted(l.analysis_runs, key=lambda r: -r.id)],
        "feedback": [{"id": f.id, "label": f.label, "note": f.note, "created_at": dt(f.created_at)} for f in sorted(l.feedback, key=lambda f: -f.id)],
        "notes": [{"id": n.id, "text": n.text, "flagged": n.flagged, "resolved": n.resolved, "created_at": dt(n.created_at)} for n in sorted(l.notes, key=lambda n: -n.id)],
        "outcome": {
            "purchased": l.outcome.purchased, "purchase_price": l.outcome.purchase_price, "acquisition_expenses": l.outcome.acquisition_expenses,
            "purchased_at": dt(l.outcome.purchased_at), "sold": l.outcome.sold, "resale_price": l.outcome.resale_price,
            "selling_fees": l.outcome.selling_fees, "resale_platform": l.outcome.resale_platform, "sold_at": dt(l.outcome.sold_at),
            "days_to_sale": l.outcome.days_to_sale, "realized_profit": l.outcome.realized_profit, "notes": l.outcome.notes,
        } if l.outcome else None,
    })
    return d
